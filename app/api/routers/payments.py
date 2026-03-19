from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import PaymentServiceDep
from app.integrations.bank.exceptions import (
    BankRequestError,
    BankUnavailableError,
)
from app.schemas.bank import AcquiringPaymentCreate
from app.schemas.payments import CashPaymentCreate, PaymentRead

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/cash", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def create_cash_payment(data: CashPaymentCreate, service: PaymentServiceDep):
    try:
        return await service.create_cash_payment(data)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            code = status.HTTP_404_NOT_FOUND
        else:
            code = status.HTTP_409_CONFLICT
        raise HTTPException(status_code=code, detail=msg)


@router.post("/acquiring", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def create_acquiring_payment(
    data: AcquiringPaymentCreate, service: PaymentServiceDep,
):
    try:
        return await service.create_acquiring_payment(data)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            code = status.HTTP_404_NOT_FOUND
        else:
            code = status.HTTP_409_CONFLICT
        raise HTTPException(status_code=code, detail=msg)
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
