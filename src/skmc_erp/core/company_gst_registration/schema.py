from datetime import date, datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    StringConstraints,
    field_validator,
    model_validator,
)

from skmc_erp.core.company_gst_registration.model import (
    CompanyGSTRegistrationStatus,
)


GSTIN = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_upper=True,
        pattern=r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$",
    ),
]
SubdivisionCode = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^[A-Z]{2}-[A-Z0-9]{1,3}$",
        max_length=10,
    ),
]
RegisteredLegalName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]


class CompanyGSTRegistrationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gstin: GSTIN
    registered_legal_name: RegisteredLegalName | None = None
    gst_registration_type_id: UUID | None = None
    subdivision_code: SubdivisionCode
    valid_from: date | None = None
    valid_to: date | None = None

    @field_validator("gstin", mode="before")
    @classmethod
    def canonicalize_gstin(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @model_validator(mode="after")
    def validate_date_order(self) -> Self:
        if (
            self.valid_from is not None
            and self.valid_to is not None
            and self.valid_to < self.valid_from
        ):
            raise ValueError("valid_to must be on or after valid_from")
        return self


class CompanyGSTRegistrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    gstin: str
    registered_legal_name: str | None
    gst_registration_type_id: UUID | None
    subdivision_code: str
    valid_from: date | None
    valid_to: date | None
    status: CompanyGSTRegistrationStatus
    created_at: datetime
    updated_at: datetime


class CompanyGSTRegistrationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    registered_legal_name: RegisteredLegalName | None = None
    gst_registration_type_id: UUID | None = None
    valid_from: date | None = None
    valid_to: date | None = None
