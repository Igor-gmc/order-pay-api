import logging
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.order import Order
from app.schemas.orders import OrderCreate
from app.schemas.payments import CashPaymentCreate
from app.schemas.bank import AcquiringPaymentCreate
from app.schemas.refunds import RefundCreate
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.refund_service import RefundService

logger = logging.getLogger(__name__)


async def seed_if_empty(session: AsyncSession) -> None:
    """Заполняет БД демо-данными, если таблица orders пуста."""
    try:
        count = await session.scalar(select(func.count()).select_from(Order))
        if count and count > 0:
            return

        order_svc = OrderService(session)
        payment_svc = PaymentService(session)
        refund_svc = RefundService(session)

        # Заказ 1 (500.00) — полная оплата наличными + частичный возврат
        order1 = await order_svc.create(OrderCreate(amount_total=Decimal("500.00")))
        pay1 = await payment_svc.create_cash_payment(
            CashPaymentCreate(order_id=order1.id, amount=Decimal("500.00")),
        )
        await refund_svc.create_refund(
            RefundCreate(payment_id=pay1.id, amount=Decimal("150.00")),
        )

        # Заказ 2 (1000.00) — частичная оплата наличными
        order2 = await order_svc.create(OrderCreate(amount_total=Decimal("1000.00")))
        await payment_svc.create_cash_payment(
            CashPaymentCreate(order_id=order2.id, amount=Decimal("400.00")),
        )

        # Заказ 3 (750.00) — оплата картой (pending, ждёт sync)
        order3 = await order_svc.create(OrderCreate(amount_total=Decimal("750.00")))
        await payment_svc.create_acquiring_payment(
            AcquiringPaymentCreate(order_id=order3.id, amount=Decimal("750.00")),
        )

        # Заказ 4 (250.00) — без оплат
        await order_svc.create(OrderCreate(amount_total=Decimal("250.00")))

        logger.info("Seed data created: 4 orders, 3 payments, 1 refund")
    except Exception:
        logger.warning("Failed to seed demo data", exc_info=True)
