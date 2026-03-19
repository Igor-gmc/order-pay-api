import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.enums import RefundStatus


class RefundCreate(BaseModel):
    payment_id: uuid.UUID
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class RefundRead(BaseModel):
    id: uuid.UUID
    payment_id: uuid.UUID
    order_id: uuid.UUID
    amount: Decimal
    status: RefundStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RefundList(BaseModel):
    items: list[RefundRead]
    count: int
