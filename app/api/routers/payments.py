from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import PaymentServiceDep
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
