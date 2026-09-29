import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.core.company.model import Company
from skmc_erp.core.company.schema import CompanyResponse, CompanyUpdate, validate_phone
from skmc_erp.core.company.service import CompanyStateConflictError, update_company
from skmc_erp.core.company_import.schema import (
    CompanyImportApplyResponse,
    CompanyImportFieldPreview,
    CompanyImportGap,
    CompanyImportIssue,
    CompanyImportPreviewResponse,
    FinancialYearImportPreview,
    FiscalSettingsImportPreview,
    GSTLocationMappingImportPreview,
    GSTRegistrationImportPreview,
    ImportClassification,
    LocationImportPreview,
)
from skmc_erp.core.company_import.token import (
    PreviewTokenError,
    create_preview_token,
    read_preview_token,
)
from skmc_erp.core.company_import.workbook import (
    FIELD_TO_COLUMN,
    FINANCIAL_YEAR_FIELD_TO_COLUMN,
    FINANCIAL_YEARS_SHEET,
    GST_LOCATION_MAPPING_FIELD_TO_COLUMN,
    GST_LOCATION_MAPPINGS_SHEET,
    GST_REGISTRATION_FIELD_TO_COLUMN,
    GST_REGISTRATIONS_SHEET,
    LOCATION_FIELD_TO_COLUMN,
    LOCATIONS_SHEET,
    SHEET_NAME,
    ParsedCompanyWorkbook,
    ParsedWorkbookRow,
    parse_company_workbook,
)
from skmc_erp.core.company_gst_registration.model import (
    CompanyGSTRegistration,
    CompanyGSTRegistrationStatus,
    GSTRegistrationType,
    GSTRegistrationTypeStatus,
)
from skmc_erp.core.company_gst_registration.schema import (
    CompanyGSTRegistrationCreate,
    GSTIN,
)
from skmc_erp.core.company_gst_registration.service import (
    create_company_gst_registration,
)
from skmc_erp.core.company_location.model import (
    CompanyLocation,
    CompanyLocationStatus,
)
from skmc_erp.core.company_location.schema import (
    CompanyLocationCreate,
    CompanyLocationUpdate,
    LocationCode,
)
from skmc_erp.core.company_location.service import (
    ADDRESS_FIELDS,
    create_company_location,
    update_company_location,
)
from skmc_erp.core.financial_year.model import (
    CompanyFiscalSettings,
    FinancialYear,
)
from skmc_erp.core.financial_year.schema import (
    CompanyFiscalSettingsUpdate,
    FinancialYearCreate,
)
from skmc_erp.core.financial_year.service import (
    calculate_financial_year_dates,
    configure_company_fiscal_settings,
    create_financial_year,
    generate_financial_year_code,
    resolve_fiscal_start,
)
from skmc_erp.core.geography.model import (
    Country,
    CountryStatus,
    CountrySubdivision,
    CountrySubdivisionStatus,
)
from skmc_erp.core.tenant.model import Tenant


SUPPORTED_FIELDS = tuple(FIELD_TO_COLUMN)
LOCATION_IMPORT_FIELDS = (
    "location_name",
    "address_line_1",
    "address_line_2",
    "city",
    "district",
    "country_code",
    "subdivision_code",
    "postal_code",
    "is_registered_office",
    "is_corporate_office",
    "is_branch",
    "is_billing_office",
    "is_warehouse",
    "other_purpose",
)
LOCATION_ADDRESS_FIELDS = tuple(ADDRESS_FIELDS)
UNSUPPORTED_FIELDS = [
    CompanyImportGap(
        field="country",
        reason="Country is not supported by the current Company update contract.",
    ),
    CompanyImportGap(
        field="entity_type",
        reason="Entity Type is not supported by the current Company update contract.",
    ),
    CompanyImportGap(
        field="base_currency",
        reason="Base Currency is not supported by the current Company update contract.",
    ),
    CompanyImportGap(
        field="msme_details",
        reason="MSME fields are not implemented on the current Company model.",
    ),
    CompanyImportGap(
        field="legal_identifiers",
        reason=(
            "Generic Company legal-identifier persistence and authoritative "
            "applicability rules are not implemented."
        ),
    ),
]
GSTIN_ADAPTER = TypeAdapter(GSTIN)
LOCATION_CODE_ADAPTER = TypeAdapter(LocationCode)


class CompanyImportValidationError(Exception):
    def __init__(self, issues: list[CompanyImportIssue]) -> None:
        super().__init__(issues[0].message if issues else "Invalid Company import")
        self.issues = issues


@dataclass(frozen=True)
class NormalizedFinancialYear:
    row: int
    start_year: int


@dataclass(frozen=True)
class NormalizedLocation:
    row: int
    data: CompanyLocationCreate


@dataclass(frozen=True)
class NormalizedGSTRegistration:
    row: int
    data: CompanyGSTRegistrationCreate
    registration_type_code: str | None


@dataclass(frozen=True)
class NormalizedGSTLocationMapping:
    row: int
    gstin: str
    location_code: str


@dataclass(frozen=True)
class ClassifiedLocation:
    preview: LocationImportPreview
    matched: CompanyLocation | None


@dataclass(frozen=True)
class ClassifiedGSTRegistration:
    preview: GSTRegistrationImportPreview
    matched: CompanyGSTRegistration | None


@dataclass(frozen=True)
class ClassifiedGSTLocationMapping:
    preview: GSTLocationMappingImportPreview


@dataclass(frozen=True)
class ClassifiedImport:
    company_update: CompanyUpdate | None
    company_fields: list[CompanyImportFieldPreview]
    company_update_fields: list[str]
    company_unchanged_fields: list[str]
    fiscal_settings_data: CompanyFiscalSettingsUpdate | None
    fiscal_settings_preview: FiscalSettingsImportPreview | None
    financial_years: list[FinancialYearImportPreview]
    locations: list[ClassifiedLocation]
    gst_registrations: list[ClassifiedGSTRegistration]
    gst_location_mappings: list[ClassifiedGSTLocationMapping]

    @property
    def has_conflicts(self) -> bool:
        return any(
            row.classification is ImportClassification.CONFLICT
            for row in self.financial_years
        ) or any(
            row.preview.classification is ImportClassification.CONFLICT
            for row in self.locations
        ) or any(
            row.preview.classification is ImportClassification.CONFLICT
            for row in self.gst_registrations
        ) or any(
            row.preview.classification is ImportClassification.CONFLICT
            for row in self.gst_location_mappings
        )

    @property
    def has_changes(self) -> bool:
        fiscal_change = (
            self.fiscal_settings_preview is not None
            and self.fiscal_settings_preview.classification
            in {ImportClassification.NEW, ImportClassification.SAFE_UPDATE}
        )
        return bool(self.company_update_fields) or fiscal_change or any(
            row.classification is ImportClassification.NEW
            for row in self.financial_years
        ) or any(
            row.preview.classification
            in {ImportClassification.NEW, ImportClassification.SAFE_UPDATE}
            for row in self.locations
        ) or any(
            row.preview.classification is ImportClassification.NEW
            for row in self.gst_registrations
        ) or any(
            row.preview.classification is ImportClassification.SAFE_UPDATE
            for row in self.gst_location_mappings
        )


