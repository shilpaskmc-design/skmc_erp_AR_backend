from sqlalchemy import CheckConstraint, ForeignKeyConstraint

from skmc_erp.core.currency.model import (
    CompanyReportingCurrency,
    CompanyReportingCurrencyStatus,
    Currency,
    CurrencyStatus,
)
from skmc_erp.model_base import Base


def test_currency_metadata_matches_approved_contract() -> None:
    table = Currency.__table__

    assert table.schema == "core"
    assert table.name == "currencies"
    assert Base.metadata.tables["core.currencies"] is table
    assert list(table.columns.keys()) == [
        "code",
        "name",
        "symbol",
        "minor_units",
        "status",
        "created_at",
        "updated_at",
    ]

    assert table.c.code.primary_key
    assert table.c.code.type.length == 3
    assert not table.c.code.nullable

    assert table.c.name.type.length == 100
    assert not table.c.name.nullable
    assert not table.c.name.unique

    assert table.c.symbol.type.length == 16
    assert table.c.symbol.nullable
    assert not table.c.symbol.unique

    assert not table.c.minor_units.nullable
    assert table.c.minor_units.server_default is None

    assert table.c.status.type.length == 20
    assert not table.c.status.nullable
    assert table.c.status.server_default is None
    assert not table.c.status.type.native_enum

    for timestamp_column in (table.c.created_at, table.c.updated_at):
        assert timestamp_column.type.timezone
        assert not timestamp_column.nullable
        assert timestamp_column.server_default is not None
        assert str(timestamp_column.server_default.arg) == "CURRENT_TIMESTAMP"

    check_constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert check_constraints == {
        "ck_currencies_code_format": "code ~ '^[A-Z]{3}$'",
        "ck_currencies_name_not_blank": "btrim(name) <> ''",
        "ck_currencies_symbol_not_blank": (
            "symbol IS NULL OR btrim(symbol) <> ''"
        ),
        "ck_currencies_minor_units_range": "minor_units BETWEEN 0 AND 4",
        "ck_currencies_status": "status IN ('ACTIVE', 'INACTIVE')",
    }
    assert not table.indexes


def test_currency_status_contains_only_approved_values() -> None:
    assert {status.value for status in CurrencyStatus} == {
        "ACTIVE",
        "INACTIVE",
    }


def test_company_reporting_currency_metadata_matches_contract() -> None:
    table = CompanyReportingCurrency.__table__

    assert table is Base.metadata.tables["core.company_reporting_currencies"]
    assert table.schema == "core"
    assert list(table.columns.keys()) == [
        "company_id",
        "currency_code",
        "status",
        "created_at",
        "updated_at",
    ]
    assert [column.name for column in table.primary_key.columns] == [
        "company_id",
        "currency_code",
    ]
    assert table.primary_key.name == "pk_company_reporting_currencies"
    assert table.c.company_id.type.as_uuid
    assert table.c.currency_code.type.length == 3
    assert table.c.status.type.length == 20
    assert table.c.status.server_default is None
    assert not table.c.status.type.native_enum
    assert not table.indexes

    for timestamp_column in (table.c.created_at, table.c.updated_at):
        assert timestamp_column.type.timezone
        assert not timestamp_column.nullable
        assert str(timestamp_column.server_default.arg) == "CURRENT_TIMESTAMP"

    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert checks == {
        "ck_company_reporting_currencies_status": (
            "status IN ('ACTIVE', 'INACTIVE')"
        )
    }
    foreign_keys = {
        constraint.name: (
            tuple(element.parent.name for element in constraint.elements),
            tuple(element.target_fullname for element in constraint.elements),
            constraint.ondelete,
        )
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    assert foreign_keys == {
        "fk_company_reporting_currencies_company_id_companies": (
            ("company_id",),
            ("core.companies.id",),
            "NO ACTION",
        ),
        "fk_company_reporting_currencies_currency_code_currencies": (
            ("currency_code",),
            ("core.currencies.code",),
            "NO ACTION",
        ),
    }


def test_company_reporting_currency_status_values_are_closed() -> None:
    assert {status.value for status in CompanyReportingCurrencyStatus} == {
        "ACTIVE",
        "INACTIVE",
    }
