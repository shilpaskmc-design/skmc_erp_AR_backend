from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from skmc_erp.core.company.schema import CompanyResponse


class CompanyImportIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sheet: str | None
    row: int | None = None
    column: str | None = None
    field: str | None = None
    message: str


class CompanyImportGap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    reason: str


class CompanyImportFieldPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    column: str
    current_value: Any
    proposed_value: Any
    changed: bool


class ImportClassification(StrEnum):
    NEW = "NEW"
    UNCHANGED = "UNCHANGED"
    SAFE_UPDATE = "SAFE_UPDATE"
    CONFLICT = "CONFLICT"


class FiscalSettingsImportPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fiscal_year_pattern: str
    start_month: int
    start_day: int
    classification: ImportClassification
    reason: str | None = None


class FinancialYearImportPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row: int
    start_year: int
    display_code: str
    start_date: date
    end_date: date
    classification: ImportClassification
    reason: str | None = None


class LocationImportPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row: int
    location_code: str | None
    location_name: str
    country_code: str
    subdivision_code: str | None
    classification: ImportClassification
    changed_fields: list[str] = Field(default_factory=list)
    reason: str | None = None
    code_will_be_generated: bool = False


class GSTRegistrationImportPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row: int
    gstin: str
    registered_legal_name: str | None
    subdivision_code: str
    registration_type_code: str | None
    valid_from: date | None
    valid_to: date | None
    classification: ImportClassification
    reason: str | None = None


class GSTLocationMappingImportPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row: int
    gstin: str
    location_code: str
    classification: ImportClassification
    reason: str | None = None


class CompanyImportPreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid: bool
    company_id: UUID
    sheet: str
    sheets: list[str] = Field(default_factory=list)
    normalized_values: dict[str, Any]
    fields: list[CompanyImportFieldPreview]
    update_fields: list[str]
    unchanged_fields: list[str]
    errors: list[CompanyImportIssue]
    unsupported_fields: list[CompanyImportGap]
    fiscal_settings: FiscalSettingsImportPreview | None = None
    financial_years: list[FinancialYearImportPreview] = Field(default_factory=list)
    locations: list[LocationImportPreview] = Field(default_factory=list)
    gst_registrations: list[GSTRegistrationImportPreview] = Field(
        default_factory=list
    )
    gst_location_mappings: list[GSTLocationMappingImportPreview] = Field(
        default_factory=list
    )
    preview_token: str | None
    expires_at: datetime | None


class CompanyImportApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preview_token: Annotated[
        str,
        StringConstraints(min_length=1, max_length=1_048_576),
    ]


class CompanyImportApplyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: CompanyResponse
    applied_fields: list[str]
    unchanged_fields: list[str]
    fiscal_settings: FiscalSettingsImportPreview | None = None
    financial_years: list[FinancialYearImportPreview] = Field(default_factory=list)
    locations: list[LocationImportPreview] = Field(default_factory=list)
    gst_registrations: list[GSTRegistrationImportPreview] = Field(
        default_factory=list
    )
    gst_location_mappings: list[GSTLocationMappingImportPreview] = Field(
        default_factory=list
    )
    no_changes: bool
