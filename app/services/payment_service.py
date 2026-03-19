import uuid
from datetime import datetime, timezone

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import OrderPaymentStatus, PaymentStatus, PaymentType
from app.database.models.bank_payment_state import BankPaymentState
from app.database.models.order import Order
from app.database.models.payment import Payment
from app.integrations.bank.client import BankClient
from app.integrations.bank.schemas import BankAcquiringStartRequest
from app.repositories.bank_payments import BankPaymentRepository
from app.repositories.orders import OrderRepository
from app.repositories.payments import PaymentRepository
from app.schemas.bank import AcquiringPaymentCreate
from app.schemas.payments import CashPaymentCreate, PaymentList, PaymentRead
from app.services.log_service import LogService


class PaymentService:
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
        self._log = LogService(session)

    async def get_by_order(self, order_id: uuid.UUID) -> PaymentList:
        order = await self._orders.get_by_id(order_id)
        if order is None:
            raise ValueError(f"Order '{order_id}' not found")

        payments = await self._payments.get_by_order_id(order_id)
        items = [PaymentRead.model_validate(p) for p in payments]
        return PaymentList(items=items, count=len(items))

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

        await self._log.log_event(
            level="info",
            source="payment_service",
            message=f"Cash payment {data.amount} for order {order.number}, status: {order.payment_status.value}",
            payload={"payment_id": str(payment.id), "order_id": str(order.id),
                     "order_number": order.number, "amount": str(data.amount),
                     "order_status": order.payment_status.value},
        )

        return PaymentRead.model_validate(payment)

    async def create_acquiring_payment(
        self, data: AcquiringPaymentCreate,
    ) -> PaymentRead:
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

        bank_response = await self._bank.acquiring_start(
            BankAcquiringStartRequest(
                order_number=order.number,
                amount=data.amount,
            ),
        )

        payment = Payment(
            order_id=order.id,
            payment_type=PaymentType.ACQUIRING,
            amount=data.amount,
            status=PaymentStatus.PENDING,
            external_id=bank_response.bank_payment_id,
        )
        await self._payments.create(payment)

        bank_state = BankPaymentState(
            payment_id=payment.id,
            bank_payment_id=bank_response.bank_payment_id,
            bank_status=bank_response.status,
            bank_amount=data.amount,
            last_synced_at=datetime.now(timezone.utc),
        )
        await self._bank_payments.create(bank_state)

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
