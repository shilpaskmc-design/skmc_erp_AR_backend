from datetime import date, datetime
from typing import Annotated
from urllib.parse import urlparse
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import phonenumbers
from pydantic import (
    BaseModel,
    ConfigDict,
    StringConstraints,
    field_validator,
    model_validator,
)

from skmc_erp.core.company.model import CompanyBusinessNature, CompanyStatus
from skmc_erp.core.email.validator import validate_email


def validate_website(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if len(value) > 2048:
        raise ValueError("website URL exceeds maximum length of 2048 characters")
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("website must use http or https scheme")
    if not parsed.netloc:
        raise ValueError("invalid website URL format")
    return value


def validate_phone(value: str | None, default_country: str | None = None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        parsed = phonenumbers.parse(value, default_country)
    except phonenumbers.NumberParseException as exc:
        raise ValueError("invalid phone number") from exc
    if not phonenumbers.is_valid_number(parsed):
        raise ValueError("invalid phone number")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


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

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, value: str | None) -> str | None:
        return validate_email(value)

    @field_validator("website")
    @classmethod
    def validate_website_field(cls, value: str | None) -> str | None:
        return validate_website(value)

    @model_validator(mode="after")
    def validate_phone_and_country(self) -> "CompanyCreate":
        if self.phone is not None:
            self.phone = validate_phone(self.phone, self.country_code)
        return self

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


class CompanyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    legal_name: RequiredName | None = None
    display_name: OptionalDisplayName | None = None
    email: OptionalEmail | None = None
    phone: OptionalPhone | None = None
    website: OptionalWebsite | None = None
    base_timezone: OptionalTimezone | None = None
    business_nature: CompanyBusinessNature | None = None

    @field_validator("legal_name")
    @classmethod
    def reject_null_legal_name(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("legal_name cannot be null")
        return value

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, value: str | None) -> str | None:
        return validate_email(value)

    @field_validator("website")
    @classmethod
    def validate_website_field(cls, value: str | None) -> str | None:
        return validate_website(value)

    @field_validator("phone")
    @classmethod
    def validate_phone_field(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if value.startswith("+"):
            return validate_phone(value)
        return value

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


class CompanyLegalNameVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    legal_name: str
    valid_from: date
    valid_to: date | None
    created_at: datetime
