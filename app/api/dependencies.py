from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_session
from app.services.bank_sync_service import BankSyncService
from app.services.log_service import LogService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.refund_service import RefundService

Session = Annotated[AsyncSession, Depends(get_session)]


async def get_order_service(
    session: Session,
) -> AsyncGenerator[OrderService, None]:
    yield OrderService(session)


async def get_payment_service(
    session: Session,
) -> AsyncGenerator[PaymentService, None]:
    yield PaymentService(session)


async def get_refund_service(
    session: Session,
) -> AsyncGenerator[RefundService, None]:
    yield RefundService(session)


async def get_bank_sync_service(
    session: Session,
) -> AsyncGenerator[BankSyncService, None]:
    yield BankSyncService(session)


async def get_log_service(
    session: Session,
) -> AsyncGenerator[LogService, None]:
    yield LogService(session)


OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]
PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]
RefundServiceDep = Annotated[RefundService, Depends(get_refund_service)]
BankSyncServiceDep = Annotated[BankSyncService, Depends(get_bank_sync_service)]
LogServiceDep = Annotated[LogService, Depends(get_log_service)]
