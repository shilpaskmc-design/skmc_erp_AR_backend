from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from skmc_erp.core.company_location.model import CompanyLocationStatus


LocationName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=150),
]
AddressLine = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
CityOrDistrict = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
CountryCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^[A-Z]{2}$"),
]
SubdivisionCode = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^[A-Z]{2}-[A-Z0-9]{1,3}$",
        max_length=10,
    ),
]
PostalCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=20),
]
OtherPurpose = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=150),
]


class CompanyLocationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location_name: LocationName
    address_line_1: AddressLine
    address_line_2: AddressLine | None = None
    city: CityOrDistrict
    district: CityOrDistrict | None = None
    subdivision_code: SubdivisionCode | None = None
    country_code: CountryCode
    postal_code: PostalCode | None = None
    is_registered_office: bool = False
    is_corporate_office: bool = False
    is_branch: bool = False
    is_billing_office: bool = False
    is_warehouse: bool = False
    other_purpose: OtherPurpose | None = None

    @model_validator(mode="after")
    def require_at_least_one_purpose(self) -> Self:
        if not (
            self.is_registered_office
            or self.is_corporate_office
            or self.is_branch
            or self.is_billing_office
            or self.is_warehouse
            or self.other_purpose is not None
        ):
            raise ValueError("at least one Location purpose must be selected")

        return self


class CompanyLocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    location_name: str
    address_line_1: str
    address_line_2: str | None
    city: str
    district: str | None
    subdivision_code: str | None
    country_code: str
    postal_code: str | None
    is_registered_office: bool
    is_corporate_office: bool
    is_branch: bool
    is_billing_office: bool
    is_warehouse: bool
    other_purpose: str | None
    status: CompanyLocationStatus
    created_at: datetime
    updated_at: datetime
