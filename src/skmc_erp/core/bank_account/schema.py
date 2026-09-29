import re
from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    StringConstraints,
    field_validator,
    model_validator,
)
from stdnum import iban as stdnum_iban

from skmc_erp.core.bank_account.model import BankAccountType, CompanyBankAccountStatus

IFSC_PATTERN = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
SWIFT_PATTERN = re.compile(r"^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$")

RequiredString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
OptionalCurrencyCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^[A-Z]{3}$"),
]
CountryCodeString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Za-z]{2}$"),
]


def validate_account_type(v: str | None) -> str | None:
    if v is None:
        return None
    cleaned = v.strip().upper()
    if not cleaned:
        return None
    if cleaned not in BankAccountType.__members__:
        raise ValueError(
            f"Invalid account_type '{cleaned}'. Must be one of: {', '.join(sorted(BankAccountType.__members__.keys()))}"
        )
    return cleaned


def validate_swift(v: str | None) -> str | None:
    if v is None:
        return None
    cleaned = v.strip().upper()
    if not cleaned:
        return None
    if not SWIFT_PATTERN.match(cleaned):
        raise ValueError("Invalid SWIFT/BIC format")
    return cleaned


def validate_iban(v: str | None) -> str | None:
    if v is None:
        return None
    cleaned = v.replace(" ", "").upper()
    if not cleaned:
        return None
    if not stdnum_iban.is_valid(cleaned):
        raise ValueError("Invalid IBAN format or checksum")
    return cleaned


class CompanyBankAccountCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bank_country_code: CountryCodeString
    account_holder_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]
    bank_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]
    account_number: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)
    ]
    currency_code: OptionalCurrencyCode
    branch_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ] | None = None
    ifsc: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=11)
    ] | None = None
    swift: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=11)
    ] | None = None
    iban: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=34)
    ] | None = None
    account_type: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)
    ] | None = None
    gl_account_id: UUID | None = None
    is_default_for_billing: bool = False

    @field_validator("account_type", mode="before")
    @classmethod
    def _validate_acc_type(cls, v: str | None) -> str | None:
        return validate_account_type(v)

    @field_validator("swift", mode="before")
    @classmethod
    def _validate_swift_val(cls, v: str | None) -> str | None:
        return validate_swift(v)

    @field_validator("iban", mode="before")
    @classmethod
    def _validate_iban_val(cls, v: str | None) -> str | None:
        return validate_iban(v)

    @model_validator(mode="after")
    def _validate_ifsc(self) -> Self:
        if self.ifsc is not None:
            cleaned = self.ifsc.strip().upper()
            if self.bank_country_code == "IN" and not IFSC_PATTERN.match(cleaned):
                raise ValueError("Invalid IFSC format for Indian bank account")
            self.ifsc = cleaned
        return self


class CompanyBankAccountUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bank_country_code: CountryCodeString | None = None
    account_holder_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ] | None = None
    bank_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ] | None = None
    branch_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ] | None = None
    ifsc: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=11)
    ] | None = None
    swift: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=11)
    ] | None = None
    iban: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=34)
    ] | None = None
    account_type: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)
    ] | None = None
    gl_account_id: UUID | None = None
    is_default_for_billing: bool | None = None

    @field_validator("account_type", mode="before")
    @classmethod
    def _validate_acc_type(cls, v: str | None) -> str | None:
        return validate_account_type(v)

    @field_validator("swift", mode="before")
    @classmethod
    def _validate_swift_val(cls, v: str | None) -> str | None:
        return validate_swift(v)

    @field_validator("iban", mode="before")
    @classmethod
    def _validate_iban_val(cls, v: str | None) -> str | None:
        return validate_iban(v)

    @model_validator(mode="after")
    def _validate_ifsc(self) -> Self:
        if self.ifsc is not None:
            cleaned = self.ifsc.strip().upper()
            if self.bank_country_code == "IN" and not IFSC_PATTERN.match(cleaned):
                raise ValueError("Invalid IFSC format for Indian bank account")
            self.ifsc = cleaned
        return self


class CompanyBankAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    bank_country_code: str | None
    account_holder_name: str
    bank_name: str
    account_number: str
    branch_name: str | None
    ifsc: str | None
    swift: str | None
    iban: str | None
    currency_code: str
    account_type: str | None
    gl_account_id: UUID | None
    is_default_for_billing: bool
    status: CompanyBankAccountStatus
    created_at: datetime
    updated_at: datetime
