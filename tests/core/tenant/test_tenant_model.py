from sqlalchemy import CheckConstraint, UniqueConstraint

from skmc_erp.core.tenant.model import Tenant, TenantStatus
from skmc_erp.model_base import Base


def test_tenant_metadata_matches_approved_contract() -> None:
    table = Tenant.__table__

    assert table.schema == "core"
    assert table.name == "tenants"
    assert Base.metadata.tables["core.tenants"] is table
    assert list(table.columns.keys()) == [
        "id",
        "name",
        "code",
        "status",
        "created_at",
        "updated_at",
    ]

    assert table.c.id.primary_key
    assert table.c.id.server_default is not None
    assert str(table.c.id.server_default.arg) == "gen_random_uuid()"

    assert table.c.name.type.length == 200
    assert not table.c.name.nullable
    assert not table.c.name.unique

    assert table.c.code.type.length == 50
    assert not table.c.code.nullable
    assert table.c.code.server_default is not None
    assert str(table.c.code.server_default.arg) == "core.next_tenant_code()"

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
        "ck_tenants_name_not_blank": "btrim(name) <> ''",
        "ck_tenants_code_not_blank": "btrim(code) <> ''",
        "ck_tenants_status": "status IN ('ACTIVE', 'SUSPENDED', 'INACTIVE')",
    }

    unique_constraints = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert unique_constraints == {"uq_tenants_code": ("code",)}
    assert not table.indexes


def test_tenant_status_contains_only_approved_values() -> None:
    assert {status.value for status in TenantStatus} == {
        "ACTIVE",
        "SUSPENDED",
        "INACTIVE",
    }
