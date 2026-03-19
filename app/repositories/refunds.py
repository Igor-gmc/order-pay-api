import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RefundStatus
from app.database.models.refund import Refund


class RefundRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, refund: Refund) -> Refund:
        self._session.add(refund)
        await self._session.flush()
        return refund

    async def get_by_payment_id(self, payment_id: uuid.UUID) -> list[Refund]:
        stmt = (
            select(Refund)
            .where(Refund.payment_id == payment_id)
            .order_by(Refund.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_refunded_amount(self, payment_id: uuid.UUID) -> Decimal:
        stmt = (
            select(func.coalesce(func.sum(Refund.amount), 0))
            .where(Refund.payment_id == payment_id)
            .where(Refund.status == RefundStatus.COMPLETED)
        )
        result = await self._session.execute(stmt)
        return Decimal(result.scalar_one())
