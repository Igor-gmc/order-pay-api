import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.enums import BankPaymentStatus


class AcquiringPaymentCreate(BaseModel):
    order_id: uuid.UUID
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class BankPaymentStateRead(BaseModel):
    payment_id: uuid.UUID
    bank_payment_id: str
    bank_status: BankPaymentStatus
    bank_amount: Decimal
    bank_paid_at: datetime | None
    last_synced_at: datetime
    sync_error: str | None

    model_config = {"from_attributes": True}


class BankPaymentStateList(BaseModel):
    items: list[BankPaymentStateRead]
    count: int
