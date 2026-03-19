import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class EventLogRead(BaseModel):
    id: uuid.UUID
    level: str
    source: str
    message: str
    payload_json: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EventLogList(BaseModel):
    items: list[EventLogRead]
    count: int
