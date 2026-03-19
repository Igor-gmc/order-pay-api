import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.dependencies import LogServiceDep
from app.core.enums import BankPaymentStatus

router = APIRouter(prefix="/mock-bank", tags=["mock-bank"])

_payments: dict[str, dict] = {}
_online: dict[str, bool] = {"value": True}


class ModeResponse(BaseModel):
    online: bool


def _check_online():
    if not _online["value"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bank is offline",
        )


@router.get("/mode", response_model=ModeResponse)
async def get_mode():
    return ModeResponse(online=_online["value"])


@router.patch("/mode", response_model=ModeResponse)
async def set_mode(data: ModeResponse, log: LogServiceDep):
    _online["value"] = data.online
    mode = "online" if data.online else "offline"
    await log.log_event(
        level="warn" if not data.online else "info",
        source="bank_simulator",
        message=f"Bank switched to {mode}",
        payload={"online": data.online},
    )
    return ModeResponse(online=_online["value"])


class StartRequest(BaseModel):
    order_number: str
    amount: Decimal


class StartResponse(BaseModel):
    bank_payment_id: str
    status: BankPaymentStatus


class CheckResponse(BaseModel):
    bank_payment_id: str
    status: BankPaymentStatus
    amount: Decimal
    paid_at: datetime | None = None


@router.post("/acquiring/start", response_model=StartResponse)
async def acquiring_start(data: StartRequest):
    _check_online()
    bank_payment_id = f"bp-{uuid.uuid4().hex[:12]}"
    _payments[bank_payment_id] = {
        "bank_payment_id": bank_payment_id,
        "status": BankPaymentStatus.RECEIVED,
        "amount": data.amount,
        "paid_at": None,
    }
    return StartResponse(
        bank_payment_id=bank_payment_id,
        status=BankPaymentStatus.RECEIVED,
    )


@router.get("/acquiring/check/{bank_payment_id}", response_model=CheckResponse)
async def acquiring_check(bank_payment_id: str):
    _check_online()
    payment = _payments.get(bank_payment_id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bank payment '{bank_payment_id}' not found",
        )
    return CheckResponse(**payment)


class StatusUpdate(BaseModel):
    bank_status: BankPaymentStatus


@router.patch(
    "/payments/{bank_payment_id}/status",
    response_model=CheckResponse,
)
async def update_status(bank_payment_id: str, data: StatusUpdate, log: LogServiceDep):
    payment = _payments.get(bank_payment_id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bank payment '{bank_payment_id}' not found",
        )

    payment["status"] = data.bank_status

    if data.bank_status == BankPaymentStatus.CONDUCTED and payment["paid_at"] is None:
        payment["paid_at"] = datetime.now(timezone.utc)

    await log.log_event(
        level="info",
        source="bank_simulator",
        message=f"Bank payment {bank_payment_id} status changed to {data.bank_status.value}",
        payload={"bank_payment_id": bank_payment_id, "bank_status": data.bank_status.value},
    )

    return CheckResponse(**payment)
