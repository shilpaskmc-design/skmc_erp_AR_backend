from datetime import date, datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from skmc_erp.core.tax_reference.model import HsnSacClassificationType, TaxReferenceStatus


def _nonblank(value: str) -> str:
    if not value.strip():
        raise ValueError("value must not be blank")
    return value


class CompanyHsnSacCodeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    classification_type: HsnSacClassificationType
    code: str = Field(max_length=20)
    description: str = Field(max_length=500)

    _code_nonblank = field_validator("code")(_nonblank)
    _description_nonblank = field_validator("description")(_nonblank)


class CompanyHsnSacCodeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(max_length=500)
    _description_nonblank = field_validator("description")(_nonblank)


class CompanyHsnSacCodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    classification_type: HsnSacClassificationType
    code: str
    description: str
    status: TaxReferenceStatus
    created_at: datetime
    updated_at: datetime


class CompanyHsnSacTaxRateCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tax_rate_id: UUID
    valid_from: date
    valid_to: date | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to must be on or after valid_from")
        return self


class CompanyHsnSacTaxRateEnd(BaseModel):
    model_config = ConfigDict(extra="forbid")
    end_date: date


class CompanyHsnSacTaxRateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_hsn_sac_code_id: UUID
    tax_rate_id: UUID
    valid_from: date
    valid_to: date | None
    status: TaxReferenceStatus
    created_at: datetime
    updated_at: datetime
