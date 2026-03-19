from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.core.enums import BankPaymentStatus


class BankAcquiringStartRequest(BaseModel):
    order_number: str
    amount: Decimal


class BankAcquiringStartResponse(BaseModel):
    bank_payment_id: str
    status: BankPaymentStatus


class BankAcquiringCheckResponse(BaseModel):
    bank_payment_id: str
    status: BankPaymentStatus
    amount: Decimal
    paid_at: datetime | None = None
