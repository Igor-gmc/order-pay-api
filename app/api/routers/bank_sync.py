import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import BankSyncServiceDep
from app.integrations.bank.exceptions import (
    BankPaymentNotFoundError,
    BankRequestError,
    BankUnavailableError,
)
from app.schemas.bank import BankPaymentStateList, BankPaymentStateRead
from app.schemas.payments import PaymentRead

router = APIRouter(prefix="/bank", tags=["bank"])


@router.get(
    "/payments",
    response_model=BankPaymentStateList,
)
async def get_bank_payment_states(service: BankSyncServiceDep):
    return await service.get_bank_states()


@router.get(
    "/payments/{payment_id}",
    response_model=BankPaymentStateRead,
)
async def get_bank_payment_state(
    payment_id: uuid.UUID, service: BankSyncServiceDep,
):
    try:
        return await service.get_bank_state(payment_id)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            code = status.HTTP_404_NOT_FOUND
        else:
            code = status.HTTP_409_CONFLICT
        raise HTTPException(status_code=code, detail=msg)


@router.post(
    "/sync/{payment_id}",
    response_model=PaymentRead,
    status_code=status.HTTP_200_OK,
)
async def sync_payment(
    payment_id: uuid.UUID, service: BankSyncServiceDep,
):
    try:
        return await service.sync_one(payment_id)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            code = status.HTTP_404_NOT_FOUND
        else:
            code = status.HTTP_409_CONFLICT
        raise HTTPException(status_code=code, detail=msg)
    except BankPaymentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except BankUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except BankRequestError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )
