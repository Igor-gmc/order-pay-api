import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import (
    BankPaymentStatus,
    OrderPaymentStatus,
    PaymentStatus,
    PaymentType,
)
from app.database.models.order import Order
from app.integrations.bank.client import BankClient
from app.repositories.bank_payments import BankPaymentRepository
from app.repositories.orders import OrderRepository
from app.repositories.payments import PaymentRepository
from app.schemas.bank import BankPaymentStateList, BankPaymentStateRead
from app.schemas.payments import PaymentRead


_BANK_TO_LOCAL: dict[BankPaymentStatus, PaymentStatus] = {
    BankPaymentStatus.RECEIVED: PaymentStatus.PENDING,
    BankPaymentStatus.CONDUCTED: PaymentStatus.COMPLETED,
    BankPaymentStatus.CANCELLED: PaymentStatus.CANCELLED,
    BankPaymentStatus.REFUNDED: PaymentStatus.REFUNDED,
}

_CREDITED = frozenset({PaymentStatus.COMPLETED})
_DEBITED = frozenset({PaymentStatus.CANCELLED, PaymentStatus.REFUNDED})


class BankSyncService:
    def __init__(
        self,
        session: AsyncSession,
        bank_client: BankClient | None = None,
    ) -> None:
        self._session = session
        self._orders = OrderRepository(session)
        self._payments = PaymentRepository(session)
        self._bank_payments = BankPaymentRepository(session)
        self._bank = bank_client or BankClient()

    async def get_bank_states(self) -> BankPaymentStateList:
        states = await self._bank_payments.get_all()
        items = [BankPaymentStateRead.model_validate(s) for s in states]
        return BankPaymentStateList(items=items, count=len(items))

    async def get_bank_state(
        self, payment_id: uuid.UUID,
    ) -> BankPaymentStateRead:
        payment = await self._payments.get_by_id(payment_id)
        if payment is None:
            raise ValueError(f"Payment '{payment_id}' not found")

        if payment.payment_type != PaymentType.ACQUIRING:
            raise ValueError(
                f"Payment '{payment_id}' is not an acquiring payment"
            )

        bank_state = await self._bank_payments.get_by_payment_id(payment.id)
        if bank_state is None:
            raise ValueError(
                f"BankPaymentState for payment '{payment_id}' not found"
            )

        return BankPaymentStateRead.model_validate(bank_state)

    async def sync_one(self, payment_id: uuid.UUID) -> PaymentRead:
        payment = await self._payments.get_by_id(payment_id)
        if payment is None:
            raise ValueError(f"Payment '{payment_id}' not found")

        if payment.payment_type != PaymentType.ACQUIRING:
            raise ValueError(
                f"Payment '{payment_id}' is not an acquiring payment"
            )

        bank_state = await self._bank_payments.get_by_payment_id(payment.id)
        if bank_state is None:
            raise ValueError(
                f"BankPaymentState for payment '{payment_id}' not found"
            )

        bank_response = await self._bank.acquiring_check(
            bank_state.bank_payment_id,
        )

        old_status = payment.status
        new_status = _BANK_TO_LOCAL[bank_response.status]

        bank_state.bank_status = bank_response.status
        bank_state.bank_amount = bank_response.amount
        bank_state.bank_paid_at = bank_response.paid_at
        bank_state.last_synced_at = datetime.now(timezone.utc)
        bank_state.sync_error = None

        payment.status = new_status

        if new_status == PaymentStatus.COMPLETED:
            payment.paid_at = bank_response.paid_at

        order = await self._orders.get_by_id(payment.order_id)

        was_credited = old_status in _CREDITED
        now_credited = new_status in _CREDITED
        now_debited = new_status in _DEBITED

        if now_credited and not was_credited:
            self._credit_order(order, payment.amount)
        elif now_debited and was_credited:
            self._debit_order(order, payment.amount)

        await self._session.commit()
        await self._session.refresh(payment)
        return PaymentRead.model_validate(payment)

    @staticmethod
    def _credit_order(order: Order, amount: Decimal) -> None:
        order.paid_amount += amount
        _recalc_order_status(order)

    @staticmethod
    def _debit_order(order: Order, amount: Decimal) -> None:
        order.paid_amount -= amount
        _recalc_order_status(order)


def _recalc_order_status(order: Order) -> None:
    if order.paid_amount >= order.amount_total:
        order.payment_status = OrderPaymentStatus.PAID
    elif order.paid_amount > 0:
        order.payment_status = OrderPaymentStatus.PARTIALLY_PAID
    else:
        order.payment_status = OrderPaymentStatus.UNPAID
