from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from skmc_erp.core.company.model import Company
from skmc_erp.core.company_gst_registration.model import (
    CompanyGSTRegistration,
    CompanyGSTRegistrationStatus,
    GSTRegistrationType,
    GSTRegistrationTypeStatus,
)
from skmc_erp.core.geography.model import CountrySubdivision
from skmc_erp.model_base import Base


def test_gst_registration_type_metadata_matches_approved_contract() -> None:
    table = GSTRegistrationType.__table__

    assert table.schema == "core"
    assert Base.metadata.tables["core.gst_registration_types"] is table
    assert list(table.columns) == [
        table.c.id,
        table.c.code,
        table.c.name,
        table.c.description,
        table.c.status,
        table.c.created_at,
        table.c.updated_at,
    ]
    assert str(table.c.id.server_default.arg) == "gen_random_uuid()"
    assert table.c.code.type.length == 50
    assert table.c.name.type.length == 100
    assert table.c.description.type.length == 500
    assert table.c.description.nullable
    assert table.c.status.server_default is None
    assert not table.c.status.type.native_enum

    uniques = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert uniques == {"uq_gst_registration_types_code": ("code",)}


def test_company_gst_registration_metadata_matches_approved_contract() -> None:
    table = CompanyGSTRegistration.__table__

    assert Company.__table__ is Base.metadata.tables["core.companies"]
    assert CountrySubdivision.__table__ is Base.metadata.tables[
        "core.country_subdivisions"
    ]
    assert table.schema == "core"
    assert Base.metadata.tables["core.company_gst_registrations"] is table
    assert list(table.columns.keys()) == [
        "id",
        "company_id",
        "gstin",
        "registered_legal_name",
        "gst_registration_type_id",
        "subdivision_code",
        "valid_from",
        "valid_to",
        "status",
        "created_at",
        "updated_at",
    ]
    assert str(table.c.id.server_default.arg) == "gen_random_uuid()"
    assert not table.c.company_id.nullable
    assert table.c.gstin.type.length == 15
    assert not table.c.gstin.nullable
    assert table.c.registered_legal_name.type.length == 255
    assert table.c.registered_legal_name.nullable
    assert table.c.gst_registration_type_id.nullable
    assert table.c.subdivision_code.type.length == 10
    assert not table.c.subdivision_code.nullable
    assert table.c.valid_from.nullable
    assert table.c.valid_to.nullable
    assert table.c.status.type.length == 20
    assert table.c.status.server_default is None
    assert not table.c.status.type.native_enum

    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert checks == {
        "ck_company_gst_registrations_gstin_format": (
            "gstin ~ "
            "'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$'"
        ),
        "ck_company_gst_registrations_legal_name_not_blank": (
            "registered_legal_name IS NULL "
            "OR btrim(registered_legal_name) <> ''"
        ),
        "ck_company_gst_registrations_date_order": (
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from"
        ),
        "ck_company_gst_registrations_status": (
            "status IN ('DRAFT', 'ACTIVE', 'INACTIVE')"
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
        "fk_company_gst_registrations_company_id_companies": (
            ("company_id",),
            ("core.companies.id",),
            "NO ACTION",
        ),
        "fk_company_gst_registrations_type_id_types": (
            ("gst_registration_type_id",),
            ("core.gst_registration_types.id",),
            "NO ACTION",
        ),
        "fk_company_gst_registrations_subdivision_code": (
            ("subdivision_code",),
            ("core.country_subdivisions.code",),
            "NO ACTION",
        ),
    }

    indexes = {index.name: index for index in table.indexes}
    assert set(indexes) == {
        "ix_company_gst_registrations_company_id",
        "uq_company_gst_registrations_active_company_subdivision",
    }
    active_unique = indexes[
        "uq_company_gst_registrations_active_company_subdivision"
    ]
    assert active_unique.unique
    assert tuple(column.name for column in active_unique.columns) == (
        "company_id",
        "subdivision_code",
    )
    assert str(active_unique.dialect_options["postgresql"]["where"]) == (
        "status = 'ACTIVE'"
    )


def test_gst_statuses_contain_only_approved_values() -> None:
    assert {status.value for status in GSTRegistrationTypeStatus} == {
        "ACTIVE",
        "INACTIVE",
    }
    assert {status.value for status in CompanyGSTRegistrationStatus} == {
        "DRAFT",
        "ACTIVE",
        "INACTIVE",
    }
