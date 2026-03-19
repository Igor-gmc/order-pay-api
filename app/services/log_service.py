from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.event_log import EventLog
from app.repositories.logs import EventLogRepository
from app.schemas.logs import EventLogList, EventLogRead


class LogService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._logs = EventLogRepository(session)

    async def log_event(
        self,
        level: str,
        source: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        log = EventLog(
            level=level,
            source=source,
            message=message,
            payload_json=payload,
        )
        await self._logs.create(log)
        await self._session.commit()

    async def get_recent(self, limit: int = 100) -> EventLogList:
        logs = await self._logs.get_recent(limit=limit)
        items = [EventLogRead.model_validate(log) for log in logs]
        return EventLogList(items=items, count=len(items))
