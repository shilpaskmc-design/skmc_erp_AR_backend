from sqlalchemy import CheckConstraint, UniqueConstraint

from skmc_erp.core.entity_type.model import EntityType, EntityTypeStatus
from skmc_erp.model_base import Base


def test_entity_type_metadata_matches_approved_contract() -> None:
    table = EntityType.__table__

    assert table.schema == "core"
    assert table.name == "entity_types"
    assert Base.metadata.tables["core.entity_types"] is table
    assert list(table.columns.keys()) == [
        "id",
        "country_code",
        "code",
        "name",
        "status",
    ]

    assert table.c.id.primary_key
    assert table.c.id.server_default is not None
    assert str(table.c.id.server_default.arg) == "gen_random_uuid()"

    assert table.c.country_code.type.length == 2
    assert not table.c.country_code.nullable
    assert table.c.country_code.server_default is None

    assert table.c.code.type.length == 50
    assert not table.c.code.nullable
    assert table.c.code.server_default is None

    assert table.c.name.type.length == 150
    assert not table.c.name.nullable
    assert not table.c.name.unique

    assert table.c.status.type.length == 20
    assert not table.c.status.nullable
    assert table.c.status.server_default is None
    assert not table.c.status.type.native_enum

    check_constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert check_constraints == {
        "ck_entity_types_country_code_format": "country_code ~ '^[A-Z]{2}$'",
        "ck_entity_types_code_not_blank": "btrim(code) <> ''",
        "ck_entity_types_code_format": (
            "code ~ '^[A-Z0-9]+(?:_[A-Z0-9]+)*$'"
        ),
        "ck_entity_types_name_not_blank": "btrim(name) <> ''",
        "ck_entity_types_status": "status IN ('ACTIVE', 'INACTIVE')",
    }

    unique_constraints = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert unique_constraints == {
        "uq_entity_types_country_code_code": ("country_code", "code")
    }
    assert not table.indexes


def test_entity_type_status_contains_only_approved_values() -> None:
    assert {status.value for status in EntityTypeStatus} == {
        "ACTIVE",
        "INACTIVE",
    }
