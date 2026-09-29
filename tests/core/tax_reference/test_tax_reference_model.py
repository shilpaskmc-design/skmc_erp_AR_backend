from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID

from skmc_erp.core.company.model import Company
from skmc_erp.core.geography.model import Country
from skmc_erp.core.tax_reference.model import (
    CompanyHsnSacCode,
    CompanyHsnSacTaxRate,
    HsnSacClassificationType,
    TaxRate,
    TaxReferenceStatus,
    TaxStatutoryCode,
    TaxStatutoryCodeKind,
    TaxStatutoryCodeRate,
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
    assert {value.value for value in TaxStatutoryCodeKind} == {
        "COMPONENT",
        "SECTION",
    }


def test_tax_statutory_code_metadata_matches_approved_contract() -> None:
    table = TaxStatutoryCode.__table__

    assert table.schema == "core"
    assert list(table.columns.keys()) == [
        "id",
        "tax_type_id",
        "code",
        "name",
        "description",
        "code_kind",
        "country_code",
        "status",
        "created_at",
        "updated_at",
    ]
    assert isinstance(table.c.id.type, PostgreSQLUUID)
    assert isinstance(table.c.tax_type_id.type, PostgreSQLUUID)
    assert isinstance(table.c.code.type, String) and table.c.code.type.length == 50
    assert isinstance(table.c.name.type, String) and table.c.name.type.length == 150
    assert (
        isinstance(table.c.description.type, String)
        and table.c.description.type.length == 500
    )
    assert table.c.code_kind.type.length == 20
    assert table.c.country_code.type.length == 2
    assert table.c.status.type.length == 20
    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone
    assert isinstance(table.c.updated_at.type, DateTime)
    assert table.c.updated_at.type.timezone

    assert not table.c.id.nullable
    assert not table.c.tax_type_id.nullable
    assert not table.c.code.nullable
    assert not table.c.name.nullable
    assert table.c.description.nullable
    assert not table.c.code_kind.nullable
    assert not table.c.country_code.nullable
    assert not table.c.status.nullable
    assert not table.c.created_at.nullable
    assert not table.c.updated_at.nullable

    assert str(table.c.id.server_default.arg) == "gen_random_uuid()"
    assert str(table.c.created_at.server_default.arg) == "CURRENT_TIMESTAMP"
    assert str(table.c.updated_at.server_default.arg) == "CURRENT_TIMESTAMP"
    for column_name in (
        "tax_type_id",
        "code",
        "name",
        "description",
        "code_kind",
        "country_code",
        "status",
    ):
        assert table.c[column_name].server_default is None

    assert table.primary_key.name == "pk_tax_statutory_codes"
    assert tuple(column.name for column in table.primary_key.columns) == ("id",)
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert checks == {
        "ck_tax_statutory_codes_code_not_blank": "btrim(code) <> ''",
        "ck_tax_statutory_codes_name_not_blank": "btrim(name) <> ''",
        "ck_tax_statutory_codes_code_kind": (
            "code_kind IN ('COMPONENT', 'SECTION')"
        ),
        "ck_tax_statutory_codes_country_code_format": (
            "country_code ~ '^[A-Z]{2}$'"
        ),
        "ck_tax_statutory_codes_status": "status IN ('ACTIVE', 'INACTIVE')",
    }
    uniques = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert uniques == {
        "uq_tax_statutory_codes_tax_type_country_kind_code": (
            "tax_type_id",
            "country_code",
            "code_kind",
            "code",
        )
    }
    foreign_keys = {
        constraint.name: (
            tuple(element.target_fullname for element in constraint.elements),
            constraint.ondelete,
        )
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    assert foreign_keys == {
        "fk_tax_statutory_codes_tax_type_id_tax_types": (
            ("core.tax_types.id",),
            "NO ACTION",
        )
    }
    assert not table.indexes
    assert "company_id" not in table.c
    assert "tenant_id" not in table.c
    assert "country_id" not in table.c
    assert "tax_rate_id" not in table.c


def test_tax_statutory_code_rate_metadata_matches_approved_contract() -> None:
    table = TaxStatutoryCodeRate.__table__

    assert table.schema == "core"
    assert list(table.columns.keys()) == [
        "id",
        "tax_statutory_code_id",
        "case_code",
        "rate_percent",
        "valid_from",
        "valid_to",
        "status",
        "created_at",
        "updated_at",
    ]
    assert isinstance(table.c.id.type, PostgreSQLUUID)
    assert isinstance(table.c.tax_statutory_code_id.type, PostgreSQLUUID)
    assert table.c.case_code.type.length == 50
    assert isinstance(table.c.rate_percent.type, Numeric)
    assert table.c.rate_percent.type.precision == 9
    assert table.c.rate_percent.type.scale == 6
    assert isinstance(table.c.valid_from.type, Date)
    assert isinstance(table.c.valid_to.type, Date)
    assert table.c.status.type.length == 20
    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone
    assert isinstance(table.c.updated_at.type, DateTime)
    assert table.c.updated_at.type.timezone

    assert not table.c.id.nullable
    assert not table.c.tax_statutory_code_id.nullable
    assert table.c.case_code.nullable
    assert not table.c.rate_percent.nullable
    assert not table.c.valid_from.nullable
    assert table.c.valid_to.nullable
    assert not table.c.status.nullable
    assert not table.c.created_at.nullable
    assert not table.c.updated_at.nullable

    assert str(table.c.id.server_default.arg) == "gen_random_uuid()"
    assert str(table.c.created_at.server_default.arg) == "CURRENT_TIMESTAMP"
    assert str(table.c.updated_at.server_default.arg) == "CURRENT_TIMESTAMP"
    for column_name in (
        "tax_statutory_code_id",
        "case_code",
        "rate_percent",
        "valid_from",
        "valid_to",
        "status",
    ):
        assert table.c[column_name].server_default is None

    assert table.primary_key.name == "pk_tax_statutory_code_rates"
    assert tuple(column.name for column in table.primary_key.columns) == ("id",)
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert checks == {
        "ck_tax_statutory_code_rates_case_code_not_blank": (
            "case_code IS NULL OR btrim(case_code) <> ''"
        ),
        "ck_tax_statutory_code_rates_rate_percent_range": (
            "rate_percent >= 0 AND rate_percent <= 100"
        ),
        "ck_tax_statutory_code_rates_date_order": (
            "valid_to IS NULL OR valid_to >= valid_from"
        ),
        "ck_tax_statutory_code_rates_status": (
            "status IN ('ACTIVE', 'INACTIVE')"
        ),
    }
    foreign_keys = {
        constraint.name: (
            tuple(element.target_fullname for element in constraint.elements),
            constraint.ondelete,
        )
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    assert foreign_keys == {
        "fk_tax_statutory_code_rates_statutory_code": (
            ("core.tax_statutory_codes.id",),
            "NO ACTION",
        )
    }

    exclusions = {
        constraint.name: constraint
        for constraint in table.constraints
        if isinstance(constraint, ExcludeConstraint)
    }
    assert set(exclusions) == {
        "ex_tax_statutory_code_rates_active_named_overlap",
        "ex_tax_statutory_code_rates_active_default_overlap",
    }
    named = exclusions["ex_tax_statutory_code_rates_active_named_overlap"]
    default = exclusions["ex_tax_statutory_code_rates_active_default_overlap"]
    assert named.using == "gist"
    assert default.using == "gist"
    assert str(named.where) == "status = 'ACTIVE' AND case_code IS NOT NULL"
    assert str(default.where) == "status = 'ACTIVE' AND case_code IS NULL"
    assert [(item[1], item[2]) for item in named._render_exprs] == [
        ("tax_statutory_code_id", "="),
        ("case_code", "="),
        (None, "&&"),
    ]
    assert [(item[1], item[2]) for item in default._render_exprs] == [
        ("tax_statutory_code_id", "="),
        (None, "&&"),
    ]
    assert "daterange(valid_from, valid_to, '[]')" in str(
        named._render_exprs[-1][0]
    )
    assert "daterange(valid_from, valid_to, '[]')" in str(
        default._render_exprs[-1][0]
    )
    assert not table.indexes
    assert "tax_rate_id" not in table.c
    assert "tax_type_id" not in table.c
    assert "code_kind" not in table.c
    assert "company_id" not in table.c
    assert "tenant_id" not in table.c
