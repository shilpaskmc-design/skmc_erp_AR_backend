from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from skmc_erp.core.geography.model import (
    Country,
    CountryStatus,
    CountrySubdivision,
    CountrySubdivisionStatus,
)
from skmc_erp.model_base import Base


def test_country_metadata_matches_approved_contract() -> None:
    table = Country.__table__

    assert table.schema == "core"
    assert table.name == "countries"
    assert Base.metadata.tables["core.countries"] is table
    assert list(table.columns.keys()) == [
        "code",
        "name",
        "status",
        "created_at",
        "updated_at",
    ]

    assert table.c.code.primary_key
    assert table.c.code.type.length == 2
    assert not table.c.code.nullable
    assert table.c.name.type.length == 100
    assert not table.c.name.nullable
    assert not table.c.name.unique
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
        "ck_countries_code_format": "code ~ '^[A-Z]{2}$'",
        "ck_countries_name_not_blank": "btrim(name) <> ''",
        "ck_countries_status": "status IN ('ACTIVE', 'INACTIVE')",
    }
    assert not table.indexes


def test_country_subdivision_metadata_matches_approved_contract() -> None:
    table = CountrySubdivision.__table__

    assert Country.__table__ is Base.metadata.tables["core.countries"]
    assert table.schema == "core"
    assert table.name == "country_subdivisions"
    assert Base.metadata.tables["core.country_subdivisions"] is table
    assert list(table.columns.keys()) == [
        "id",
        "country_code",
        "code",
        "name",
        "subdivision_type",
        "gst_state_code",
        "status",
        "created_at",
        "updated_at",
    ]

    assert table.c.id.primary_key
    assert str(table.c.id.server_default.arg) == "gen_random_uuid()"
    assert table.c.country_code.type.length == 2
    assert not table.c.country_code.nullable
    assert table.c.code.type.length == 10
    assert not table.c.code.nullable
    assert table.c.name.type.length == 150
    assert not table.c.name.nullable
    assert not table.c.name.unique
    assert table.c.subdivision_type.type.length == 50
    assert not table.c.subdivision_type.nullable
    assert table.c.gst_state_code.type.length == 2
    assert table.c.gst_state_code.nullable
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
        "ck_country_subdivisions_code_format": (
            "code ~ '^[A-Z]{2}-[A-Z0-9]{1,3}$'"
        ),
        "ck_country_subdivisions_country_prefix": (
            "left(code, 2) = country_code"
        ),
        "ck_country_subdivisions_name_not_blank": "btrim(name) <> ''",
        "ck_country_subdivisions_type_format": (
            "subdivision_type ~ '^[A-Z]+(_[A-Z]+)*$'"
        ),
        "ck_country_subdivisions_gst_state_code_format": (
            "gst_state_code IS NULL OR gst_state_code ~ '^[0-9]{2}$'"
        ),
        "ck_country_subdivisions_status": (
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
        "fk_country_subdivisions_country_code_countries": (
            ("country_code",),
            ("core.countries.code",),
            "NO ACTION",
        )
    }

    unique_constraints = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert unique_constraints == {
        "uq_country_subdivisions_code": ("code",),
        "uq_country_subdivisions_country_code_code": (
            "country_code",
            "code",
        ),
    }
    assert {index.name for index in table.indexes} == {
        "ix_country_subdivisions_country_code",
        "uq_country_subdivisions_country_gst_state_code",
    }


def test_geographic_statuses_contain_only_approved_values() -> None:
    assert {status.value for status in CountryStatus} == {
        "ACTIVE",
        "INACTIVE",
    }
    assert {status.value for status in CountrySubdivisionStatus} == {
        "ACTIVE",
        "INACTIVE",
    }
