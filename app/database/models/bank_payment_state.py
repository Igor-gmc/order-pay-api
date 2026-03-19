import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import BankPaymentStatus
from app.database.base import Base

_enum_values = lambda e: [x.value for x in e]


class BankPaymentState(Base):
    __tablename__ = "bank_payment_states"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    bank_payment_id: Mapped[str] = mapped_column(
        String(128), nullable=False,
    )
    bank_status: Mapped[BankPaymentStatus] = mapped_column(
        Enum(BankPaymentStatus, values_callable=_enum_values),
        nullable=False,
    )
    bank_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    bank_paid_at: Mapped[datetime | None] = mapped_column(default=None)
    last_synced_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
    )
    sync_error: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )

    payment: Mapped["Payment"] = relationship(back_populates="bank_payment_state")
