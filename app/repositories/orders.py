import uuid

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.order import Order


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, order: Order) -> Order:
        self._session.add(order)
        await self._session.flush()
        return order

    async def get_by_id(self, order_id: uuid.UUID) -> Order | None:
        return await self._session.get(Order, order_id)

    async def get_by_number(self, number: str) -> Order | None:
        stmt = select(Order).where(Order.number == number)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_list(self) -> list[Order]:
        stmt = select(Order).order_by(Order.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def next_number(self) -> str:
        result = await self._session.execute(text("SELECT nextval('order_number_seq')"))
        val = result.scalar_one()
        return f"{val:04d}"
