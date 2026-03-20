# Order Pay API

Платёжный backend для обработки заказов, оплат (наличные и эквайринг), возвратов и синхронизации с внешним банком. Включает mock-симулятор банка и веб-интерфейс для ручного тестирования.

![Веб-интерфейс](docs/screenshot.png)

## Быстрый старт

### Требования

- Python 3.11+
- PostgreSQL

### Установка и запуск

```bash
# Зависимости
pip install -r requirements.txt

# Настроить переменные окружения (или .env файл)
# DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/order_processing
# BANK_API_URL=http://localhost:8000/mock-bank

# Запуск
uvicorn app.main:app --reload
```

При первом старте приложение автоматически:
- создаёт PostgreSQL sequence `order_number_seq` для номеров заказов
- создаёт все таблицы через `Base.metadata.create_all`
- заполняет БД демо-данными (4 заказа, 3 платежа, 1 возврат), если таблица `orders` пуста

При повторном запуске данные не дублируются — seed выполняется только при пустой БД.

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
- **Integrations** — адаптеры к внешним системам (mock-банк)
- **Schemas** — Pydantic-контракты для API и внешних систем

## Структура проекта

```
app/
├── main.py                          # FastAPI app, lifespan, middleware, роутеры
├── core/
│   ├── config.py                    # Settings (database_url, bank_api_url, debug)
│   ├── enums.py                     # Все статусные enum'ы
│   ├── exceptions.py                # Доменные исключения
│   ├── logging.py                   # Настройка логирования
│   └── seed.py                      # Демо-данные при первом запуске (опционально)
├── database/
│   ├── base.py                      # DeclarativeBase
│   ├── session.py                   # AsyncEngine, async_session_maker, get_session
│   └── models/
│       ├── order.py                 # Order
│       ├── payment.py               # Payment
│       ├── refund.py                # Refund
│       ├── bank_payment_state.py    # BankPaymentState
│       └── event_log.py             # EventLog (immutable)
├── schemas/
│   ├── common.py                    # Общие схемы
│   ├── orders.py                    # OrderCreate, OrderRead, OrderList
│   ├── payments.py                  # CashPaymentCreate, PaymentRead, PaymentList
│   ├── refunds.py                   # RefundCreate, RefundRead, RefundList
│   ├── bank.py                      # AcquiringPaymentCreate, BankPaymentStateRead
│   └── logs.py                      # EventLogRead, EventLogList
├── repositories/
│   ├── orders.py                    # OrderRepository
│   ├── payments.py                  # PaymentRepository
│   ├── refunds.py                   # RefundRepository
│   ├── bank_payments.py             # BankPaymentRepository
│   └── logs.py                      # LogRepository
├── services/
│   ├── order_service.py             # Создание и чтение заказов
│   ├── payment_service.py           # Наличная и эквайринговая оплата
│   ├── refund_service.py            # Возвраты
│   ├── bank_sync_service.py         # Синхронизация платежей с банком
│   ├── bank_state_service.py        # Управление состоянием банковских платежей
│   └── log_service.py               # Логирование событий
├── integrations/
│   └── bank/
│       ├── client.py                # BankClient (acquiring_start, acquiring_check)
│       ├── schemas.py               # DTO внешнего банка
│       └── exceptions.py            # BankUnavailableError, BankRequestError
├── api/
│   ├── dependencies.py              # DI: Session, сервисы через Depends
│   └── routers/
│       ├── orders.py                # /orders
│       ├── payments.py              # /payments
│       ├── refunds.py               # /refunds
│       ├── bank_sync.py             # /bank (синхронизация)
│       ├── bank_simulator.py        # /mock-bank (симулятор)
│       └── logs.py                  # /logs
├── static/
│   ├── css/styles.css               # Стили веб-интерфейса
│   └── js/app.js                    # Клиентская логика
└── templates/
    └── index.html                   # SPA-страница
```

## API-эндпоинты

### Заказы

| Метод | URL | Описание | Коды |
|-------|-----|----------|------|
| POST | `/orders` | Создать заказ | 201, 409 |
| GET | `/orders` | Список заказов | 200 |
| GET | `/orders/{order_id}` | Заказ по ID | 200, 404 |
| GET | `/orders/{order_id}/payments` | Платежи заказа | 200, 404 |

### Платежи

| Метод | URL | Описание | Коды |
|-------|-----|----------|------|
| POST | `/payments/cash` | Оплата наличными | 201, 404, 409 |
| POST | `/payments/acquiring` | Оплата картой (эквайринг) | 201, 404, 409, 502, 503 |

### Возвраты

| Метод | URL | Описание | Коды |
|-------|-----|----------|------|
| POST | `/refunds` | Создать возврат | 201, 404, 409 |
| GET | `/payments/{payment_id}/refunds` | Возвраты по платежу | 200, 404 |

### Банк (синхронизация)

| Метод | URL | Описание | Коды |
|-------|-----|----------|------|
| GET | `/bank/payments` | Все банковские платежи | 200 |
| GET | `/bank/payments/{payment_id}` | Состояние банковского платежа | 200, 404, 409 |
| POST | `/bank/sync/{payment_id}` | Синхронизировать с банком | 200, 404, 409, 502, 503 |

