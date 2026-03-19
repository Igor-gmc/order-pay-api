from fastapi import APIRouter, Query

from app.api.dependencies import LogServiceDep
from app.schemas.logs import EventLogList

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("", response_model=EventLogList)
async def get_logs(
    service: LogServiceDep,
    limit: int = Query(default=100, ge=1, le=1000),
):
    return await service.get_recent(limit=limit)
