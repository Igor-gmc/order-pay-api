from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_session
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService

Session = Annotated[AsyncSession, Depends(get_session)]


async def get_order_service(
    session: Session,
) -> AsyncGenerator[OrderService, None]:
    yield OrderService(session)


async def get_payment_service(
    session: Session,
) -> AsyncGenerator[PaymentService, None]:
    yield PaymentService(session)


OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]
PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]
