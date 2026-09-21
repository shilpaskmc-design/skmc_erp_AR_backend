from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import ExcludeConstraint

from skmc_erp.core.company.model import Company
from skmc_erp.core.financial_year.model import (
    CompanyFiscalSettings,
    FinancialYear,
    FinancialYearStatus,
    FiscalYearPattern,
)
from skmc_erp.model_base import Base


def test_company_fiscal_settings_metadata_matches_contract() -> None:
    table = CompanyFiscalSettings.__table__

    assert Company.__table__ is Base.metadata.tables["core.companies"]
    assert table.schema == "core"
    assert table.name == "company_fiscal_settings"
    assert list(table.columns.keys()) == [
        "company_id",
        "fiscal_year_pattern",
        "start_month",
        "start_day",
        "created_at",
        "updated_at",
    ]
    assert table.c.company_id.primary_key
    assert table.c.fiscal_year_pattern.type.length == 20
    assert not table.c.fiscal_year_pattern.type.native_enum
    assert not table.c.start_month.nullable
    assert not table.c.start_day.nullable

    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert checks["ck_company_fiscal_settings_start_month"] == (
        "start_month BETWEEN 1 AND 12"
    )
    assert "WHEN start_month = 2 THEN 28" in checks[
        "ck_company_fiscal_settings_recurring_date"
    ]
    assert "APR_MAR" in checks["ck_company_fiscal_settings_pattern_values"]

    foreign_keys = {
        constraint.name: constraint.ondelete
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    assert foreign_keys == {
        "fk_company_fiscal_settings_company_id_companies": "NO ACTION"
    }


def test_financial_year_metadata_matches_contract() -> None:
    table = FinancialYear.__table__

    assert table.schema == "core"
    assert table.name == "financial_years"
    assert list(table.columns.keys()) == [
        "id",
        "company_id",
        "start_date",
        "end_date",
        "display_code",
        "is_transition",
        "status",
        "created_at",
        "updated_at",
    ]
    assert table.c.id.primary_key
    assert str(table.c.id.server_default.arg) == "gen_random_uuid()"
    assert table.c.display_code.type.length == 30
    assert not table.c.display_code.nullable
    assert str(table.c.is_transition.server_default.arg) == "false"
    assert table.c.status.server_default is None
    assert not table.c.status.type.native_enum

    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert checks == {
        "ck_financial_years_date_order": "end_date >= start_date",
        "ck_financial_years_display_code_not_blank": (
            "btrim(display_code) <> ''"
        ),
        "ck_financial_years_status": (
            "status IN ('DRAFT', 'OPEN', 'CLOSED')"
        ),
    }

    unique_constraints = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert unique_constraints == {
        "uq_financial_years_company_id_display_code": (
            "company_id",
            "display_code",
        )
    }
    exclusion_constraints = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, ExcludeConstraint)
    ]
    assert len(exclusion_constraints) == 1
    assert exclusion_constraints[0].name == (
        "ex_financial_years_company_date_overlap"
    )


def test_financial_year_enums_contain_only_approved_values() -> None:
    assert {pattern.value for pattern in FiscalYearPattern} == {
        "APR_MAR",
        "JAN_DEC",
        "CUSTOM",
    }
    assert {status.value for status in FinancialYearStatus} == {
        "DRAFT",
        "OPEN",
        "CLOSED",
    }
