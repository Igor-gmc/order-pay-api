import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import OrderServiceDep
from app.schemas.orders import OrderCreate, OrderList, OrderRead

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(data: OrderCreate, service: OrderServiceDep):
    try:
        return await service.create(data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("", response_model=OrderList)
async def get_orders(service: OrderServiceDep):
    return await service.get_list()


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(order_id: uuid.UUID, service: OrderServiceDep):
    order = await service.get_by_id(order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_id}' not found",
        )
    return order
