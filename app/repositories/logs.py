from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.event_log import EventLog


class EventLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, log: EventLog) -> EventLog:
        self._session.add(log)
        await self._session.flush()
        return log

    async def get_recent(self, limit: int = 100) -> list[EventLog]:
        stmt = (
            select(EventLog)
            .order_by(EventLog.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
