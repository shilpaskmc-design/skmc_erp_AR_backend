from datetime import datetime
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

from skmc_erp.core.company.model import CompanyBusinessNature, CompanyStatus


RequiredName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
OptionalDisplayName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]
OptionalEmail = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=320),
]
OptionalPhone = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=32),
]
OptionalWebsite = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=2048),
]
OptionalTimezone = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=64),
]
OptionalCountryCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^[A-Z]{2}$"),
]
OptionalCurrencyCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^[A-Z]{3}$"),
]


class CompanyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    legal_name: RequiredName
    organisation_id: UUID | None = None
    display_name: OptionalDisplayName | None = None
    entity_type_id: UUID | None = None
    country_code: OptionalCountryCode | None = None
    email: OptionalEmail | None = None
    phone: OptionalPhone | None = None
    website: OptionalWebsite | None = None
    base_timezone: OptionalTimezone | None = None
    base_currency_code: OptionalCurrencyCode | None = None
    business_nature: CompanyBusinessNature | None = None

    @field_validator("base_timezone")
    @classmethod
    def validate_base_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None

        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("base_timezone must be a valid IANA timezone") from exc

        return value


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    organisation_id: UUID | None
    legal_name: str
    display_name: str | None
    company_code: str
    entity_type_id: UUID | None
    country_code: str | None
    email: str | None
    phone: str | None
    website: str | None
    base_timezone: str | None
    base_currency_code: str | None
    business_nature: CompanyBusinessNature | None
    status: CompanyStatus
    created_at: datetime
    updated_at: datetime