def _json_value(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, (date,)):
        return value.isoformat()
    return value


def _hash_state(state: Any) -> str:
    return hashlib.sha256(
        json.dumps(state, sort_keys=True, separators=(",", ":"), default=_json_value).encode(
            "utf-8"
        )
    ).hexdigest()


async def configuration_fingerprint(
    session: AsyncSession, company: Company
) -> str:
    settings = await session.get(CompanyFiscalSettings, company.id)
    financial_years = (
        await session.scalars(
            select(FinancialYear)
            .where(FinancialYear.company_id == company.id)
            .order_by(FinancialYear.start_date, FinancialYear.id)
        )
    ).all()
    locations = (
        await session.scalars(
            select(CompanyLocation)
            .where(CompanyLocation.company_id == company.id)
            .order_by(CompanyLocation.location_code, CompanyLocation.id)
        )
    ).all()
    gst_registrations = (
        await session.scalars(
            select(CompanyGSTRegistration)
            .where(CompanyGSTRegistration.company_id == company.id)
            .order_by(CompanyGSTRegistration.gstin, CompanyGSTRegistration.id)
        )
    ).all()
    state = {
        "company": {
            **{field: _json_value(getattr(company, field)) for field in SUPPORTED_FIELDS},
            "updated_at": company.updated_at.isoformat(),
        },
        "fiscal_settings": (
            None
            if settings is None
            else {
                "pattern": settings.fiscal_year_pattern.value,
                "start_month": settings.start_month,
                "start_day": settings.start_day,
                "updated_at": settings.updated_at.isoformat(),
            }
        ),
        "financial_years": [
            {
                "id": str(row.id),
                "start_date": row.start_date.isoformat(),
                "end_date": row.end_date.isoformat(),
                "display_code": row.display_code,
                "is_transition": row.is_transition,
                "status": row.status.value,
                "updated_at": row.updated_at.isoformat(),
            }
            for row in financial_years
        ],
        "locations": [
            {
                "id": str(row.id),
                "location_code": row.location_code,
                "gst_registration_id": (
                    None
                    if row.gst_registration_id is None
                    else str(row.gst_registration_id)
                ),
                **{
                    field: _json_value(getattr(row, field))
                    for field in LOCATION_IMPORT_FIELDS
                },
                "status": row.status.value,
                "updated_at": row.updated_at.isoformat(),
            }
            for row in locations
        ],
        "gst_registrations": [
            {
                "id": str(row.id),
                "gstin": row.gstin,
                "registered_legal_name": row.registered_legal_name,
                "gst_registration_type_id": (
                    None
                    if row.gst_registration_type_id is None
                    else str(row.gst_registration_type_id)
                ),
                "subdivision_code": row.subdivision_code,
                "valid_from": _json_value(row.valid_from),
                "valid_to": _json_value(row.valid_to),
                "status": row.status.value,
                "updated_at": row.updated_at.isoformat(),
            }
            for row in gst_registrations
        ],
    }
    return _hash_state(state)


def _pydantic_issues(
    error: ValidationError,
    *,
    sheet: str,
    row: int,
    columns: dict[str, str],
) -> list[CompanyImportIssue]:
    issues: list[CompanyImportIssue] = []
    for detail in error.errors(include_url=False):
        field = str(detail["loc"][0]) if detail.get("loc") else None
        message = str(detail["msg"])
        if message.startswith("Value error, "):
            message = message.removeprefix("Value error, ")
        issues.append(
            CompanyImportIssue(
                sheet=sheet,
                row=row,
                column=columns.get(field or ""),
                field=field,
                message=message,
            )
        )
    return issues


def validate_and_normalize_values(
    values: dict[str, Any], *, company: Company
) -> tuple[CompanyUpdate | None, list[CompanyImportIssue]]:
    try:
        company_update = CompanyUpdate.model_validate(values)
    except ValidationError as exc:
        return None, _pydantic_issues(
            exc, sheet=SHEET_NAME, row=2, columns=FIELD_TO_COLUMN
        )
    if company_update.phone is not None:
        try:
            company_update.phone = validate_phone(
                company_update.phone, company.country_code
            )
        except ValueError:
            return None, [
                CompanyImportIssue(
                    sheet=SHEET_NAME,
                    row=2,
                    column=FIELD_TO_COLUMN["phone"],
                    field="phone",
                    message="invalid phone number for the Company's country context",
                )
            ]
    return company_update, []


