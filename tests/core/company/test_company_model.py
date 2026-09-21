from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from skmc_erp.core.company.model import (
    Company,
    CompanyBusinessNature,
    CompanyStatus,
)
from skmc_erp.core.currency.model import Currency
from skmc_erp.core.entity_type.model import EntityType
from skmc_erp.core.organisation.model import Organisation
from skmc_erp.core.tenant.model import Tenant
from skmc_erp.model_base import Base


def test_company_metadata_matches_approved_contract() -> None:
    table = Company.__table__

    assert Tenant.__table__ is Base.metadata.tables["core.tenants"]
    assert EntityType.__table__ is Base.metadata.tables["core.entity_types"]
    assert Currency.__table__ is Base.metadata.tables["core.currencies"]
    assert Organisation.__table__ is Base.metadata.tables["core.organisations"]
    assert table.schema == "core"
    assert table.name == "companies"
    assert Base.metadata.tables["core.companies"] is table
    assert list(table.columns.keys()) == [
        "id",
        "tenant_id",
        "organisation_id",
        "legal_name",
        "display_name",
        "company_code",
        "entity_type_id",
        "country_code",
        "email",
        "phone",
        "website",
        "base_timezone",
        "base_currency_code",
        "business_nature",
        "status",
        "created_at",
        "updated_at",
    ]

    assert table.c.id.primary_key
    assert str(table.c.id.server_default.arg) == "gen_random_uuid()"
    assert not table.c.tenant_id.nullable
    assert table.c.organisation_id.nullable
    assert table.c.legal_name.type.length == 255
    assert not table.c.legal_name.nullable
    assert not table.c.legal_name.unique
    assert table.c.display_name.type.length == 200
    assert table.c.display_name.nullable

    assert table.c.company_code.type.length == 50
    assert not table.c.company_code.nullable
    assert str(table.c.company_code.server_default.arg) == (
        "core.next_company_code()"
    )

    assert table.c.entity_type_id.nullable
    assert table.c.country_code.type.length == 2
    assert table.c.country_code.nullable
    assert table.c.email.type.length == 320
    assert table.c.phone.type.length == 32
    assert table.c.website.type.length == 2048
    assert table.c.base_timezone.type.length == 64
    assert table.c.base_currency_code.type.length == 3

    assert table.c.business_nature.type.length == 20
    assert table.c.business_nature.nullable
    assert not table.c.business_nature.type.native_enum
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
        "ck_companies_legal_name_not_blank": "btrim(legal_name) <> ''",
        "ck_companies_display_name_not_blank": (
            "display_name IS NULL OR btrim(display_name) <> ''"
        ),
        "ck_companies_company_code_format": (
            "company_code ~ '^COM[0-9]{6,}$'"
        ),
        "ck_companies_country_code_format": (
            "country_code IS NULL OR country_code ~ '^[A-Z]{2}$'"
        ),
        "ck_companies_email_not_blank": (
            "email IS NULL OR btrim(email) <> ''"
        ),
        "ck_companies_phone_not_blank": (
            "phone IS NULL OR btrim(phone) <> ''"
        ),
        "ck_companies_website_not_blank": (
            "website IS NULL OR btrim(website) <> ''"
        ),
        "ck_companies_base_timezone_not_blank": (
            "base_timezone IS NULL OR btrim(base_timezone) <> ''"
        ),
        "ck_companies_business_nature": (
            "business_nature IS NULL OR "
            "business_nature IN ('SERVICES', 'GOODS', 'BOTH')"
        ),
        "ck_companies_status": "status IN ('DRAFT', 'ACTIVE', 'INACTIVE')",
    }

    unique_constraints = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert unique_constraints == {
        "uq_companies_company_code": ("company_code",)
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
        "fk_companies_tenant_id_tenants": (
            ("tenant_id",),
            ("core.tenants.id",),
            "NO ACTION",
        ),
        "fk_companies_tenant_organisation": (
            ("tenant_id", "organisation_id"),
            ("core.organisations.tenant_id", "core.organisations.id"),
            "NO ACTION",
        ),
        "fk_companies_entity_type_id_entity_types": (
            ("entity_type_id",),
            ("core.entity_types.id",),
            "NO ACTION",
        ),
        "fk_companies_base_currency_code_currencies": (
            ("base_currency_code",),
            ("core.currencies.code",),
            "NO ACTION",
        ),
    }
    assert {index.name for index in table.indexes} == {
        "ix_companies_tenant_id_organisation_id"
    }


def test_company_enums_contain_only_approved_values() -> None:
    assert {status.value for status in CompanyStatus} == {
        "DRAFT",
        "ACTIVE",
        "INACTIVE",
    }
    assert {nature.value for nature in CompanyBusinessNature} == {
        "SERVICES",
        "GOODS",
        "BOTH",
    }
