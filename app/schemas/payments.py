import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.enums import PaymentStatus, PaymentType


class CashPaymentCreate(BaseModel):
    order_id: uuid.UUID
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class PaymentRead(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    payment_type: PaymentType
    amount: Decimal
    status: PaymentStatus
    external_id: str | None
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaymentList(BaseModel):
    items: list[PaymentRead]
    count: int