### Mock-банк (симулятор)

| Метод | URL | Описание | Коды |
|-------|-----|----------|------|
| GET | `/mock-bank/mode` | Текущий режим (online/offline) | 200 |
| PATCH | `/mock-bank/mode` | Переключить режим | 200 |
| POST | `/mock-bank/acquiring/start` | Инициировать платёж | 201, 503 |
| GET | `/mock-bank/acquiring/check/{id}` | Проверить статус платежа | 200, 404, 503 |
| PATCH | `/mock-bank/payments/{id}/status` | Изменить статус платежа | 200, 404 |

### Прочее

| Метод | URL | Описание | Коды |
|-------|-----|----------|------|
| GET | `/logs` | Журнал событий (query: limit) | 200 |
| GET | `/ping` | Health check | 200 |
| GET | `/` | Веб-интерфейс | 200 |

## Схема БД

![Схема базы данных](docs/db_scheme.png)

Исходный код схемы для [dbdiagram.io](https://dbdiagram.io/) — [`docs/dbdiagram.dbml`](docs/dbdiagram.dbml)

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
- `id` (UUID PK), `number` (unique, автогенерация через sequence, формат `0001`), `amount_total`, `payment_status`, `paid_amount`, `refunded_amount`, `created_at`, `updated_at`

**payments** — платежи:
- `id` (UUID PK), `order_id` (FK → orders), `payment_type`, `amount`, `status`, `external_id` (bank_payment_id для эквайринга), `paid_at`, `created_at`, `updated_at`

**refunds** — возвраты:
- `id` (UUID PK), `payment_id` (FK → payments), `order_id` (FK → orders), `amount`, `status`, `created_at`, `updated_at`

**bank_payment_states** — состояние банковского платежа:
- `id` (UUID PK), `payment_id` (FK → payments, unique 1:1), `bank_payment_id`, `bank_status`, `bank_amount`, `bank_paid_at`, `last_synced_at`, `sync_error`, `created_at`, `updated_at`

**event_logs** — иммутабельный журнал событий:
- `id` (UUID PK), `level`, `source`, `message`, `payload_json` (JSONB), `created_at`

### Связи

```
Order 1──* Payment 1──? BankPaymentState
  │            │
  │            └──* Refund
  └───────────────* Refund
```

## Пользовательские сценарии

### 1. Оплата наличными

```
POST /orders              { amount_total: 1000 }       → заказ (unpaid, paid=0)
POST /payments/cash       { order_id, amount: 600 }    → заказ (partially_paid, paid=600)
POST /payments/cash       { order_id, amount: 400 }    → заказ (paid, paid=1000)
```

### 2. Оплата картой

```
POST /payments/acquiring  { order_id, amount: 500 }    → платёж (pending), банковский платёж создан
                                                         заказ остаётся unpaid (pending не считается)
Банк: PATCH /mock-bank/payments/{id}/status             → conducted
POST /bank/sync/{payment_id}                            → платёж (completed), заказ обновлён
```

### 3. Отмена банковского платежа

```
Банк: PATCH /mock-bank/payments/{id}/status             → cancelled
POST /bank/sync/{payment_id}                            → платёж (cancelled), заказ не меняется
```

### 4. Возврат

```
POST /refunds  { payment_id, amount: 300 }              → возврат создан
                                                          платёж → part_refunded
                                                          заказ: paid_amount -= 300, refunded_amount += 300
POST /refunds  { payment_id, amount: 200 }              → платёж → refunded (вся сумма возвращена)
```

### 5. Offline-режим банка

```
PATCH /mock-bank/mode     { online: false }             → банк переходит в офлайн
POST /payments/acquiring  { order_id, amount: 500 }     → 503 Service Unavailable
PATCH /mock-bank/mode     { online: true }              → банк снова онлайн
```

### 6. Защитные проверки

| Ситуация | HTTP-код | Сообщение |
|----------|----------|-----------|
| Переплата (сумма > остаток) | 409 | `Payment amount 500 exceeds remaining 200` |
| Повторная оплата оплаченного заказа | 409 | `Order '0001' is already fully paid` |
| Возврат больше доступного | 409 | `Refund amount 100 exceeds available 50` |
| Заказ/платёж не найден | 404 | `Order '{id}' not found` |

## Веб-интерфейс

Доступен по адресу `http://localhost:8000`. Одностраничное приложение с тремя панелями:

- **Компания** — создание заказов, оплата наличными/картой, возвраты. Таблица заказов с номером, суммой, статусом оплаты, суммой возвратов
- **Банк** — управление mock-банком: переключение online/offline, просмотр банковских платежей, изменение статусов, синхронизация
- **Журнал** — иммутабельный лог всех событий системы (HTTP-запросы, действия сервисов)

## Стек технологий

| Технология | Назначение |
|------------|------------|
| FastAPI | Async REST API фреймворк |
| SQLAlchemy 2.0 | Async ORM (Mapped, mapped_column) |
| PostgreSQL | Основная БД (asyncpg) |
| Pydantic v2 | Валидация и сериализация |
| httpx | Async HTTP-клиент для интеграции с банком |
| Jinja2 | Шаблонизатор для веб-интерфейса |
