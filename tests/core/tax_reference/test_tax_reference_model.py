from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from skmc_erp.core.company.model import Company
from skmc_erp.core.geography.model import Country
from skmc_erp.core.tax_reference.model import (
    CompanyHsnSacCode,
    CompanyHsnSacTaxRate,
    HsnSacClassificationType,
    TaxRate,
    TaxReferenceStatus,
    TaxTreatment,
    TaxType,
)
from skmc_erp.model_base import Base


def test_tax_reference_metadata_uses_core_schema_and_approved_columns() -> None:
    assert Company.__table__ is Base.metadata.tables["core.companies"]
    assert Country.__table__ is Base.metadata.tables["core.countries"]
    expected_columns = {
        TaxType: [
            "id", "code", "name", "country_code", "status", "created_at", "updated_at"
        ],
        CompanyHsnSacCode: [
            "id", "company_id", "classification_type", "code", "description",
            "status", "created_at", "updated_at",
        ],
        TaxRate: [
            "id", "tax_type_id", "rate_percent", "country_code", "status",
            "created_at", "updated_at",
        ],
        CompanyHsnSacTaxRate: [
            "id", "company_hsn_sac_code_id", "tax_rate_id", "valid_from",
            "valid_to", "status", "created_at", "updated_at",
        ],
        TaxTreatment: [
            "id", "code", "name", "tax_type_id", "country_code", "status",
            "created_at", "updated_at",
        ],
    }

    for model, columns in expected_columns.items():
        table = model.__table__
        assert table.schema == "core"
        assert list(table.columns.keys()) == columns
        assert str(table.c.id.server_default.arg) == "gen_random_uuid()"
        assert table.c.status.server_default is None
        assert not table.c.status.type.native_enum


def test_tax_reference_constraints_match_contract() -> None:
    rate_checks = {
        constraint.name
        for constraint in TaxRate.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert rate_checks == {
        "ck_tax_rates_rate_percent_range",
        "ck_tax_rates_status",
    }

    hsn_uniques = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in CompanyHsnSacCode.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert hsn_uniques["uq_company_hsn_sac_codes_company_type_code"] == (
        "company_id", "classification_type", "code"
    )

    country_fks = {
        constraint.name
        for model in (TaxType, TaxRate, TaxTreatment)
        for constraint in model.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
        and any(
            element.target_fullname == "core.countries.code"
            for element in constraint.elements
        )
    }
    assert country_fks == {
        "fk_tax_types_country_code_countries",
        "fk_tax_rates_country_code_countries",
        "fk_tax_treatments_country_code_countries",
    }


def test_tax_reference_enums_contain_only_approved_values() -> None:
    assert {value.value for value in TaxReferenceStatus} == {"ACTIVE", "INACTIVE"}
    assert {value.value for value in HsnSacClassificationType} == {"HSN", "SAC"}
