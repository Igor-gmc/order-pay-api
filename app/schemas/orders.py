import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.enums import OrderPaymentStatus


class OrderCreate(BaseModel):
    amount_total: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class OrderRead(BaseModel):
    id: uuid.UUID
    number: str
    amount_total: Decimal
    payment_status: OrderPaymentStatus
    paid_amount: Decimal
    refunded_amount: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderList(BaseModel):
    items: list[OrderRead]
    count: int
