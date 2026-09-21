from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index

from skmc_erp.core.company.model import Company
from skmc_erp.core.company_location.model import (
    CompanyLocation,
    CompanyLocationStatus,
)
from skmc_erp.core.company_gst_registration.model import CompanyGSTRegistration
from skmc_erp.core.cost_center.model import CostCenterLocation
from skmc_erp.core.geography.model import Country, CountrySubdivision
from skmc_erp.model_base import Base


def test_company_location_metadata_matches_approved_contract() -> None:
    table = CompanyLocation.__table__

    assert Company.__table__ is Base.metadata.tables["core.companies"]
    assert Country.__table__ is Base.metadata.tables["core.countries"]
    assert CountrySubdivision.__table__ is Base.metadata.tables[
        "core.country_subdivisions"
    ]
    assert CostCenterLocation.__table__ is Base.metadata.tables[
        "core.cost_center_locations"
    ]
    assert table.schema == "core"
    assert table.name == "company_locations"
    assert list(table.columns.keys()) == [
        "id",
        "company_id",
        "location_name",
        "address_line_1",
        "address_line_2",
        "city",
        "district",
        "subdivision_code",
        "country_code",
        "gst_registration_id",
        "cost_center_location_id",
        "postal_code",
        "is_registered_office",
        "is_corporate_office",
        "is_branch",
        "is_billing_office",
        "is_warehouse",
        "other_purpose",
        "status",
        "created_at",
        "updated_at",
    ]

    assert table.c.id.primary_key
    assert str(table.c.id.server_default.arg) == "gen_random_uuid()"
    assert not table.c.company_id.nullable
    assert table.c.location_name.type.length == 150
    assert not table.c.location_name.nullable
    assert table.c.address_line_1.type.length == 255
    assert not table.c.address_line_1.nullable
    assert table.c.address_line_2.nullable
    assert table.c.city.type.length == 100
    assert not table.c.city.nullable
    assert table.c.district.type.length == 100
    assert table.c.district.nullable
    assert table.c.subdivision_code.type.length == 10
    assert table.c.subdivision_code.nullable
    assert table.c.country_code.type.length == 2
    assert not table.c.country_code.nullable
    assert table.c.gst_registration_id.nullable
    assert table.c.cost_center_location_id.nullable
    assert table.c.postal_code.type.length == 20
    assert table.c.postal_code.nullable
    assert table.c.other_purpose.type.length == 150
    assert table.c.other_purpose.nullable
    assert table.c.status.type.length == 20
    assert not table.c.status.nullable
    assert table.c.status.server_default is None
    assert not table.c.status.type.native_enum

    for purpose_column in (
        table.c.is_registered_office,
        table.c.is_corporate_office,
        table.c.is_branch,
        table.c.is_billing_office,
        table.c.is_warehouse,
    ):
        assert not purpose_column.nullable
        assert str(purpose_column.server_default.arg) == "false"

    for timestamp_column in (table.c.created_at, table.c.updated_at):
        assert timestamp_column.type.timezone
        assert not timestamp_column.nullable
        assert str(timestamp_column.server_default.arg) == "CURRENT_TIMESTAMP"

    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert checks["ck_company_locations_name_not_blank"] == (
        "btrim(location_name) <> ''"
    )
    assert checks["ck_company_locations_at_least_one_purpose"] == (
        "is_registered_office OR is_corporate_office OR is_branch "
        "OR is_billing_office OR is_warehouse OR other_purpose IS NOT NULL"
    )
    assert checks["ck_company_locations_status"] == (
        "status IN ('ACTIVE', 'INACTIVE')"
    )
    assert checks["ck_company_locations_gst_requires_subdivision"] == (
        "gst_registration_id IS NULL OR subdivision_code IS NOT NULL"
    )

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
        "fk_company_locations_company_id_companies": (
            ("company_id",),
            ("core.companies.id",),
            "NO ACTION",
        ),
        "fk_company_locations_country_code_countries": (
            ("country_code",),
            ("core.countries.code",),
            "NO ACTION",
        ),
        "fk_company_locations_country_subdivision": (
            ("country_code", "subdivision_code"),
            (
                "core.country_subdivisions.country_code",
                "core.country_subdivisions.code",
            ),
            "NO ACTION",
        ),
        "fk_company_locations_gst_registration_jurisdiction": (
            ("company_id", "gst_registration_id", "subdivision_code"),
            (
                "core.company_gst_registrations.company_id",
                "core.company_gst_registrations.id",
                "core.company_gst_registrations.subdivision_code",
            ),
            "NO ACTION",
        ),
        "fk_company_locations_company_cost_center_location": (
            ("company_id", "cost_center_location_id"),
            (
                "core.cost_center_locations.company_id",
                "core.cost_center_locations.id",
            ),
            "NO ACTION",
        ),
    }

    indexes: dict[str, Index] = {index.name: index for index in table.indexes}
    assert set(indexes) == {
        "ix_company_locations_company_id",
        "ix_company_locations_gst_registration_id",
        "uq_company_locations_active_registered_office",
    }
    registered_index = indexes[
        "uq_company_locations_active_registered_office"
    ]
    assert registered_index.unique
    assert tuple(column.name for column in registered_index.columns) == (
        "company_id",
    )
    assert str(registered_index.dialect_options["postgresql"]["where"]) == (
        "status = 'ACTIVE' AND is_registered_office"
    )


def test_company_location_status_contains_only_approved_values() -> None:
    assert {status.value for status in CompanyLocationStatus} == {
        "ACTIVE",
        "INACTIVE",
    }
