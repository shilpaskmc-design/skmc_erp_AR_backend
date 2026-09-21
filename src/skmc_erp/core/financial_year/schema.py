from calendar import monthrange
from datetime import date, datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from skmc_erp.core.financial_year.model import (
    FinancialYearStatus,
    FiscalYearPattern,
)


class CompanyFiscalSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fiscal_year_pattern: FiscalYearPattern
    custom_fiscal_year_start_month: int | None = Field(
        default=None,
        ge=1,
        le=12,
    )
    custom_fiscal_year_start_day: int | None = Field(
        default=None,
        ge=1,
        le=31,
    )

    @model_validator(mode="after")
    def validate_pattern_values(self) -> Self:
        if self.fiscal_year_pattern is FiscalYearPattern.CUSTOM:
            if (
                self.custom_fiscal_year_start_month is None
                or self.custom_fiscal_year_start_day is None
            ):
                raise ValueError(
                    "CUSTOM requires custom fiscal start month and day"
                )
            maximum_day = monthrange(
                2001,
                self.custom_fiscal_year_start_month,
            )[1]
            if self.custom_fiscal_year_start_day > maximum_day:
                raise ValueError(
                    "custom fiscal start must be valid in every calendar year"
                )
        elif (
            self.custom_fiscal_year_start_month is not None
            or self.custom_fiscal_year_start_day is not None
        ):
            raise ValueError(
                "preset fiscal patterns do not accept custom month or day"
            )

        return self


class CompanyFiscalSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_id: UUID
    fiscal_year_pattern: FiscalYearPattern
    start_month: int
    start_day: int
    created_at: datetime
    updated_at: datetime


class FinancialYearCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_year: int = Field(ge=1, le=9998)


class FinancialYearResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    display_code: str
    start_date: date
    end_date: date
    is_transition: bool
    status: FinancialYearStatus
    created_at: datetime
    updated_at: datetime
