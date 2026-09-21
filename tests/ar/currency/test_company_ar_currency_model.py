from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index, UniqueConstraint

from skmc_erp.ar.currency.model import (
    CompanyARCurrency,
    CompanyARCurrencyStatus,
)
from skmc_erp.model_base import Base


def test_company_ar_currency_metadata_matches_contract() -> None:
    table = CompanyARCurrency.__table__

    assert table is Base.metadata.tables["ar.company_ar_currencies"]
    assert table.schema == "ar"
    assert list(table.columns.keys()) == [
        "id",
        "company_id",
        "currency_code",
        "billing_enabled",
        "receipt_enabled",
        "is_default_billing",
        "is_default_receipt",
        "status",
        "created_at",
        "updated_at",
    ]
    assert table.primary_key.name == "pk_company_ar_currencies"
    assert table.c.id.type.as_uuid
    assert str(table.c.id.server_default.arg) == "gen_random_uuid()"
    assert table.c.currency_code.type.length == 3
    assert table.c.status.type.length == 20
    assert table.c.status.server_default is None
    assert not table.c.status.type.native_enum

    for column_name in (
        "billing_enabled",
        "receipt_enabled",
        "is_default_billing",
        "is_default_receipt",
    ):
        column = table.c[column_name]
        assert not column.nullable
        assert str(column.server_default.arg) == "false"

    for timestamp_column in (table.c.created_at, table.c.updated_at):
        assert timestamp_column.type.timezone
        assert not timestamp_column.nullable
        assert str(timestamp_column.server_default.arg) == "CURRENT_TIMESTAMP"


def test_company_ar_currency_constraints_match_contract() -> None:
    table = CompanyARCurrency.__table__
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert checks == {
        "ck_company_ar_currencies_default_billing_enabled": (
            "NOT is_default_billing OR billing_enabled"
        ),
        "ck_company_ar_currencies_default_receipt_enabled": (
            "NOT is_default_receipt OR receipt_enabled"
        ),
        "ck_company_ar_currencies_active_use_enabled": (
            "status <> 'ACTIVE' OR billing_enabled OR receipt_enabled"
        ),
        "ck_company_ar_currencies_status": (
            "status IN ('ACTIVE', 'INACTIVE')"
        ),
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
        "fk_company_ar_currencies_company_id_companies": (
            ("company_id",),
            ("core.companies.id",),
            "NO ACTION",
        ),
        "fk_company_ar_currencies_currency_code_currencies": (
            ("currency_code",),
            ("core.currencies.code",),
            "NO ACTION",
        ),
    }

    uniques = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert uniques == {
        "uq_company_ar_currencies_company_currency": (
            "company_id",
            "currency_code",
        )
    }

    indexes = {
        index.name: (
            index.unique,
            tuple(column.name for column in index.columns),
            str(index.dialect_options["postgresql"]["where"]),
        )
        for index in table.indexes
        if isinstance(index, Index)
    }
    assert indexes == {
        "uq_company_ar_currencies_active_billing_default": (
            True,
            ("company_id",),
            "status = 'ACTIVE' AND billing_enabled = true "
            "AND is_default_billing = true",
        ),
        "uq_company_ar_currencies_active_receipt_default": (
            True,
            ("company_id",),
            "status = 'ACTIVE' AND receipt_enabled = true "
            "AND is_default_receipt = true",
        ),
    }


def test_company_ar_currency_status_values_are_closed() -> None:
    assert {status.value for status in CompanyARCurrencyStatus} == {
        "ACTIVE",
        "INACTIVE",
    }
