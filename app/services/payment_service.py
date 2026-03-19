from datetime import datetime, timezone

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import OrderPaymentStatus, PaymentStatus, PaymentType
from app.database.models.order import Order
from app.database.models.payment import Payment
from app.repositories.orders import OrderRepository
from app.repositories.payments import PaymentRepository
from app.schemas.payments import CashPaymentCreate, PaymentRead


class PaymentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._orders = OrderRepository(session)
        self._payments = PaymentRepository(session)

    async def create_cash_payment(self, data: CashPaymentCreate) -> PaymentRead:
        order = await self._orders.get_by_id(data.order_id)
        if order is None:
            raise ValueError(f"Order '{data.order_id}' not found")

        if order.payment_status == OrderPaymentStatus.PAID:
            raise ValueError(f"Order '{order.number}' is already fully paid")

        remaining = order.amount_total - order.paid_amount
        if data.amount > remaining:
            raise ValueError(
                f"Payment amount {data.amount} exceeds remaining {remaining}"
            )

        payment = Payment(
            order_id=order.id,
            payment_type=PaymentType.CASH,
            amount=data.amount,
            status=PaymentStatus.COMPLETED,
            paid_at=datetime.now(timezone.utc),
        )
        await self._payments.create(payment)

        self._update_order_totals(order, data.amount)

        await self._session.commit()
        await self._session.refresh(payment)
        return PaymentRead.model_validate(payment)

    @staticmethod
    def _update_order_totals(order: Order, paid: Decimal) -> None:
        order.paid_amount += paid
        if order.paid_amount >= order.amount_total:
            order.payment_status = OrderPaymentStatus.PAID
        elif order.paid_amount > 0:
            order.payment_status = OrderPaymentStatus.PARTIALLY_PAID
        else:
            order.payment_status = OrderPaymentStatus.UNPAID
