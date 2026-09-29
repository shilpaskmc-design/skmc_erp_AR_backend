from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

from skmc_erp.core.email.validator import validate_email as _validate_email

OptionalText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CompanyInvoiceDeliverySettingsPut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    automatic_sending_enabled: bool = False
    email_provider_config_id: UUID | None = None
    sender_email: str | None = None
    reply_to_email: str | None = None
    default_email_template_key: OptionalText | None = None
    default_cc: list[str] | None = None

    @field_validator("sender_email", "reply_to_email")
    @classmethod
    def validate_address(cls, value: str | None) -> str | None:
        return _validate_email(value)

    @field_validator("default_cc")
    @classmethod
    def validate_cc(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return [_validate_email(item) for item in value]  # type: ignore[misc]


class CompanyInvoiceDeliverySettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_id: UUID
    automatic_sending_enabled: bool
    email_provider_config_id: UUID | None
    sender_email: str | None
    reply_to_email: str | None
    default_email_template_key: str | None
    default_cc: list[str] | None
    created_at: datetime
    updated_at: datetime
