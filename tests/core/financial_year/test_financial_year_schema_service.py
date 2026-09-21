from datetime import date

import pytest
from pydantic import ValidationError

from skmc_erp.core.financial_year.model import FiscalYearPattern
from skmc_erp.core.financial_year.schema import (
    CompanyFiscalSettingsUpdate,
    FinancialYearCreate,
)
from skmc_erp.core.financial_year.service import (
    calculate_financial_year_dates,
    generate_financial_year_code,
    resolve_fiscal_start,
)


@pytest.mark.parametrize(
    ("pattern", "expected"),
    [
        (FiscalYearPattern.APR_MAR, (4, 1)),
        (FiscalYearPattern.JAN_DEC, (1, 1)),
    ],
)
def test_preset_patterns_resolve_fixed_start(
    pattern: FiscalYearPattern,
    expected: tuple[int, int],
) -> None:
    settings = CompanyFiscalSettingsUpdate(fiscal_year_pattern=pattern)

    assert resolve_fiscal_start(settings) == expected


@pytest.mark.parametrize(
    ("month", "day"),
    [(2, 28), (4, 30), (1, 31), (7, 15)],
)
def test_custom_accepts_dates_valid_every_year(month: int, day: int) -> None:
    settings = CompanyFiscalSettingsUpdate(
        fiscal_year_pattern="CUSTOM",
        custom_fiscal_year_start_month=month,
        custom_fiscal_year_start_day=day,
    )

    assert resolve_fiscal_start(settings) == (month, day)


@pytest.mark.parametrize(
    "payload",
    [
        {"fiscal_year_pattern": "CUSTOM"},
        {
            "fiscal_year_pattern": "CUSTOM",
            "custom_fiscal_year_start_month": 2,
            "custom_fiscal_year_start_day": 29,
        },
        {
            "fiscal_year_pattern": "CUSTOM",
            "custom_fiscal_year_start_month": 4,
            "custom_fiscal_year_start_day": 31,
        },
        {
            "fiscal_year_pattern": "CUSTOM",
            "custom_fiscal_year_start_month": 13,
            "custom_fiscal_year_start_day": 1,
        },
        {
            "fiscal_year_pattern": "APR_MAR",
            "custom_fiscal_year_start_month": 4,
            "custom_fiscal_year_start_day": 1,
        },
        {
            "fiscal_year_pattern": "JAN_DEC",
            "custom_fiscal_year_start_month": 1,
            "custom_fiscal_year_start_day": 1,
        },
    ],
)
def test_fiscal_settings_reject_invalid_pattern_values(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        CompanyFiscalSettingsUpdate.model_validate(payload)


@pytest.mark.parametrize(
    ("start_year", "month", "day", "expected_start", "expected_end"),
    [
        (2026, 4, 1, date(2026, 4, 1), date(2027, 3, 31)),
        (2026, 1, 1, date(2026, 1, 1), date(2026, 12, 31)),
        (2026, 7, 15, date(2026, 7, 15), date(2027, 7, 14)),
        (2023, 2, 28, date(2023, 2, 28), date(2024, 2, 27)),
        (2024, 2, 28, date(2024, 2, 28), date(2025, 2, 27)),
    ],
)
def test_financial_year_date_generation(
    start_year: int,
    month: int,
    day: int,
    expected_start: date,
    expected_end: date,
) -> None:
    assert calculate_financial_year_dates(
        start_year=start_year,
        start_month=month,
        start_day=day,
    ) == (expected_start, expected_end)


@pytest.mark.parametrize(
    ("start_date", "end_date", "expected"),
    [
        (date(2026, 4, 1), date(2027, 3, 31), "FY2026-27"),
        (date(2026, 1, 1), date(2026, 12, 31), "FY2026"),
        (date(2026, 7, 15), date(2027, 7, 14), "FY2026-27"),
    ],
)
def test_financial_year_code_generation(
    start_date: date,
    end_date: date,
    expected: str,
) -> None:
    assert generate_financial_year_code(start_date, end_date) == expected


def test_financial_year_generation_request_rejects_system_fields() -> None:
    for field_name, value in (
        ("company_id", "00000000-0000-0000-0000-000000000001"),
        ("tenant_id", "00000000-0000-0000-0000-000000000001"),
        ("start_date", "2026-04-01"),
        ("end_date", "2027-03-31"),
        ("status", "OPEN"),
        ("display_code", "CUSTOM"),
    ):
        with pytest.raises(ValidationError):
            FinancialYearCreate.model_validate(
                {"start_year": 2026, field_name: value}
            )