def _integer(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{field} must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        text_value = value.strip()
        if text_value.isdigit():
            return int(text_value)
    raise ValueError(f"{field} must be an integer")


def _normalize_financial_years(
    rows: list[ParsedWorkbookRow],
) -> tuple[CompanyFiscalSettingsUpdate | None, list[NormalizedFinancialYear], list[CompanyImportIssue]]:
    if not rows:
        return None, [], []
    settings: CompanyFiscalSettingsUpdate | None = None
    normalized: list[NormalizedFinancialYear] = []
    issues: list[CompanyImportIssue] = []
    seen_years: set[int] = set()
    for row in rows:
        raw = row.values
        try:
            pattern_value = raw["fiscal_year_pattern"]
            if not isinstance(pattern_value, str) or not pattern_value.strip():
                raise ValueError("Fiscal Year Pattern is required")
            pattern = pattern_value.strip().upper()
            month = (
                None
                if raw["custom_fiscal_year_start_month"] is None
                else _integer(
                    raw["custom_fiscal_year_start_month"],
                    field="Custom Start Month",
                )
            )
            day = (
                None
                if raw["custom_fiscal_year_start_day"] is None
                else _integer(
                    raw["custom_fiscal_year_start_day"], field="Custom Start Day"
                )
            )
            candidate = CompanyFiscalSettingsUpdate.model_validate(
                {
                    "fiscal_year_pattern": pattern,
                    "custom_fiscal_year_start_month": month,
                    "custom_fiscal_year_start_day": day,
                }
            )
            start_year = FinancialYearCreate.model_validate(
                {"start_year": _integer(raw["start_year"], field="Start Year")}
            ).start_year
        except ValueError as exc:
            issues.append(
                CompanyImportIssue(
                    sheet=FINANCIAL_YEARS_SHEET,
                    row=row.row,
                    message=str(exc),
                )
            )
            continue
        except ValidationError as exc:
            issues.extend(
                _pydantic_issues(
                    exc,
                    sheet=FINANCIAL_YEARS_SHEET,
                    row=row.row,
                    columns=FINANCIAL_YEAR_FIELD_TO_COLUMN,
                )
            )
            continue
        if settings is None:
            settings = candidate
        elif settings.model_dump() != candidate.model_dump():
            issues.append(
                CompanyImportIssue(
                    sheet=FINANCIAL_YEARS_SHEET,
                    row=row.row,
                    column="Fiscal Year Pattern",
                    field="fiscal_year_pattern",
                    message="All Financial Years rows must use the same fiscal settings",
                )
            )
        if start_year in seen_years:
            issues.append(
                CompanyImportIssue(
                    sheet=FINANCIAL_YEARS_SHEET,
                    row=row.row,
                    column="Start Year",
                    field="start_year",
                    message=f"Duplicate Start Year '{start_year}'",
                )
            )
        else:
            seen_years.add(start_year)
            normalized.append(NormalizedFinancialYear(row=row.row, start_year=start_year))
    return settings, normalized, issues


def _yes_no(value: Any, *, field: str) -> bool:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be YES or NO")
    normalized = value.strip().upper()
    if normalized == "YES":
        return True
    if normalized == "NO":
        return False
    raise ValueError(f"{field} must be YES or NO")


async def _normalize_locations(
    session: AsyncSession, rows: list[ParsedWorkbookRow]
) -> tuple[list[NormalizedLocation], list[CompanyImportIssue]]:
    normalized: list[NormalizedLocation] = []
    issues: list[CompanyImportIssue] = []
    boolean_fields = {
        "is_registered_office": "Registered Office",
        "is_corporate_office": "Corporate Office",
        "is_branch": "Branch",
        "is_billing_office": "Billing Office",
        "is_warehouse": "Warehouse",
    }
    for row in rows:
        values = dict(row.values)
        try:
            for field, header in boolean_fields.items():
                values[field] = _yes_no(values[field], field=header)
            for field in ("location_code", "country_code", "subdivision_code"):
                value = values[field]
                if isinstance(value, str):
                    values[field] = value.strip().upper() or None
            data = CompanyLocationCreate.model_validate(values)
        except ValueError as exc:
            issues.append(
                CompanyImportIssue(
                    sheet=LOCATIONS_SHEET,
                    row=row.row,
                    message=str(exc),
                )
            )
            continue
        except ValidationError as exc:
            issues.extend(
                _pydantic_issues(
                    exc,
                    sheet=LOCATIONS_SHEET,
                    row=row.row,
                    columns=LOCATION_FIELD_TO_COLUMN,
                )
            )
            continue

        country = await session.get(Country, data.country_code)
        if country is None:
            issues.append(
                CompanyImportIssue(
                    sheet=LOCATIONS_SHEET,
                    row=row.row,
                    column="Country Code",
                    field="country_code",
                    message="Country does not exist",
                )
            )
            continue
        if country.status is not CountryStatus.ACTIVE:
            issues.append(
                CompanyImportIssue(
                    sheet=LOCATIONS_SHEET,
                    row=row.row,
                    column="Country Code",
                    field="country_code",
                    message="Country is not active",
                )
            )
            continue
        if data.subdivision_code is not None:
            subdivision = await session.scalar(
                select(CountrySubdivision).where(
                    CountrySubdivision.code == data.subdivision_code
                )
            )
            if subdivision is None:
                issues.append(
                    CompanyImportIssue(
                        sheet=LOCATIONS_SHEET,
                        row=row.row,
                        column="Subdivision Code",
                        field="subdivision_code",
                        message="Country Subdivision does not exist",
                    )
                )
                continue
            if subdivision.status is not CountrySubdivisionStatus.ACTIVE:
                issues.append(
                    CompanyImportIssue(
                        sheet=LOCATIONS_SHEET,
                        row=row.row,
                        column="Subdivision Code",
                        field="subdivision_code",
                        message="Country Subdivision is not active",
                    )
                )
                continue
            if subdivision.country_code != data.country_code:
                issues.append(
                    CompanyImportIssue(
                        sheet=LOCATIONS_SHEET,
                        row=row.row,
                        column="Subdivision Code",
                        field="subdivision_code",
                        message="Country Subdivision does not belong to the selected Country",
                    )
                )
                continue
        normalized.append(NormalizedLocation(row=row.row, data=data))
    return normalized, issues


def _date_cell(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.date()
    return value


async def _normalize_gst_registrations(
    session: AsyncSession,
    company: Company,
    rows: list[ParsedWorkbookRow],
) -> tuple[list[NormalizedGSTRegistration], list[CompanyImportIssue]]:
    normalized: list[NormalizedGSTRegistration] = []
    issues: list[CompanyImportIssue] = []
    seen_gstins: dict[str, int] = {}
    for row in rows:
        values = dict(row.values)
        raw_gstin = values.get("gstin")
        if isinstance(raw_gstin, str):
            raw_gstin = raw_gstin.strip().upper()
            values["gstin"] = raw_gstin
        try:
            normalized_gstin = GSTIN_ADAPTER.validate_python(raw_gstin)
        except ValidationError:
            normalized_gstin = None
        if normalized_gstin is not None:
            previous_row = seen_gstins.get(normalized_gstin)
            if previous_row is not None:
                issues.append(
                    CompanyImportIssue(
                        sheet=GST_REGISTRATIONS_SHEET,
                        row=row.row,
                        column="GSTIN",
                        field="gstin",
                        message=(
                            f"Duplicate GSTIN: {normalized_gstin} appears more than once "
                            "in the GST Registrations sheet. Keep only one row for "
                            f"each GSTIN (first seen at row {previous_row})."
                        ),
                    )
                )
                continue
            seen_gstins[normalized_gstin] = row.row
        raw_type_code = values.pop("registration_type_code")
        type_code = (
            raw_type_code.strip().upper()
            if isinstance(raw_type_code, str) and raw_type_code.strip()
            else None
        )
        if isinstance(values.get("subdivision_code"), str):
            values["subdivision_code"] = (
                values["subdivision_code"].strip().upper()
            )
        values["valid_from"] = _date_cell(values["valid_from"])
        values["valid_to"] = _date_cell(values["valid_to"])

        registration_type: GSTRegistrationType | None = None
        if type_code is not None:
            registration_type = await session.scalar(
                select(GSTRegistrationType).where(
                    GSTRegistrationType.code == type_code
                )
            )
            if registration_type is None:
                issues.append(
                    CompanyImportIssue(
                        sheet=GST_REGISTRATIONS_SHEET,
                        row=row.row,
                        column="Registration Type Code",
                        field="registration_type_code",
                        message=f"GST Registration Type Code '{type_code}' does not exist",
                    )
                )
                continue
            if registration_type.status is not GSTRegistrationTypeStatus.ACTIVE:
                issues.append(
                    CompanyImportIssue(
                        sheet=GST_REGISTRATIONS_SHEET,
                        row=row.row,
                        column="Registration Type Code",
                        field="registration_type_code",
                        message=f"GST Registration Type Code '{type_code}' is not active",
                    )
                )
                continue
        values["gst_registration_type_id"] = (
            None if registration_type is None else registration_type.id
        )
        try:
            data = CompanyGSTRegistrationCreate.model_validate(values)
        except ValidationError as exc:
            issues.extend(
                _pydantic_issues(
                    exc,
                    sheet=GST_REGISTRATIONS_SHEET,
                    row=row.row,
                    columns=GST_REGISTRATION_FIELD_TO_COLUMN,
                )
            )
            continue

        if company.country_code != "IN":
            issues.append(
                CompanyImportIssue(
                    sheet=GST_REGISTRATIONS_SHEET,
                    row=row.row,
                    message="Company must be registered in India",
                )
            )
            continue
        subdivision = await session.scalar(
            select(CountrySubdivision).where(
                CountrySubdivision.code == data.subdivision_code
            )
        )
        if subdivision is None:
            issues.append(
                CompanyImportIssue(
                    sheet=GST_REGISTRATIONS_SHEET,
                    row=row.row,
                    column="Subdivision Code",
                    field="subdivision_code",
                    message="Country Subdivision does not exist",
                )
            )
            continue
        if subdivision.status is not CountrySubdivisionStatus.ACTIVE:
            issues.append(
                CompanyImportIssue(
                    sheet=GST_REGISTRATIONS_SHEET,
                    row=row.row,
                    column="Subdivision Code",
                    field="subdivision_code",
                    message="Country Subdivision is not active",
                )
            )
            continue
        if subdivision.country_code != "IN":
            issues.append(
                CompanyImportIssue(
                    sheet=GST_REGISTRATIONS_SHEET,
                    row=row.row,
                    column="Subdivision Code",
                    field="subdivision_code",
                    message="GST Registration requires an Indian State or Union Territory",
                )
            )
            continue
        if subdivision.gst_state_code is None:
            issues.append(
                CompanyImportIssue(
                    sheet=GST_REGISTRATIONS_SHEET,
                    row=row.row,
                    column="Subdivision Code",
                    field="subdivision_code",
                    message="Country Subdivision has no GST State code",
                )
            )
            continue
        if not data.gstin.startswith(subdivision.gst_state_code):
            issues.append(
                CompanyImportIssue(
                    sheet=GST_REGISTRATIONS_SHEET,
                    row=row.row,
                    column="Subdivision Code",
                    field="subdivision_code",
                    message="GSTIN State code does not match the selected Country Subdivision",
                )
            )
            continue
        normalized.append(
            NormalizedGSTRegistration(
                row=row.row,
                data=data,
                registration_type_code=type_code,
            )
        )
    return normalized, issues


def _normalize_gst_location_mappings(
    rows: list[ParsedWorkbookRow],
) -> tuple[list[NormalizedGSTLocationMapping], list[CompanyImportIssue]]:
    normalized: list[NormalizedGSTLocationMapping] = []
    issues: list[CompanyImportIssue] = []
    seen_pairs: dict[tuple[str, str], int] = {}
    for row in rows:
        try:
            raw_gstin = row.values["gstin"]
            if isinstance(raw_gstin, str):
                raw_gstin = raw_gstin.strip().upper()
            gstin = GSTIN_ADAPTER.validate_python(raw_gstin)
            raw_location_code = row.values["location_code"]
            if isinstance(raw_location_code, str):
                raw_location_code = raw_location_code.strip().upper()
            location_code = LOCATION_CODE_ADAPTER.validate_python(
                raw_location_code
            )
        except ValidationError as exc:
            issues.extend(
                _pydantic_issues(
                    exc,
                    sheet=GST_LOCATION_MAPPINGS_SHEET,
                    row=row.row,
                    columns=GST_LOCATION_MAPPING_FIELD_TO_COLUMN,
                )
            )
            continue
        pair = (gstin, location_code)
        previous_row = seen_pairs.get(pair)
        if previous_row is not None:
            issues.append(
                CompanyImportIssue(
                    sheet=GST_LOCATION_MAPPINGS_SHEET,
                    row=row.row,
                    message=(
                        f"Duplicate GST Location mapping '{gstin}' + "
                        f"'{location_code}' (first seen at row {previous_row})"
                    ),
                )
            )
            continue
        seen_pairs[pair] = row.row
        normalized.append(
            NormalizedGSTLocationMapping(
                row=row.row,
                gstin=gstin,
                location_code=location_code,
            )
        )
    return normalized, issues


def _location_state(location: CompanyLocation) -> dict[str, Any]:
    return {field: _json_value(getattr(location, field)) for field in LOCATION_IMPORT_FIELDS}


def _proposed_location_state(data: CompanyLocationCreate) -> dict[str, Any]:
    return {field: _json_value(getattr(data, field)) for field in LOCATION_IMPORT_FIELDS}


def _location_fingerprint(state: dict[str, Any]) -> str:
    return _hash_state(state)


def _location_name_key(state: dict[str, Any]) -> str:
    return str(state["location_name"]).strip().casefold()


def _location_address_key(state: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(
        value.strip().casefold() if isinstance(value, str) else value
        for value in (state[field] for field in LOCATION_ADDRESS_FIELDS)
    )


def _normalized_payload(
    *,
    workbook: ParsedCompanyWorkbook,
    company_update: CompanyUpdate | None,
    settings: CompanyFiscalSettingsUpdate | None,
    financial_years: list[NormalizedFinancialYear],
    locations: list[NormalizedLocation],
    gst_registrations: list[NormalizedGSTRegistration],
    gst_location_mappings: list[NormalizedGSTLocationMapping],
) -> dict[str, Any]:
    return {
        "sheets": workbook.sheets,
        "company_details": (
            None if company_update is None else company_update.model_dump(mode="json")
        ),
        "fiscal_settings": (
            None if settings is None else settings.model_dump(mode="json")
        ),
        "financial_years": [
            {"row": row.row, "start_year": row.start_year} for row in financial_years
        ],
        "locations": [
            {"row": row.row, "values": row.data.model_dump(mode="json")}
            for row in locations
        ],
        "gst_registrations": [
            {
                "row": row.row,
                "values": row.data.model_dump(mode="json"),
                "registration_type_code": row.registration_type_code,
            }
            for row in gst_registrations
        ],
        "gst_location_mappings": [
            {
                "row": row.row,
                "gstin": row.gstin,
                "location_code": row.location_code,
            }
            for row in gst_location_mappings
        ],
    }


async def _classify(
    *,
    session: AsyncSession | None,
    company: Company,
    company_update: CompanyUpdate | None,
    settings_data: CompanyFiscalSettingsUpdate | None,
    financial_year_rows: list[NormalizedFinancialYear],
    location_rows: list[NormalizedLocation],
    gst_registration_rows: list[NormalizedGSTRegistration],
    gst_location_mapping_rows: list[NormalizedGSTLocationMapping],
) -> ClassifiedImport:
    company_fields: list[CompanyImportFieldPreview] = []
    company_update_fields: list[str] = []
    company_unchanged_fields: list[str] = []
    if company_update is not None:
        normalized_values = company_update.model_dump(mode="json")
        for field in SUPPORTED_FIELDS:
            current = _json_value(getattr(company, field))
            proposed = normalized_values[field]
            changed = current != proposed
            company_fields.append(
                CompanyImportFieldPreview(
                    field=field,
                    column=FIELD_TO_COLUMN[field],
                    current_value=current,
                    proposed_value=proposed,
                    changed=changed,
                )
            )
            (company_update_fields if changed else company_unchanged_fields).append(field)

    settings_preview: FiscalSettingsImportPreview | None = None
    if settings_data is not None:
        if session is None:
            raise RuntimeError("A database session is required for Financial Years")
        start_month, start_day = resolve_fiscal_start(settings_data)
        current_settings = await session.get(CompanyFiscalSettings, company.id)
        if current_settings is None:
            classification = ImportClassification.NEW
        elif (
            current_settings.fiscal_year_pattern == settings_data.fiscal_year_pattern
            and current_settings.start_month == start_month
            and current_settings.start_day == start_day
        ):
            classification = ImportClassification.UNCHANGED
        else:
            classification = ImportClassification.SAFE_UPDATE
        settings_preview = FiscalSettingsImportPreview(
            fiscal_year_pattern=settings_data.fiscal_year_pattern.value,
            start_month=start_month,
            start_day=start_day,
            classification=classification,
        )

    existing_years: list[FinancialYear] = []
    if financial_year_rows:
        if session is None:
            raise RuntimeError("A database session is required for Financial Years")
        existing_years = list(
            (
                await session.scalars(
                    select(FinancialYear).where(FinancialYear.company_id == company.id)
                )
            ).all()
        )
    financial_previews: list[FinancialYearImportPreview] = []
    if settings_data is not None:
        start_month, start_day = resolve_fiscal_start(settings_data)
        for row in financial_year_rows:
            start_date, end_date = calculate_financial_year_dates(
                start_year=row.start_year,
                start_month=start_month,
                start_day=start_day,
            )
            display_code = generate_financial_year_code(start_date, end_date)
            exact = next(
                (
                    existing
                    for existing in existing_years
                    if existing.start_date == start_date and existing.end_date == end_date
                ),
                None,
            )
            if exact is not None:
                if exact.display_code != display_code or exact.is_transition:
                    classification = ImportClassification.CONFLICT
                    reason = "Existing period has incompatible code or transition intent"
                else:
                    classification = ImportClassification.UNCHANGED
                    reason = None
            else:
                overlap = next(
                    (
                        existing
                        for existing in existing_years
                        if existing.start_date <= end_date
                        and existing.end_date >= start_date
                    ),
                    None,
                )
                code_conflict = next(
                    (
                        existing
                        for existing in existing_years
                        if existing.display_code == display_code
                    ),
                    None,
                )
                if overlap is not None:
                    classification = ImportClassification.CONFLICT
                    reason = "Derived period overlaps an existing Financial Year"
                elif code_conflict is not None:
                    classification = ImportClassification.CONFLICT
                    reason = "Derived display code conflicts with an existing Financial Year"
                else:
                    classification = ImportClassification.NEW
                    reason = None
            financial_previews.append(
                FinancialYearImportPreview(
                    row=row.row,
                    start_year=row.start_year,
                    display_code=display_code,
                    start_date=start_date,
                    end_date=end_date,
                    classification=classification,
                    reason=reason,
                )
            )

    existing_locations: list[CompanyLocation] = []
    if location_rows or gst_location_mapping_rows:
        if session is None:
            raise RuntimeError("A database session is required for Locations")
        existing_locations = list(
            (
                await session.scalars(
                    select(CompanyLocation).where(CompanyLocation.company_id == company.id)
                )
            ).all()
        )
    by_code = {row.location_code: row for row in existing_locations}
    active = [
        row for row in existing_locations if row.status is CompanyLocationStatus.ACTIVE
    ]
    classified_locations: list[ClassifiedLocation] = []
    seen_codes: dict[str, int] = {}
    seen_blank_fingerprints: dict[str, int] = {}
    matched_ids: dict[UUID, int] = {}
    for row in location_rows:
        data = row.data
        proposed = _proposed_location_state(data)
        fingerprint = _location_fingerprint(proposed)
        matched: CompanyLocation | None = None
        reason: str | None = None
        changed_fields: list[str] = []
        code = data.location_code
        if code is not None:
            if code in seen_codes:
                classification = ImportClassification.CONFLICT
                reason = f"Duplicate Location Code '{code}' in workbook"
            else:
                seen_codes[code] = row.row
                matched = by_code.get(code)
                if matched is not None:
                    if matched.status is CompanyLocationStatus.INACTIVE:
                        classification = ImportClassification.CONFLICT
                        reason = "Inactive Location cannot be updated or reactivated"
                    else:
                        current = _location_state(matched)
                        changed_fields = [
                            field
                            for field in LOCATION_IMPORT_FIELDS
                            if current[field] != proposed[field]
                        ]
                        classification = (
                            ImportClassification.SAFE_UPDATE
                            if changed_fields
                            else ImportClassification.UNCHANGED
                        )
                else:
                    ambiguous = [
                        existing
                        for existing in active
                        if _location_fingerprint(_location_state(existing)) == fingerprint
                        or _location_name_key(_location_state(existing))
                        == _location_name_key(proposed)
                        or _location_address_key(_location_state(existing))
                        == _location_address_key(proposed)
                    ]
                    if ambiguous:
                        classification = ImportClassification.CONFLICT
                        reason = (
                            "Location Code is unknown but the row resembles an existing "
                            "Location; use the existing immutable code"
                        )
                    else:
                        classification = ImportClassification.NEW
        else:
            exact = [
                existing
                for existing in active
                if _location_fingerprint(_location_state(existing)) == fingerprint
            ]
            if len(exact) == 1:
                matched = exact[0]
                classification = ImportClassification.UNCHANGED
                code = matched.location_code
            elif len(exact) > 1:
                classification = ImportClassification.CONFLICT
                reason = (
                    "Blank-code row matches multiple active Locations; supply Location Code"
                )
            elif fingerprint in seen_blank_fingerprints:
                classification = ImportClassification.CONFLICT
                reason = "Duplicate blank-code Location row in workbook"
            else:
                seen_blank_fingerprints[fingerprint] = row.row
                ambiguous = [
                    existing
                    for existing in active
                    if _location_name_key(_location_state(existing))
                    == _location_name_key(proposed)
                    or _location_address_key(_location_state(existing))
                    == _location_address_key(proposed)
                ]
                if ambiguous:
                    classification = ImportClassification.CONFLICT
                    reason = (
                        "Blank-code row resembles an existing Location but differs; "
                        "supply its Location Code for update"
                    )
                else:
                    classification = ImportClassification.NEW
        if matched is not None:
            if matched.id in matched_ids:
                classification = ImportClassification.CONFLICT
                reason = "Multiple workbook rows resolve to the same Location"
            else:
                matched_ids[matched.id] = row.row
        preview = LocationImportPreview(
            row=row.row,
            location_code=code,
            location_name=data.location_name,
            country_code=data.country_code,
            subdivision_code=data.subdivision_code,
            classification=classification,
            changed_fields=changed_fields,
            reason=reason,
            code_will_be_generated=(
                data.location_code is None
                and classification is ImportClassification.NEW
            ),
        )
        classified_locations.append(ClassifiedLocation(preview=preview, matched=matched))

    registered_ids: set[str] = {
        str(row.id) for row in active if row.is_registered_office
    }
    for row, classified in zip(location_rows, classified_locations, strict=True):
        if classified.preview.classification is ImportClassification.CONFLICT:
            continue
        key = (
            str(classified.matched.id)
            if classified.matched is not None
            else f"new-row-{row.row}"
        )
        if row.data.is_registered_office:
            registered_ids.add(key)
        else:
            registered_ids.discard(key)
    if len(registered_ids) > 1:
        replacement: list[ClassifiedLocation] = []
        for row, classified in zip(location_rows, classified_locations, strict=True):
            if row.data.is_registered_office:
                preview = classified.preview.model_copy(
                    update={
                        "classification": ImportClassification.CONFLICT,
                        "reason": "Workbook desired state has more than one active Registered Office",
                    }
                )
                replacement.append(
                    ClassifiedLocation(preview=preview, matched=classified.matched)
                )
            else:
                replacement.append(classified)
        classified_locations = replacement

    requested_gstins = {
        row.data.gstin for row in gst_registration_rows
    } | {row.gstin for row in gst_location_mapping_rows}
    existing_gst_registrations: list[CompanyGSTRegistration] = []
    if requested_gstins:
        if session is None:
            raise RuntimeError("A database session is required for GST Registrations")
        existing_gst_registrations = list(
            (
                await session.scalars(
                    select(CompanyGSTRegistration).where(
                        CompanyGSTRegistration.gstin.in_(requested_gstins)
                    )
                )
            ).all()
        )
    gst_by_gstin = {row.gstin: row for row in existing_gst_registrations}
    classified_gst_registrations: list[ClassifiedGSTRegistration] = []
    for row in gst_registration_rows:
        data = row.data
        existing = gst_by_gstin.get(data.gstin)
        reason: str | None = None
        matched: CompanyGSTRegistration | None = None
        if existing is None:
            classification = ImportClassification.NEW
        elif existing.company_id != company.id:
            classification = ImportClassification.CONFLICT
            reason = "GSTIN already exists outside the selected Company"
        else:
            matched = existing
            equivalent = (
                existing.registered_legal_name == data.registered_legal_name
                and existing.gst_registration_type_id
                == data.gst_registration_type_id
                and existing.subdivision_code == data.subdivision_code
                and existing.valid_from == data.valid_from
                and existing.valid_to == data.valid_to
            )
            if equivalent:
                classification = ImportClassification.UNCHANGED
            else:
                classification = ImportClassification.CONFLICT
                reason = (
                    "GSTIN already exists and GST Registration data cannot be "
                    "modified through Company Configuration Excel Import"
                )
        classified_gst_registrations.append(
            ClassifiedGSTRegistration(
                preview=GSTRegistrationImportPreview(
                    row=row.row,
                    gstin=data.gstin,
                    registered_legal_name=data.registered_legal_name,
                    subdivision_code=data.subdivision_code,
                    registration_type_code=row.registration_type_code,
                    valid_from=data.valid_from,
                    valid_to=data.valid_to,
                    classification=classification,
                    reason=reason,
                ),
                matched=matched,
            )
        )

    gst_row_by_gstin = {row.data.gstin: row for row in gst_registration_rows}
    gst_classification_by_gstin = {
        row.preview.gstin: row for row in classified_gst_registrations
    }
    location_row_by_code = {
        row.data.location_code: (row, classified)
        for row, classified in zip(
            location_rows, classified_locations, strict=True
        )
        if row.data.location_code is not None
    }
    existing_location_by_code = {
        row.location_code: row for row in existing_locations
    }
    mapping_targets_by_location: dict[str, set[str]] = {}
    for row in gst_location_mapping_rows:
        mapping_targets_by_location.setdefault(row.location_code, set()).add(
            row.gstin
        )

    classified_mappings: list[ClassifiedGSTLocationMapping] = []
    for row in gst_location_mapping_rows:
        classification = ImportClassification.CONFLICT
        reason: str | None = None
        gst = gst_by_gstin.get(row.gstin)
        workbook_gst = gst_row_by_gstin.get(row.gstin)
        workbook_gst_classification = gst_classification_by_gstin.get(row.gstin)

        if len(mapping_targets_by_location[row.location_code]) > 1:
            reason = "Location Code is mapped to more than one GSTIN in the workbook"
        elif gst is not None and gst.company_id != company.id:
            reason = "GSTIN does not resolve within the selected Company"
        elif (
            workbook_gst_classification is not None
            and workbook_gst_classification.preview.classification
            is ImportClassification.CONFLICT
        ):
            reason = "GST Registration row is in conflict"
        elif gst is None and workbook_gst is None:
            reason = "GSTIN does not resolve within the selected Company"
        else:
            workbook_location_pair = location_row_by_code.get(row.location_code)
            existing_location = existing_location_by_code.get(row.location_code)
            if workbook_location_pair is not None:
                workbook_location, workbook_location_classification = (
                    workbook_location_pair
                )
                if (
                    workbook_location_classification.preview.classification
                    is ImportClassification.CONFLICT
                ):
                    reason = "Location row is in conflict"
                    location = workbook_location_classification.matched
                    location_subdivision = workbook_location.data.subdivision_code
                    location_status = (
                        None if location is None else location.status
                    )
                else:
                    location = workbook_location_classification.matched
                    location_subdivision = workbook_location.data.subdivision_code
                    location_status = (
                        CompanyLocationStatus.ACTIVE
                        if location is None
                        else location.status
                    )
            else:
                location = existing_location
                location_subdivision = (
                    None if location is None else location.subdivision_code
                )
                location_status = None if location is None else location.status

            if reason is None and location is None and workbook_location_pair is None:
                reason = (
                    "Location Code does not resolve within the selected Company; "
                    "a same-workbook new Location must have an explicitly supplied code"
                )
            target_subdivision = (
                workbook_gst.data.subdivision_code
                if workbook_gst is not None
                else None if gst is None else gst.subdivision_code
            )
            target_status = (
                CompanyGSTRegistrationStatus.DRAFT
                if gst is None and workbook_gst is not None
                else None if gst is None else gst.status
            )
            target_id = None if gst is None else gst.id
            if reason is None and location_status is CompanyLocationStatus.INACTIVE:
                reason = "Inactive Location cannot receive a GST Registration assignment"
            elif reason is None and location_subdivision != target_subdivision:
                reason = "GST Registration jurisdiction does not match the Location"
            elif reason is None:
                current_registration_id = (
                    None if location is None else location.gst_registration_id
                )
                if target_id is not None and current_registration_id == target_id:
                    classification = ImportClassification.UNCHANGED
                elif current_registration_id is not None:
                    reason = "Location is already assigned to a different GSTIN"
                elif target_status is CompanyGSTRegistrationStatus.INACTIVE:
                    reason = (
                        "Inactive GST Registration cannot receive a new Location assignment"
                    )
                else:
                    classification = ImportClassification.SAFE_UPDATE

        classified_mappings.append(
            ClassifiedGSTLocationMapping(
                preview=GSTLocationMappingImportPreview(
                    row=row.row,
                    gstin=row.gstin,
                    location_code=row.location_code,
                    classification=classification,
                    reason=reason,
                )
            )
        )

    return ClassifiedImport(
        company_update=company_update,
        company_fields=company_fields,
        company_update_fields=company_update_fields,
        company_unchanged_fields=company_unchanged_fields,
        fiscal_settings_data=settings_data,
        fiscal_settings_preview=settings_preview,
        financial_years=financial_previews,
        locations=classified_locations,
        gst_registrations=classified_gst_registrations,
        gst_location_mappings=classified_mappings,
    )


async def _normalize_workbook(
    *,
    session: AsyncSession | None,
    company: Company,
    workbook: ParsedCompanyWorkbook,
) -> tuple[
    CompanyUpdate | None,
    CompanyFiscalSettingsUpdate | None,
    list[NormalizedFinancialYear],
    list[NormalizedLocation],
    list[NormalizedGSTRegistration],
    list[NormalizedGSTLocationMapping],
]:
    issues: list[CompanyImportIssue] = []
    company_update: CompanyUpdate | None = None
    if workbook.company_details is not None:
        company_update, company_issues = validate_and_normalize_values(
            workbook.company_details.values, company=company
        )
        issues.extend(company_issues)
    settings, financial_years, fiscal_issues = _normalize_financial_years(
        workbook.financial_years
    )
    issues.extend(fiscal_issues)
    if workbook.locations and session is None:
        raise RuntimeError("A database session is required for Locations")
    locations, location_issues = await _normalize_locations(session, workbook.locations)  # type: ignore[arg-type]
    issues.extend(location_issues)
    if (workbook.gst_registrations or workbook.gst_location_mappings) and session is None:
        raise RuntimeError("A database session is required for GST import")
    gst_registrations, gst_issues = await _normalize_gst_registrations(
        session, company, workbook.gst_registrations  # type: ignore[arg-type]
    )
    issues.extend(gst_issues)
    gst_location_mappings, mapping_issues = _normalize_gst_location_mappings(
        workbook.gst_location_mappings
    )
    issues.extend(mapping_issues)
    if issues:
        raise CompanyImportValidationError(issues)
    return (
        company_update,
        settings,
        financial_years,
        locations,
        gst_registrations,
        gst_location_mappings,
    )


def _payload_rows(
    values: dict[str, Any], company: Company
) -> tuple[
    CompanyUpdate | None,
    CompanyFiscalSettingsUpdate | None,
    list[NormalizedFinancialYear],
    list[NormalizedLocation],
    list[NormalizedGSTRegistration],
    list[NormalizedGSTLocationMapping],
    list[str],
]:
    try:
        company_values = values.get("company_details")
        company_update = (
            None
            if company_values is None
            else validate_and_normalize_values(company_values, company=company)[0]
        )
        if company_values is not None and company_update is None:
            raise ValueError("Company Details in preview token are invalid")
        settings_values = values.get("fiscal_settings")
        settings = (
            None
            if settings_values is None
            else CompanyFiscalSettingsUpdate.model_validate(settings_values)
        )
        financial_years = [
            NormalizedFinancialYear(
                row=int(item["row"]),
                start_year=FinancialYearCreate.model_validate(
                    {"start_year": item["start_year"]}
                ).start_year,
            )
            for item in values.get("financial_years", [])
        ]
        locations = [
            NormalizedLocation(
                row=int(item["row"]),
                data=CompanyLocationCreate.model_validate(item["values"]),
            )
            for item in values.get("locations", [])
        ]
        gst_registrations = [
            NormalizedGSTRegistration(
                row=int(item["row"]),
                data=CompanyGSTRegistrationCreate.model_validate(item["values"]),
                registration_type_code=(
                    None
                    if item.get("registration_type_code") is None
                    else str(item["registration_type_code"])
                ),
            )
            for item in values.get("gst_registrations", [])
        ]
        gst_location_mappings = [
            NormalizedGSTLocationMapping(
                row=int(item["row"]),
                gstin=GSTIN_ADAPTER.validate_python(item["gstin"]),
                location_code=LOCATION_CODE_ADAPTER.validate_python(
                    item["location_code"]
                ),
            )
            for item in values.get("gst_location_mappings", [])
        ]
        sheets = [str(sheet) for sheet in values["sheets"]]
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        raise PreviewTokenError("Preview token is invalid") from exc
    return (
        company_update,
        settings,
        financial_years,
        locations,
        gst_registrations,
        gst_location_mappings,
        sheets,
    )


async def preview_company_import(
    *,
    session: AsyncSession | None = None,
    company: Company,
    tenant: Tenant,
    contents: bytes,
    signing_key: str,
) -> CompanyImportPreviewResponse:
    workbook = parse_company_workbook(contents)
    (
        company_update,
        settings,
        financial_years,
        locations,
        gst_registrations,
        gst_location_mappings,
    ) = await _normalize_workbook(session=session, company=company, workbook=workbook)
    classified = await _classify(
        session=session,
        company=company,
        company_update=company_update,
        settings_data=settings,
        financial_year_rows=financial_years,
        location_rows=locations,
        gst_registration_rows=gst_registrations,
        gst_location_mapping_rows=gst_location_mappings,
    )
    normalized_values = (
        {} if company_update is None else company_update.model_dump(mode="json")
    )
    payload = _normalized_payload(
        workbook=workbook,
        company_update=company_update,
        settings=settings,
        financial_years=financial_years,
        locations=locations,
        gst_registrations=gst_registrations,
        gst_location_mappings=gst_location_mappings,
    )
    token: str | None = None
    expires_at = None
    if not classified.has_conflicts:
        fingerprint = (
            await configuration_fingerprint(session, company)
            if session is not None
            else _hash_state(
                {
                    **{
                        field: _json_value(getattr(company, field))
                        for field in SUPPORTED_FIELDS
                    },
                    "updated_at": company.updated_at.isoformat(),
                }
            )
        )
        token, expires_at = create_preview_token(
            signing_key=signing_key,
            tenant_id=str(tenant.id),
            company_id=str(company.id),
            values=payload,
            company_fingerprint=fingerprint,
        )
    return CompanyImportPreviewResponse(
        valid=not classified.has_conflicts,
        company_id=company.id,
        sheet=(workbook.sheets[0] if len(workbook.sheets) == 1 else "Multiple"),
        sheets=workbook.sheets,
        normalized_values=normalized_values,
        fields=classified.company_fields,
        update_fields=classified.company_update_fields,
        unchanged_fields=classified.company_unchanged_fields,
        errors=[],
        unsupported_fields=UNSUPPORTED_FIELDS,
        fiscal_settings=classified.fiscal_settings_preview,
        financial_years=classified.financial_years,
        locations=[row.preview for row in classified.locations],
        gst_registrations=[
            row.preview for row in classified.gst_registrations
        ],
        gst_location_mappings=[
            row.preview for row in classified.gst_location_mappings
        ],
        preview_token=token,
        expires_at=expires_at,
    )


async def apply_company_import(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    preview_token: str,
    signing_key: str,
) -> CompanyImportApplyResponse | None:
    payload = read_preview_token(preview_token, signing_key=signing_key)
    if payload.tenant_id != str(tenant.id) or payload.company_id != str(company_id):
        raise PreviewTokenError(
            "Preview token does not belong to the selected Company context"
        )
    company = await session.scalar(
        select(Company)
        .where(Company.id == company_id, Company.tenant_id == tenant.id)
        .with_for_update()
    )
    if company is None:
        return None
    try:
        (
            company_update,
            settings,
            financial_rows,
            location_rows,
            gst_registration_rows,
            gst_location_mapping_rows,
            _,
        ) = _payload_rows(payload.values, company)
        mapping_location_codes = {
            row.location_code for row in gst_location_mapping_rows
        }
        requested_gstins = {
            row.data.gstin for row in gst_registration_rows
        } | {row.gstin for row in gst_location_mapping_rows}
        if mapping_location_codes:
            await session.scalars(
                select(CompanyLocation)
                .where(
                    CompanyLocation.company_id == company_id,
                    CompanyLocation.location_code.in_(mapping_location_codes),
                )
                .with_for_update()
            )
        if requested_gstins:
            await session.scalars(
                select(CompanyGSTRegistration)
                .where(CompanyGSTRegistration.gstin.in_(requested_gstins))
                .with_for_update()
            )
        classified = await _classify(
            session=session,
            company=company,
            company_update=company_update,
            settings_data=settings,
            financial_year_rows=financial_rows,
            location_rows=location_rows,
            gst_registration_rows=gst_registration_rows,
            gst_location_mapping_rows=gst_location_mapping_rows,
        )
        if classified.has_conflicts:
            raise CompanyStateConflictError(
                "Company configuration conflicts with current state; create a new preview"
            )
        current_fingerprint = await configuration_fingerprint(session, company)
        if current_fingerprint != payload.company_fingerprint and classified.has_changes:
            raise CompanyStateConflictError(
                "Company configuration changed after preview; create a new preview before applying"
            )

        if classified.company_update_fields and company_update is not None:
            changed_values = {
                field: company_update.model_dump(mode="json")[field]
                for field in classified.company_update_fields
            }
            await update_company(
                session=session,
                tenant=tenant,
                company_id=company_id,
                company_data=CompanyUpdate.model_validate(changed_values),
                commit=False,
            )
        if (
            classified.fiscal_settings_preview is not None
            and classified.fiscal_settings_preview.classification
            in {ImportClassification.NEW, ImportClassification.SAFE_UPDATE}
            and settings is not None
        ):
            await configure_company_fiscal_settings(
                session=session,
                tenant=tenant,
                company_id=company_id,
                settings_data=settings,
                commit=False,
            )
        for row in sorted(financial_rows, key=lambda value: value.start_year):
            preview = next(item for item in classified.financial_years if item.row == row.row)
            if preview.classification is ImportClassification.NEW:
                await create_financial_year(
                    session=session,
                    tenant=tenant,
                    company_id=company_id,
                    financial_year_data=FinancialYearCreate(start_year=row.start_year),
                    commit=False,
                )

        location_pairs = list(zip(location_rows, classified.locations, strict=True))
        location_pairs.sort(
            key=lambda pair: (
                0
                if pair[1].matched is not None
                and pair[1].matched.is_registered_office
                and not pair[0].data.is_registered_office
                else 1,
                pair[0].row,
            )
        )
        applied_location_previews: dict[int, LocationImportPreview] = {}
        for row, classified_location in location_pairs:
            preview = classified_location.preview
            if preview.classification is ImportClassification.SAFE_UPDATE:
                assert classified_location.matched is not None
                update_values = {
                    field: getattr(row.data, field)
                    for field in preview.changed_fields
                }
                updated = await update_company_location(
                    session=session,
                    tenant=tenant,
                    company_id=company_id,
                    location_id=classified_location.matched.id,
                    location_data=CompanyLocationUpdate.model_validate(update_values),
                    commit=False,
                )
                if updated is None:
                    raise CompanyStateConflictError(
                        "Company Location changed during import apply"
                    )
                applied_location_previews[row.row] = preview
            elif preview.classification is ImportClassification.NEW:
                created = await create_company_location(
                    session=session,
                    tenant=tenant,
                    company_id=company_id,
                    location_data=row.data,
                    commit=False,
                )
                applied_location_previews[row.row] = preview.model_copy(
                    update={
                        "location_code": created.location_code,
                        "code_will_be_generated": False,
                    }
                )
            else:
                applied_location_previews[row.row] = preview

        for row, classified_gst in zip(
            gst_registration_rows,
            classified.gst_registrations,
            strict=True,
        ):
            if classified_gst.preview.classification is ImportClassification.NEW:
                await create_company_gst_registration(
                    session=session,
                    tenant=tenant,
                    company_id=company_id,
                    registration_data=row.data,
                    commit=False,
                )

        mapping_gstins = {row.gstin for row in gst_location_mapping_rows}
        mapping_location_codes = {
            row.location_code for row in gst_location_mapping_rows
        }
        gst_targets = {
            row.gstin: row
            for row in (
                await session.scalars(
                    select(CompanyGSTRegistration).where(
                        CompanyGSTRegistration.company_id == company_id,
                        CompanyGSTRegistration.gstin.in_(mapping_gstins),
                    )
                )
            ).all()
        } if mapping_gstins else {}
        location_targets = {
            row.location_code: row
            for row in (
                await session.scalars(
                    select(CompanyLocation).where(
                        CompanyLocation.company_id == company_id,
                        CompanyLocation.location_code.in_(
                            mapping_location_codes
                        ),
                    )
                )
            ).all()
        } if mapping_location_codes else {}
        for row, classified_mapping in zip(
            gst_location_mapping_rows,
            classified.gst_location_mappings,
            strict=True,
        ):
            if (
                classified_mapping.preview.classification
                is not ImportClassification.SAFE_UPDATE
            ):
                continue
            registration = gst_targets.get(row.gstin)
            location = location_targets.get(row.location_code)
            if registration is None or location is None:
                raise CompanyStateConflictError(
                    "GST Location mapping target changed during import apply"
                )
            updated = await update_company_location(
                session=session,
                tenant=tenant,
                company_id=company_id,
                location_id=location.id,
                location_data=CompanyLocationUpdate(
                    gst_registration_id=registration.id
                ),
                commit=False,
            )
            if updated is None:
                raise CompanyStateConflictError(
                    "GST Location mapping target changed during import apply"
                )

        await session.commit()
        await session.refresh(company)
        ordered_locations = [
            applied_location_previews[row.row]
            for row in sorted(location_rows, key=lambda value: value.row)
        ]
        return CompanyImportApplyResponse(
            company=CompanyResponse.model_validate(company),
            applied_fields=classified.company_update_fields,
            unchanged_fields=classified.company_unchanged_fields,
            fiscal_settings=classified.fiscal_settings_preview,
            financial_years=classified.financial_years,
            locations=ordered_locations,
            gst_registrations=[
                row.preview for row in classified.gst_registrations
            ],
            gst_location_mappings=[
                row.preview for row in classified.gst_location_mappings
            ],
            no_changes=not classified.has_changes,
        )
    except Exception:
        await session.rollback()
        raise
