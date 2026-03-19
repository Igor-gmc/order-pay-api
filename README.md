# Order Pay API

Платёжный backend для обработки заказов, оплат (наличные и эквайринг), возвратов и синхронизации с внешним банком.

## Стек

- **FastAPI** — async REST API
- **SQLAlchemy 2.0** — async ORM (Mapped, mapped_column)
- **PostgreSQL** — основная БД (asyncpg)
- **Pydantic v2** — валидация и сериализация
- **httpx** — async HTTP-клиент для интеграции с банком

## Запуск

```bash
# Зависимости
pip install -r requirements.txt

# PostgreSQL должен быть доступен (см. .env или config.py)
# Default: postgresql+asyncpg://postgres:postgres@localhost:5432/order_processing

# Старт
uvicorn app.main:app --reload
```

При старте приложение автоматически:
- создаёт PostgreSQL sequence `order_number_seq` для номеров заказов
- создаёт все таблицы через `Base.metadata.create_all`

## Архитектура

```
Router (тонкий) → Service (бизнес-логика) → Repository (данные) → ORM → PostgreSQL
                      ↓
              Integration (банк)
```

**Слои:**
- **Routers** — принимают HTTP, вызывают сервис, маппят ошибки в HTTP-коды
- **Services** — вся бизнес-логика, валидация, транзакции
- **Repositories** — чистый data access, без бизнес-решений
- **Integrations** — адаптеры к внешним системам (банк)
- **Schemas** — Pydantic-контракты для API и внешних систем

## Структура проекта

```
app/
├── main.py                          # FastAPI app, lifespan, подключение роутеров
├── core/
│   ├── config.py                    # Settings (database_url, bank_api_url, debug)
│   └── enums.py                     # Все статусные enum'ы
├── database/
│   ├── base.py                      # DeclarativeBase
│   ├── session.py                   # AsyncEngine, async_session_maker, get_session
│   └── models/
│       ├── order.py                 # Order
│       ├── payment.py               # Payment
│       ├── refund.py                # Refund
│       ├── bank_payment_state.py    # BankPaymentState
│       └── event_log.py            # EventLog (immutable)
├── schemas/
│   ├── orders.py                    # OrderCreate, OrderRead, OrderList
│   ├── payments.py                  # CashPaymentCreate, PaymentRead, PaymentList
│   ├── refunds.py                   # RefundCreate, RefundRead
│   └── bank.py                      # AcquiringPaymentCreate, BankPaymentStateRead
├── repositories/
│   ├── orders.py                    # OrderRepository
│   ├── payments.py                  # PaymentRepository
│   ├── refunds.py                   # RefundRepository
│   └── bank_payments.py             # BankPaymentRepository
├── services/
│   ├── order_service.py             # Создание и чтение заказов
│   ├── payment_service.py           # Наличная и эквайринговая оплата
│   └── refund_service.py            # Возвраты
├── integrations/
│   └── bank/
│       ├── client.py                # BankClient (acquiring_start, acquiring_check)
│       ├── schemas.py               # DTO внешнего банка
│       └── exceptions.py            # BankUnavailableError, BankRequestError, BankPaymentNotFoundError
└── api/
    ├── dependencies.py              # DI: Session, OrderServiceDep, PaymentServiceDep, RefundServiceDep
    └── routers/
        ├── orders.py                # /orders
        ├── payments.py              # /payments
        └── refunds.py               # /refunds
```

## API-эндпоинты

| Метод | URL | Описание | Коды |
|-------|-----|----------|------|
| GET | `/ping` | Health check | 200 |
| POST | `/orders` | Создать заказ | 201, 409 |
| GET | `/orders` | Список заказов | 200 |
| GET | `/orders/{order_id}` | Заказ по ID | 200, 404 |
| GET | `/orders/{order_id}/payments` | Платежи заказа | 200, 404 |
| POST | `/payments/cash` | Наличная оплата | 201, 404, 409 |
| POST | `/refunds` | Возврат по платежу | 201, 404, 409 |

## Модель данных

### Enum'ы

| Enum | Значения |
|------|----------|
| `PaymentType` | `cash`, `acquiring` |
| `OrderPaymentStatus` | `unpaid`, `partially_paid`, `paid` |
| `PaymentStatus` | `pending`, `completed`, `cancelled`, `part_refunded`, `refunded`, `failed` |
| `BankPaymentStatus` | `received`, `conducted`, `cancelled`, `refunded` |
| `RefundStatus` | `completed`, `failed` |

### Таблицы

**orders** — заказы:
- `id` (UUID PK), `number` (unique, автогенерация через PG sequence, формат `0001`), `amount_total`, `payment_status`, `paid_amount`, `refunded_amount`, `created_at`, `updated_at`

**payments** — платежи (наличные и эквайринг):
- `id` (UUID PK), `order_id` (FK → orders), `payment_type`, `amount`, `status`, `external_id` (bank_payment_id для эквайринга), `paid_at`, `created_at`, `updated_at`

**refunds** — возвраты:
- `id` (UUID PK), `payment_id` (FK → payments), `order_id` (FK → orders), `amount`, `status`, `created_at`, `updated_at`

**bank_payment_states** — снимок состояния банковского платежа:
- `id` (UUID PK), `payment_id` (FK → payments, unique 1:1), `bank_payment_id`, `bank_status`, `bank_amount`, `bank_paid_at`, `last_synced_at`, `sync_error`, `created_at`, `updated_at`

