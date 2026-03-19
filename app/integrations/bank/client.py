import httpx

from app.core.config import settings
from app.integrations.bank.exceptions import (
    BankPaymentNotFoundError,
    BankRequestError,
    BankUnavailableError,
)
from app.integrations.bank.schemas import (
    BankAcquiringCheckResponse,
    BankAcquiringStartRequest,
    BankAcquiringStartResponse,
)


class BankClient:
    def __init__(self, base_url: str = settings.bank_api_url) -> None:
        self._base_url = base_url.rstrip("/")

    async def acquiring_start(
        self, data: BankAcquiringStartRequest,
    ) -> BankAcquiringStartResponse:
        url = f"{self._base_url}/acquiring/start"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data.model_dump(mode="json"))
        except httpx.ConnectError as exc:
            raise BankUnavailableError(f"Cannot connect to bank: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise BankUnavailableError(f"Bank request timed out: {exc}") from exc

        if response.status_code != 200:
            raise BankRequestError(response.status_code, response.text)

        return BankAcquiringStartResponse.model_validate(response.json())

    async def acquiring_check(
        self, bank_payment_id: str,
    ) -> BankAcquiringCheckResponse:
        url = f"{self._base_url}/acquiring/check/{bank_payment_id}"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
        except httpx.ConnectError as exc:
            raise BankUnavailableError(f"Cannot connect to bank: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise BankUnavailableError(f"Bank request timed out: {exc}") from exc

        if response.status_code == 404:
            raise BankPaymentNotFoundError(bank_payment_id)

        if response.status_code != 200:
            raise BankRequestError(response.status_code, response.text)

        return BankAcquiringCheckResponse.model_validate(response.json())
