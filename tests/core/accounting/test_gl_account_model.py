from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index, UniqueConstraint

from skmc_erp.core.accounting.model import GlAccount, GlAccountStatus
from skmc_erp.model_base import Base


def test_gl_account_metadata_matches_contract() -> None:
    table = GlAccount.__table__
    assert table is Base.metadata.tables["core.gl_accounts"]
    assert table.schema == "core"
    assert list(table.columns.keys()) == [
        "id",
        "company_id",
        "account_code",
        "account_name",
        "valid_from",
        "valid_to",
        "status",
        "created_at",
        "updated_at",
    ]
    assert table.c.account_code.nullable
    assert table.c.account_code.type.length == 50
    assert table.c.account_name.type.length == 200
    assert table.c.valid_to.nullable
    assert str(table.c.id.server_default.arg) == "gen_random_uuid()"
    assert table.c.status.server_default is None


def test_gl_account_constraints_match_contract() -> None:
    table = GlAccount.__table__
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert set(checks) == {
        "ck_gl_accounts_code_not_blank",
        "ck_gl_accounts_name_not_blank",
        "ck_gl_accounts_valid_range",
        "ck_gl_accounts_status",
    }

    uniques = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert uniques == {"uq_gl_accounts_company_id_id": ("company_id", "id")}
    assert not any("account_name" in columns for columns in uniques.values())

    company_fk = next(
        constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    )
    assert company_fk.name == "fk_gl_accounts_company_id_companies"
    assert company_fk.ondelete == "NO ACTION"
    assert tuple(
        element.target_fullname for element in company_fk.elements
    ) == ("core.companies.id",)

    code_index = next(
        index
        for index in table.indexes
        if isinstance(index, Index)
        and index.name == "uq_gl_accounts_company_id_account_code"
    )
    assert code_index.unique
    assert tuple(column.name for column in code_index.columns) == (
        "company_id",
        "account_code",
    )
    assert str(code_index.dialect_options["postgresql"]["where"]) == (
        "account_code IS NOT NULL"
    )


def test_gl_account_status_contains_only_approved_values() -> None:
    assert {status.value for status in GlAccountStatus} == {
        "ACTIVE",
        "INACTIVE",
    }
