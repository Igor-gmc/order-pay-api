import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import OrderPaymentStatus, PaymentStatus, RefundStatus
from app.database.models.order import Order
from app.database.models.payment import Payment
from app.database.models.refund import Refund
from app.repositories.orders import OrderRepository
from app.repositories.payments import PaymentRepository
from app.repositories.refunds import RefundRepository
from app.schemas.refunds import RefundCreate, RefundList, RefundRead
from app.services.log_service import LogService


class RefundService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._orders = OrderRepository(session)
        self._payments = PaymentRepository(session)
        self._refunds = RefundRepository(session)
        self._log = LogService(session)

    async def get_by_payment(self, payment_id: uuid.UUID) -> RefundList:
        payment = await self._payments.get_by_id(payment_id)
        if payment is None:
            raise ValueError(f"Payment '{payment_id}' not found")

        refunds = await self._refunds.get_by_payment_id(payment.id)
        items = [RefundRead.model_validate(r) for r in refunds]
        return RefundList(items=items, count=len(items))

    async def create_refund(self, data: RefundCreate) -> RefundRead:
        payment = await self._payments.get_by_id(data.payment_id)
        if payment is None:
            raise ValueError(f"Payment '{data.payment_id}' not found")

        refunded = await self._refunds.get_refunded_amount(payment.id)
        available = payment.amount - refunded
        if data.amount > available:
            raise ValueError(
                f"Refund amount {data.amount} exceeds available {available}"
            )

        refund = Refund(
            payment_id=payment.id,
            order_id=payment.order_id,
            amount=data.amount,
            status=RefundStatus.COMPLETED,
        )
        await self._refunds.create(refund)

        order = await self._orders.get_by_id(payment.order_id)
        self._update_payment_status(payment, refunded + data.amount)
        self._update_order_after_refund(order, data.amount)

        await self._session.commit()
        await self._session.refresh(refund)

        await self._log.log_event(
            level="info",
            source="refund_service",
            message=f"Refund {data.amount} for payment {payment.id}, payment: {payment.status.value}, order: {order.payment_status.value}",
            payload={"refund_id": str(refund.id), "payment_id": str(payment.id),
                     "order_id": str(order.id), "amount": str(data.amount),
                     "payment_status": payment.status.value,
                     "order_status": order.payment_status.value},
        )

        return RefundRead.model_validate(refund)

    @staticmethod
    def _update_payment_status(
        payment: Payment, total_refunded: Decimal,
    ) -> None:
        if total_refunded >= payment.amount:
            payment.status = PaymentStatus.REFUNDED
        else:
            payment.status = PaymentStatus.PART_REFUNDED

    @staticmethod
    def _update_order_after_refund(order: Order, refund_amount: Decimal) -> None:
        order.refunded_amount += refund_amount
        order.paid_amount -= refund_amount

        if order.paid_amount >= order.amount_total:
            order.payment_status = OrderPaymentStatus.PAID
        elif order.paid_amount > 0:
            order.payment_status = OrderPaymentStatus.PARTIALLY_PAID
        else:
            order.payment_status = OrderPaymentStatus.UNPAID
