from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from skmc_erp.core.organisation.model import Organisation, OrganisationStatus
from skmc_erp.core.tenant.model import Tenant
from skmc_erp.model_base import Base


def test_organisation_metadata_matches_approved_contract() -> None:
    table = Organisation.__table__

    assert Tenant.__table__ is Base.metadata.tables["core.tenants"]
    assert table.schema == "core"
    assert table.name == "organisations"
    assert Base.metadata.tables["core.organisations"] is table
    assert list(table.columns.keys()) == [
        "id",
        "tenant_id",
        "name",
        "status",
        "created_at",
        "updated_at",
    ]

    assert table.c.id.primary_key
    assert str(table.c.id.server_default.arg) == "gen_random_uuid()"
    assert not table.c.tenant_id.nullable
    assert table.c.name.type.length == 200
    assert not table.c.name.nullable
    assert table.c.status.type.length == 20
    assert not table.c.status.nullable
    assert table.c.status.server_default is None
    assert not table.c.status.type.native_enum

    for timestamp_column in (table.c.created_at, table.c.updated_at):
        assert timestamp_column.type.timezone
        assert not timestamp_column.nullable
        assert str(timestamp_column.server_default.arg) == "CURRENT_TIMESTAMP"

    check_constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert check_constraints == {
        "ck_organisations_name_not_blank": "btrim(name) <> ''",
        "ck_organisations_status": "status IN ('ACTIVE', 'INACTIVE')",
    }

    unique_constraints = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert unique_constraints == {
        "uq_organisations_tenant_id_name": ("tenant_id", "name"),
        "uq_organisations_tenant_id_id": ("tenant_id", "id"),
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
        "fk_organisations_tenant_id_tenants": (
            ("tenant_id",),
            ("core.tenants.id",),
            "NO ACTION",
        )
    }
    assert not table.indexes


def test_organisation_status_contains_only_approved_values() -> None:
    assert {status.value for status in OrganisationStatus} == {
        "ACTIVE",
        "INACTIVE",
    }