**event_logs** — иммутабельный лог событий:
- `id` (UUID PK), `level`, `source`, `message`, `payload_json` (JSONB), `created_at`

### Связи

```
Order 1──* Payment 1──? BankPaymentState
  │            │
  │            └──* Refund
  └───────────────* Refund
```

## Бизнес-логика

### 1. Создание заказа

```
POST /orders { amount_total }
```

- Генерация номера через `SELECT nextval('order_number_seq')` → формат `0001`, `0002`, ...
- Начальное состояние: `payment_status=unpaid`, `paid_amount=0`, `refunded_amount=0`

### 2. Оплата наличными

```
POST /payments/cash { order_id, amount }
```

Валидация:
- Заказ существует
- Заказ не в статусе `paid`
- `amount ≤ remaining` (remaining = amount_total − paid_amount)

Действия в одной транзакции:
- Создаёт `Payment(type=cash, status=completed, paid_at=now)`
- Обновляет `order.paid_amount += amount`
- Пересчитывает `order.payment_status`:
  - `paid_amount >= amount_total` → `paid`
  - `paid_amount > 0` → `partially_paid`
  - иначе → `unpaid`

### 3. Оплата картой (эквайринг)

Пока доступен только на уровне сервиса (`PaymentService.create_acquiring_payment`), API-ручка не подключена.

```python
create_acquiring_payment(AcquiringPaymentCreate { order_id, amount })
```

Валидация — та же, что и для наличных.

Действия:
1. Вызов банка: `BankClient.acquiring_start(order_number, amount)` — **до** любых записей в БД
2. Создаёт `Payment(type=acquiring, status=pending, external_id=bank_payment_id)` — **не** `completed`
3. Создаёт `BankPaymentState(bank_payment_id, bank_status, bank_amount, last_synced_at=now)`
4. **Не меняет** `order.paid_amount` и `order.payment_status` — платёж ещё не подтверждён

Ключевое отличие от наличных: эквайринговый платёж при создании не является подтверждённой оплатой. Деньги зачисляются в заказ только после подтверждения от банка (sync — ещё не реализован).

Если банк недоступен или вернул ошибку — транзакция не коммитится, ничего не сохраняется.

### 4. Возврат

```
POST /refunds { payment_id, amount }
```

Валидация:
- Платёж существует
- `amount ≤ available` (available = payment.amount − sum(completed refunds))

Действия в одной транзакции:
- Создаёт `Refund(status=completed)`
- Обновляет статус платежа:
  - вся сумма возвращена → `refunded`
  - часть суммы → `part_refunded`
- Обновляет заказ:
  - `order.refunded_amount += amount`
  - `order.paid_amount -= amount`
  - Пересчитывает `order.payment_status`

Поддерживает множественные частичные возвраты по одному платежу.

### 5. Чтение платежей заказа

```
GET /orders/{order_id}/payments
```

- Проверяет существование заказа
- Возвращает список всех платежей заказа (desc по дате)

## Интеграция с банком

### Разделение контрактов

- `app/schemas/bank.py` — контракт между нашим API и фронтендом
- `app/integrations/bank/schemas.py` — DTO для внешнего банка (отдельная граница)

### BankClient

Адаптер к внешнему банковскому API (`settings.bank_api_url`):

| Метод | HTTP | URL | Назначение |
|-------|------|-----|------------|
| `acquiring_start(data)` | POST | `/acquiring/start` | Инициировать платёж |
| `acquiring_check(bank_payment_id)` | GET | `/acquiring/check/{id}` | Проверить статус |

### Исключения банка

| Исключение | Когда |
|------------|-------|
| `BankUnavailableError` | Сеть / таймаут |
| `BankRequestError` | Банк ответил не-2xx (хранит `status_code`, `detail`) |
| `BankPaymentNotFoundError` | Банк вернул 404 (хранит `bank_payment_id`) |

## Типичные сценарии

### Полный цикл: оплата → возврат

```
1. POST /orders          { amount_total: 1000 }         → order (unpaid, paid=0)
2. POST /payments/cash   { order_id, amount: 600 }      → order (partially_paid, paid=600)
3. POST /payments/cash   { order_id, amount: 400 }      → order (paid, paid=1000)
4. GET  /orders/{id}/payments                            → [payment_600, payment_400]
5. POST /refunds         { payment_id, amount: 300 }     → order (partially_paid, paid=700, refunded=300)
                                                           payment_600 → part_refunded
6. POST /refunds         { payment_id, amount: 300 }     → order (partially_paid, paid=400, refunded=600)
                                                           payment_600 → refunded
7. POST /refunds         { payment_id, amount: 1 }       → 409 (exceeds available 0.00)
```

### Ошибки

| Ситуация | HTTP-код | Пример |
|----------|----------|--------|
| Заказ/платёж не найден | 404 | `Order '{id}' not found` |
| Заказ уже полностью оплачен | 409 | `Order '0001' is already fully paid` |
| Сумма оплаты больше остатка | 409 | `Payment amount 500 exceeds remaining 200` |
| Сумма возврата больше доступного | 409 | `Refund amount 100 exceeds available 50` |

## Что ещё не реализовано

- API-ручка для эквайринговой оплаты (`POST /payments/acquiring`)
- Синхронизация с банком (bank sync)
- Mock-симулятор банка
- Event logging
- Фронтенд (templates/static)
- Миграции Alembic
- Тесты
