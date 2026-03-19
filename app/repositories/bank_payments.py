import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.bank_payment_state import BankPaymentState


class BankPaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, state: BankPaymentState) -> BankPaymentState:
        self._session.add(state)
        await self._session.flush()
        return state

    async def get_by_payment_id(self, payment_id: uuid.UUID) -> BankPaymentState | None:
        stmt = select(BankPaymentState).where(
            BankPaymentState.payment_id == payment_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_bank_payment_id(self, bank_payment_id: str) -> BankPaymentState | None:
        stmt = select(BankPaymentState).where(
            BankPaymentState.bank_payment_id == bank_payment_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self) -> list[BankPaymentState]:
        stmt = (
            select(BankPaymentState)
            .order_by(BankPaymentState.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
