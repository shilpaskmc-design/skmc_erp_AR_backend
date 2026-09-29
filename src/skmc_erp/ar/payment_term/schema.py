from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from skmc_erp.ar.payment_term.model import PaymentTermStatus, PaymentTermType


RequiredString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
OptionalCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50),
]


class PaymentTermCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
    ]
    code: OptionalCode
    term_type: PaymentTermType
    credit_days: Annotated[int, Field(ge=0, le=32767)]
    is_default: bool = False

    @field_validator("credit_days")
    @classmethod
    def validate_credit_days(cls, v: int, info) -> int:
        term_type = info.data.get("term_type")
        if term_type == PaymentTermType.IMMEDIATE and v != 0:
            raise ValueError("credit_days must be 0 for IMMEDIATE term type")
        if term_type == PaymentTermType.NET_DAYS and v <= 0:
            raise ValueError("credit_days must be > 0 for NET_DAYS term type")
        return v


class PaymentTermUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
    ] | None = None
    credit_days: Annotated[int, Field(ge=0, le=32767)] | None = None
    # term_type and code are stable.
    # Note: If credit_days is updated, it must still satisfy the database constraint:
    # (term_type = 'IMMEDIATE' AND credit_days = 0) OR (term_type = 'NET_DAYS' AND credit_days > 0).
    # We will enforce this in the service layer where term_type is available.
    is_default: bool | None = None


class PaymentTermResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    code: str
    term_type: PaymentTermType
    credit_days: int
    is_default: bool
    status: PaymentTermStatus
    created_at: datetime
    updated_at: datetime
