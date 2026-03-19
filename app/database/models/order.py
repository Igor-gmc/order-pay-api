import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Enum, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import OrderPaymentStatus
from app.database.base import Base

_enum_values = lambda e: [x.value for x in e]


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    amount_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False,
    )
    payment_status: Mapped[OrderPaymentStatus] = mapped_column(
        Enum(OrderPaymentStatus, values_callable=_enum_values),
        default=OrderPaymentStatus.UNPAID,
        server_default=OrderPaymentStatus.UNPAID.value,
    )
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), server_default="0",
    )
    refunded_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), server_default="0",
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )

    payments: Mapped[list["Payment"]] = relationship(back_populates="order")
    refunds: Mapped[list["Refund"]] = relationship(back_populates="order")
