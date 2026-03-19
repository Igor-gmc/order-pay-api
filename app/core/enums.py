from enum import StrEnum


class PaymentType(StrEnum):
    CASH = "cash"
    ACQUIRING = "acquiring"


class OrderPaymentStatus(StrEnum):
    UNPAID = "unpaid"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PART_REFUNDED = "part_refunded"
    REFUNDED = "refunded"
    FAILED = "failed"


class BankPaymentStatus(StrEnum):
    RECEIVED = "received"
    CONDUCTED = "conducted"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class RefundStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
