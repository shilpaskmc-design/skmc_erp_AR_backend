from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Numeric,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from skmc_erp.model_base import Base


class TaxReferenceStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class HsnSacClassificationType(StrEnum):
    HSN = "HSN"
    SAC = "SAC"


class TaxType(Base):
    __tablename__ = "tax_types"
    __table_args__ = (
        CheckConstraint("btrim(code) <> ''", name="ck_tax_types_code_not_blank"),
        CheckConstraint("btrim(name) <> ''", name="ck_tax_types_name_not_blank"),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_tax_types_status",
        ),
        ForeignKeyConstraint(
            ["country_code"],
            ["core.countries.code"],
            name="fk_tax_types_country_code_countries",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_tax_types"),
        UniqueConstraint(
            "country_code",
            "code",
            name="uq_tax_types_country_code_code",
        ),
        {"schema": "core"},
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    status: Mapped[TaxReferenceStatus] = mapped_column(
        Enum(
            TaxReferenceStatus,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=20,
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class CompanyHsnSacCode(Base):
    __tablename__ = "company_hsn_sac_codes"
    __table_args__ = (
        CheckConstraint(
            "classification_type IN ('HSN', 'SAC')",
            name="ck_company_hsn_sac_codes_classification_type",
        ),
        CheckConstraint(
            "btrim(code) <> ''",
            name="ck_company_hsn_sac_codes_code_not_blank",
        ),
        CheckConstraint(
            "btrim(description) <> ''",
            name="ck_company_hsn_sac_codes_description_not_blank",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_company_hsn_sac_codes_status",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_hsn_sac_codes_company_id_companies",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_company_hsn_sac_codes"),
        UniqueConstraint(
            "company_id",
            "classification_type",
            "code",
            name="uq_company_hsn_sac_codes_company_type_code",
        ),
        UniqueConstraint(
            "company_id",
            "id",
            name="uq_company_hsn_sac_codes_company_id_id",
        ),
        {"schema": "core"},
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    company_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    classification_type: Mapped[HsnSacClassificationType] = mapped_column(
        Enum(
            HsnSacClassificationType,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=10,
        ),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[TaxReferenceStatus] = mapped_column(
        Enum(
            TaxReferenceStatus,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=20,
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class TaxRate(Base):
    __tablename__ = "tax_rates"
    __table_args__ = (
        CheckConstraint(
            "rate_percent >= 0 AND rate_percent <= 100",
            name="ck_tax_rates_rate_percent_range",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_tax_rates_status",
        ),
        ForeignKeyConstraint(
            ["tax_type_id"],
            ["core.tax_types.id"],
            name="fk_tax_rates_tax_type_id_tax_types",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["country_code"],
            ["core.countries.code"],
            name="fk_tax_rates_country_code_countries",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_tax_rates"),
        UniqueConstraint(
            "tax_type_id",
            "country_code",
            "rate_percent",
            name="uq_tax_rates_tax_type_country_rate",
        ),
        {"schema": "core"},
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tax_type_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    rate_percent: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    status: Mapped[TaxReferenceStatus] = mapped_column(
        Enum(
            TaxReferenceStatus,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=20,
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class CompanyHsnSacTaxRate(Base):
    __tablename__ = "company_hsn_sac_tax_rates"
    __table_args__ = (
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_company_hsn_sac_tax_rates_date_order",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_company_hsn_sac_tax_rates_status",
        ),
        ForeignKeyConstraint(
            ["company_hsn_sac_code_id"],
            ["core.company_hsn_sac_codes.id"],
            name="fk_company_hsn_sac_tax_rates_hsn_sac_code",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["tax_rate_id"],
            ["core.tax_rates.id"],
            name="fk_company_hsn_sac_tax_rates_tax_rate",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_company_hsn_sac_tax_rates"),
        ExcludeConstraint(
            ("company_hsn_sac_code_id", "="),
            ("tax_rate_id", "="),
            (
                text("daterange(valid_from, valid_to, '[]')"),
                "&&",
            ),
            name="ex_company_hsn_sac_tax_rates_active_overlap",
            using="gist",
            where=text("status = 'ACTIVE'"),
        ),
        {"schema": "core"},
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    company_hsn_sac_code_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    tax_rate_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[TaxReferenceStatus] = mapped_column(
        Enum(
            TaxReferenceStatus,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=20,
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class TaxTreatment(Base):
    __tablename__ = "tax_treatments"
    __table_args__ = (
        CheckConstraint(
            "btrim(code) <> ''",
            name="ck_tax_treatments_code_not_blank",
        ),
        CheckConstraint(
            "btrim(name) <> ''",
            name="ck_tax_treatments_name_not_blank",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_tax_treatments_status",
        ),
        ForeignKeyConstraint(
            ["tax_type_id"],
            ["core.tax_types.id"],
            name="fk_tax_treatments_tax_type_id_tax_types",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["country_code"],
            ["core.countries.code"],
            name="fk_tax_treatments_country_code_countries",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_tax_treatments"),
        UniqueConstraint(
            "tax_type_id",
            "country_code",
            "code",
            name="uq_tax_treatments_tax_type_country_code",
        ),
        {"schema": "core"},
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    tax_type_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    status: Mapped[TaxReferenceStatus] = mapped_column(
        Enum(
            TaxReferenceStatus,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=20,
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
