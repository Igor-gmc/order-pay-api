import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import OrderPaymentStatus
from app.database.models.order import Order
from app.repositories.orders import OrderRepository
from app.schemas.orders import OrderCreate, OrderList, OrderRead


class OrderService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = OrderRepository(session)

    async def create(self, data: OrderCreate) -> OrderRead:
        number = await self._repo.next_number()

        order = Order(
            number=number,
            amount_total=data.amount_total,
            payment_status=OrderPaymentStatus.UNPAID,
            paid_amount=Decimal("0"),
            refunded_amount=Decimal("0"),
        )
        await self._repo.create(order)
        await self._session.commit()
        await self._session.refresh(order)
        return OrderRead.model_validate(order)

    async def get_by_id(self, order_id: uuid.UUID) -> OrderRead | None:
        order = await self._repo.get_by_id(order_id)
        if order is None:
            return None
        return OrderRead.model_validate(order)

    async def get_list(self) -> OrderList:
        orders = await self._repo.get_list()
        items = [OrderRead.model_validate(o) for o in orders]
        return OrderList(items=items, count=len(items))
