from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from skmc_erp.ar.fx.model import (
    FXPolicy,
    FXPolicyPurpose,
    FXPolicyRateType,
    FXPolicyStatus,
)
from skmc_erp.model_base import Base


def test_fx_policy_metadata_matches_contract() -> None:
    table = FXPolicy.__table__

    assert table is Base.metadata.tables["ar.fx_policies"]
    assert table.schema == "ar"
    assert list(table.columns.keys()) == [
        "id",
        "company_id",
        "purpose",
        "default_rate_type",
        "allow_user_fixed_override",
        "reason_required_for_override",
        "status",
        "created_at",
        "updated_at",
    ]
    assert table.primary_key.name == "pk_fx_policies"
    assert table.c.id.type.as_uuid
    assert str(table.c.id.server_default.arg) == "gen_random_uuid()"
    assert table.c.purpose.type.length == 20
    assert table.c.default_rate_type.type.length == 20
    assert table.c.status.type.length == 20
    for enum_column in (
        table.c.purpose,
        table.c.default_rate_type,
        table.c.status,
    ):
        assert not enum_column.type.native_enum
        assert enum_column.server_default is None

    for boolean_column in (
        table.c.allow_user_fixed_override,
        table.c.reason_required_for_override,
    ):
        assert not boolean_column.nullable
        assert str(boolean_column.server_default.arg) == "false"

    for timestamp_column in (table.c.created_at, table.c.updated_at):
        assert timestamp_column.type.timezone
        assert not timestamp_column.nullable
        assert str(timestamp_column.server_default.arg) == "CURRENT_TIMESTAMP"


def test_fx_policy_constraints_match_contract() -> None:
    table = FXPolicy.__table__
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert checks == {
        "ck_fx_policies_purpose": (
            "purpose IN ('BILLING', 'RECEIPT', 'REPORTING')"
        ),
        "ck_fx_policies_default_rate_type": (
            "default_rate_type IN ('CORPORATE', 'SPOT')"
        ),
        "ck_fx_policies_override_reason_requires_override": (
            "NOT reason_required_for_override OR allow_user_fixed_override"
        ),
        "ck_fx_policies_status": "status IN ('ACTIVE', 'INACTIVE')",
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
        "fk_fx_policies_company_id_companies": (
            ("company_id",),
            ("core.companies.id",),
            "NO ACTION",
        )
    }

    uniques = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert uniques == {
        "uq_fx_policies_company_id_purpose": ("company_id", "purpose")
    }
    assert not table.indexes


def test_fx_policy_enums_contain_only_approved_values() -> None:
    assert {value.value for value in FXPolicyPurpose} == {
        "BILLING",
        "RECEIPT",
        "REPORTING",
    }
    assert {value.value for value in FXPolicyRateType} == {
        "CORPORATE",
        "SPOT",
    }
    assert {value.value for value in FXPolicyStatus} == {
        "ACTIVE",
        "INACTIVE",
    }
