from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from skmc_erp.core.fx.model import ExchangeRateStatus, ExchangeRateType

CurrencyCode = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[A-Z]{3}$")]


class ExchangeRateCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_currency_code: CurrencyCode
    to_currency_code: CurrencyCode
    rate: Decimal = Field(gt=0, max_digits=28, decimal_places=12)
    rate_type: ExchangeRateType
    effective_from: date
    effective_to: date | None = None
    source: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)] | None = None

    @model_validator(mode="after")
    def validate_pair_and_dates(self) -> "ExchangeRateCreate":
        if self.from_currency_code == self.to_currency_code:
            raise ValueError("from_currency_code and to_currency_code must differ")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to must be on or after effective_from")
        return self


class ExchangeRateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    from_currency_code: str
    to_currency_code: str
    rate: Decimal
    rate_type: ExchangeRateType
    effective_from: date
    effective_to: date | None
    source: str | None
    status: ExchangeRateStatus
    created_at: datetime
    updated_at: datetime
