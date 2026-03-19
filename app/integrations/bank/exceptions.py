class BankUnavailableError(Exception):
    """Банк недоступен (таймаут, сетевая ошибка)."""


class BankRequestError(Exception):
    """Банк вернул ошибку (не-2xx ответ)."""

    def __init__(self, status_code: int, detail: str = "") -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Bank returned {status_code}: {detail}")


class BankPaymentNotFoundError(Exception):
    """Платёж не найден в банке."""

    def __init__(self, bank_payment_id: str) -> None:
        self.bank_payment_id = bank_payment_id
        super().__init__(f"Bank payment '{bank_payment_id}' not found")
