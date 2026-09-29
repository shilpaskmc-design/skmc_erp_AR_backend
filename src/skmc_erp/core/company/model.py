from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Index,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from skmc_erp.model_base import Base


class CompanyBusinessNature(StrEnum):
    SERVICES = "SERVICES"
    GOODS = "GOODS"
    BOTH = "BOTH"


class CompanyStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (
        CheckConstraint(
            "btrim(legal_name) <> ''",
            name="ck_companies_legal_name_not_blank",
        ),
        CheckConstraint(
            "display_name IS NULL OR btrim(display_name) <> ''",
            name="ck_companies_display_name_not_blank",
        ),
        CheckConstraint(
            "company_code ~ '^COM[0-9]{6,}$'",
            name="ck_companies_company_code_format",
        ),
        CheckConstraint(
            "country_code IS NULL OR country_code ~ '^[A-Z]{2}$'",
            name="ck_companies_country_code_format",
        ),
        CheckConstraint(
            "email IS NULL OR btrim(email) <> ''",
            name="ck_companies_email_not_blank",
        ),
        CheckConstraint(
            "phone IS NULL OR btrim(phone) <> ''",
            name="ck_companies_phone_not_blank",
        ),
        CheckConstraint(
            "website IS NULL OR btrim(website) <> ''",
            name="ck_companies_website_not_blank",
        ),
        CheckConstraint(
            "base_timezone IS NULL OR btrim(base_timezone) <> ''",
            name="ck_companies_base_timezone_not_blank",
        ),
        CheckConstraint(
            "business_nature IS NULL OR "
            "business_nature IN ('SERVICES', 'GOODS', 'BOTH')",
            name="ck_companies_business_nature",
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'INACTIVE')",
            name="ck_companies_status",
        ),
        ForeignKeyConstraint(
            ["tenant_id"],
            ["core.tenants.id"],
            name="fk_companies_tenant_id_tenants",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organisation_id"],
            ["core.organisations.tenant_id", "core.organisations.id"],
            name="fk_companies_tenant_organisation",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["entity_type_id"],
            ["core.entity_types.id"],
            name="fk_companies_entity_type_id_entity_types",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["base_currency_code"],
            ["core.currencies.code"],
            name="fk_companies_base_currency_code_currencies",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_companies"),
        UniqueConstraint("company_code", name="uq_companies_company_code"),
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_companies_tenant_id_id",
        ),
        Index(
            "ix_companies_tenant_id_organisation_id",
            "tenant_id",
            "organisation_id",
        ),
        {"schema": "core"},
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )
    organisation_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=True,
    )
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    company_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("core.next_company_code()"),
    )
    entity_type_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=True,
    )
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    website: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    base_timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    base_currency_code: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
    )
    business_nature: Mapped[CompanyBusinessNature | None] = mapped_column(
        Enum(
            CompanyBusinessNature,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=20,
        ),
        nullable=True,
    )
    status: Mapped[CompanyStatus] = mapped_column(
        Enum(
            CompanyStatus,
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


class CompanyLegalNameVersion(Base):
    __tablename__ = "company_legal_name_versions"
    __table_args__ = (
        CheckConstraint(
            "btrim(legal_name) <> ''",
            name="ck_company_legal_name_versions_legal_name_not_blank",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_company_legal_name_versions_date_order",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_legal_name_versions_company_id_companies",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_company_legal_name_versions"),
        ExcludeConstraint(
            ("company_id", "="),
            (text("daterange(valid_from, valid_to, '[]')"), "&&"),
            name="ex_company_legal_name_versions_company_effective_range",
            using="gist",
        ),
        Index(
            "ix_company_legal_name_versions_company_valid_from",
            "company_id",
            "valid_from",
        ),
        Index(
            "uq_company_legal_name_versions_open_company",
            "company_id",
            unique=True,
            postgresql_where=text("valid_to IS NULL"),
        ),
        {"schema": "core"},
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    company_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
