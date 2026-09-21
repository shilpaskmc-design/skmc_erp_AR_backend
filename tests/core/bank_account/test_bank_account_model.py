from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index, UniqueConstraint

from skmc_erp.core.bank_account.model import (
    CompanyBankAccount,
    CompanyBankAccountStatus,
)
from skmc_erp.model_base import Base


def test_company_bank_account_metadata_matches_contract() -> None:
    table = CompanyBankAccount.__table__
    assert table is Base.metadata.tables["core.company_bank_accounts"]
    assert table.schema == "core"
    assert list(table.columns.keys()) == [
        "id",
        "company_id",
        "account_holder_name",
        "bank_name",
        "account_number",
        "branch_name",
        "ifsc",
        "swift",
        "iban",
        "currency_code",
        "account_type",
        "gl_account_id",
        "is_default_for_billing",
        "status",
        "created_at",
        "updated_at",
    ]
    assert table.c.gl_account_id.nullable
    assert table.c.account_type.nullable
    assert table.c.is_default_for_billing.server_default.arg.text == "false"
    assert table.c.status.server_default is None


def test_company_bank_account_constraints_match_contract() -> None:
    table = CompanyBankAccount.__table__
    checks = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert checks == {
        "ck_company_bank_accounts_holder_name_not_blank",
        "ck_company_bank_accounts_bank_name_not_blank",
        "ck_company_bank_accounts_status",
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
        "fk_company_bank_accounts_company_id_companies": (
            ("company_id",),
            ("core.companies.id",),
            "NO ACTION",
        ),
        "fk_company_bank_accounts_currency_code_currencies": (
            ("currency_code",),
            ("core.currencies.code",),
            "NO ACTION",
        ),
        "fk_company_bank_accounts_company_gl_account": (
            ("company_id", "gl_account_id"),
            ("core.gl_accounts.company_id", "core.gl_accounts.id"),
            "NO ACTION",
        ),
    }

    uniques = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert uniques == {
        "uq_company_bank_accounts_company_id_id": ("company_id", "id")
    }
    assert not any("account_number" in columns for columns in uniques.values())

    default_index = next(
        index
        for index in table.indexes
        if isinstance(index, Index)
        and index.name == "uq_company_bank_accounts_active_billing_default"
    )
    assert default_index.unique
    assert tuple(column.name for column in default_index.columns) == (
        "company_id",
        "currency_code",
    )
    assert str(default_index.dialect_options["postgresql"]["where"]) == (
        "is_default_for_billing = true AND status = 'ACTIVE'"
    )


def test_company_bank_account_status_contains_only_approved_values() -> None:
    assert {status.value for status in CompanyBankAccountStatus} == {
        "ACTIVE",
        "INACTIVE",
    }
