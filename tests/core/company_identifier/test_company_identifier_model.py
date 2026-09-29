from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from skmc_erp.core.company_identifier.model import (
    CompanyIdentifier,
    CompanyIdentifierStatus,
    CompanyIdentifierType,
    CompanyIdentifierTypeStatus,
    EntityTypeIdentifierRule,
    IdentifierRequirementLevel,
)
from skmc_erp.model_base import Base


def _unique_constraints(table: object) -> dict[str | None, tuple[str, ...]]:
    return {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def _foreign_keys(
    table: object,
) -> dict[str | None, tuple[tuple[str, ...], tuple[str, ...], str | None]]:
    return {
        constraint.name: (
            tuple(element.parent.name for element in constraint.elements),
            tuple(element.target_fullname for element in constraint.elements),
            constraint.ondelete,
        )
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }


def test_company_identifier_type_metadata_matches_approved_contract() -> None:
    table = CompanyIdentifierType.__table__
    assert table is Base.metadata.tables["core.company_identifier_types"]
    assert list(table.columns) == [
        table.c.id,
        table.c.country_code,
        table.c.code,
        table.c.name,
        table.c.status,
    ]
    assert str(table.c.id.server_default.arg) == "gen_random_uuid()"
    assert _unique_constraints(table) == {
        "uq_company_identifier_types_country_code_code": (
            "country_code",
            "code",
        )
    }
    assert _foreign_keys(table) == {
        "fk_company_identifier_types_country_code_countries": (
            ("country_code",),
            ("core.countries.code",),
            "NO ACTION",
        )
    }
    assert {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    } == {
        "ck_company_identifier_types_country_code_format",
        "ck_company_identifier_types_code_format",
        "ck_company_identifier_types_name_not_blank",
        "ck_company_identifier_types_status",
    }


def test_company_identifier_metadata_matches_approved_contract() -> None:
    table = CompanyIdentifier.__table__
    assert table is Base.metadata.tables["core.company_identifiers"]
    assert list(table.columns.keys()) == [
        "id",
        "company_id",
        "identifier_type_id",
        "identifier_value",
        "status",
        "created_at",
        "updated_at",
    ]
    assert _unique_constraints(table) == {
        "uq_company_identifiers_company_id_type_id": (
            "company_id",
            "identifier_type_id",
        )
    }
    assert _foreign_keys(table) == {
        "fk_company_identifiers_company_id_companies": (
            ("company_id",),
            ("core.companies.id",),
            "NO ACTION",
        ),
        "fk_company_identifiers_type_id_types": (
            ("identifier_type_id",),
            ("core.company_identifier_types.id",),
            "NO ACTION",
        ),
    }


def test_entity_type_identifier_rule_metadata_matches_approved_contract() -> None:
    table = EntityTypeIdentifierRule.__table__
    assert table is Base.metadata.tables["core.entity_type_identifier_rules"]
    assert list(table.columns.keys()) == [
        "id",
        "entity_type_id",
        "identifier_type_id",
        "requirement_level",
        "created_at",
        "updated_at",
    ]
    assert _unique_constraints(table) == {
        "uq_entity_type_identifier_rules_entity_type_id_type_id": (
            "entity_type_id",
            "identifier_type_id",
        )
    }


def test_identifier_enums_contain_only_approved_values() -> None:
    assert {value.value for value in CompanyIdentifierTypeStatus} == {
        "ACTIVE",
        "INACTIVE",
    }
    assert {value.value for value in CompanyIdentifierStatus} == {
        "ACTIVE",
        "INACTIVE",
    }
    assert {value.value for value in IdentifierRequirementLevel} == {
        "REQUIRED",
        "OPTIONAL",
    }
