import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import RefundServiceDep
from app.schemas.refunds import RefundCreate, RefundList, RefundRead

router = APIRouter(tags=["refunds"])


@router.get(
    "/payments/{payment_id}/refunds",
    response_model=RefundList,
)
async def get_payment_refunds(
    payment_id: uuid.UUID, service: RefundServiceDep,
):
    try:
        return await service.get_by_payment(payment_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e),
        )


@router.post(
    "/refunds", response_model=RefundRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_refund(data: RefundCreate, service: RefundServiceDep):
    try:
        return await service.create_refund(data)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            code = status.HTTP_404_NOT_FOUND
        else:
            code = status.HTTP_409_CONFLICT
        raise HTTPException(status_code=code, detail=msg)
