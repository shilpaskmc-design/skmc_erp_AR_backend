from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

from skmc_erp.ar.currency.model import CompanyARCurrencyStatus


OptionalCurrencyCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^[A-Z]{3}$"),
]


class CompanyARCurrencyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency_code: OptionalCurrencyCode
    billing_enabled: bool = False
    receipt_enabled: bool = False
    is_default_billing: bool = False
    is_default_receipt: bool = False


class CompanyARCurrencyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    billing_enabled: bool | None = None
    receipt_enabled: bool | None = None
    is_default_billing: bool | None = None
    is_default_receipt: bool | None = None


class CompanyARCurrencyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    currency_code: str
    billing_enabled: bool
    receipt_enabled: bool
    is_default_billing: bool
    is_default_receipt: bool
    status: CompanyARCurrencyStatus
    created_at: datetime
    updated_at: datetime
