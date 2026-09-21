from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index, UniqueConstraint

from skmc_erp.ar.payment_term.model import (
    PaymentTerm,
    PaymentTermStatus,
    PaymentTermType,
)
from skmc_erp.model_base import Base


def test_payment_term_metadata_matches_contract() -> None:
    table = PaymentTerm.__table__
    assert table is Base.metadata.tables["ar.payment_terms"]
    assert table.schema == "ar"
    assert list(table.columns.keys()) == [
        "id",
        "company_id",
        "name",
        "code",
        "term_type",
        "credit_days",
        "is_default",
        "status",
        "created_at",
        "updated_at",
    ]
    assert str(table.c.id.server_default.arg) == "gen_random_uuid()"
    assert table.c.is_default.server_default.arg.text == "false"
    assert table.c.status.server_default is None
    assert table.c.name.type.length == 100
    assert table.c.code.type.length == 50


def test_payment_term_constraints_match_contract() -> None:
    table = PaymentTerm.__table__
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert set(checks) == {
        "ck_payment_terms_name_not_blank",
        "ck_payment_terms_term_type",
        "ck_payment_terms_credit_days",
        "ck_payment_terms_status",
        "ck_payment_terms_default_active",
    }

    uniques = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert uniques == {
        "uq_payment_terms_company_id_code": ("company_id", "code")
    }
    assert not any("name" in columns for columns in uniques.values())

    company_fk = next(
        constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    )
    assert company_fk.name == "fk_payment_terms_company_id_companies"
    assert company_fk.ondelete == "NO ACTION"
    assert tuple(
        element.target_fullname for element in company_fk.elements
    ) == ("core.companies.id",)

    default_index = next(
        index
        for index in table.indexes
        if isinstance(index, Index)
        and index.name == "uq_payment_terms_active_default_company"
    )
    assert default_index.unique
    assert tuple(column.name for column in default_index.columns) == ("company_id",)
    assert str(default_index.dialect_options["postgresql"]["where"]) == (
        "is_default = true AND status = 'ACTIVE'"
    )


def test_payment_term_enums_contain_only_approved_values() -> None:
    assert {value.value for value in PaymentTermType} == {
        "IMMEDIATE",
        "NET_DAYS",
    }
    assert {value.value for value in PaymentTermStatus} == {
        "ACTIVE",
        "INACTIVE",
    }
