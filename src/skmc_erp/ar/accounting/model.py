from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from skmc_erp.model_base import Base


class AccountingMappingStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class RevenueGlMapping(Base):
    __tablename__ = "revenue_gl_mappings"
    __table_args__ = (
        CheckConstraint(
            "(service_type_id IS NOT NULL AND sku_id IS NULL) OR (service_type_id IS NULL AND sku_id IS NOT NULL)",
            name="ck_revenue_gl_mappings_exactly_one_item",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_revenue_gl_mappings_date_order",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_revenue_gl_mappings_status",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_revenue_gl_mappings_company_id_companies",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "service_type_id"],
            ["ar.service_types.company_id", "ar.service_types.id"],
            name="fk_revenue_gl_mappings_company_service_type",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "sku_id"],
            ["ar.skus.company_id", "ar.skus.id"],
            name="fk_revenue_gl_mappings_company_sku",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "company_location_id"],
            ["core.company_locations.company_id", "core.company_locations.id"],
            name="fk_revenue_gl_mappings_company_location",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "gl_account_id"],
            ["core.gl_accounts.company_id", "core.gl_accounts.id"],
            name="fk_revenue_gl_mappings_company_gl_account",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_revenue_gl_mappings"),
        ExcludeConstraint(
            ("company_id", "="),
            ("service_type_id", "="),
            (text("COALESCE(supply_type_code, '__NULL__')"), "="),
            (
                text(
                    "COALESCE(company_location_id, '00000000-0000-0000-0000-000000000000'::uuid)"
                ),
                "=",
            ),
            (text("daterange(valid_from, valid_to, '[]')"), "&&"),
            name="ex_revenue_gl_mappings_service_type_overlap",
            using="gist",
            where=text("service_type_id IS NOT NULL AND status = 'ACTIVE'"),
        ),
        ExcludeConstraint(
            ("company_id", "="),
            ("sku_id", "="),
            (text("COALESCE(supply_type_code, '__NULL__')"), "="),
            (
                text(
                    "COALESCE(company_location_id, '00000000-0000-0000-0000-000000000000'::uuid)"
                ),
                "=",
            ),
            (text("daterange(valid_from, valid_to, '[]')"), "&&"),
            name="ex_revenue_gl_mappings_sku_overlap",
            using="gist",
            where=text("sku_id IS NOT NULL AND status = 'ACTIVE'"),
        ),
        {"schema": "ar"},
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    company_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    service_type_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    sku_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    supply_type_code: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )
    company_location_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    gl_account_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[AccountingMappingStatus] = mapped_column(
        Enum(
            AccountingMappingStatus,
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


class TaxGlAccountMapping(Base):
    __tablename__ = "tax_gl_account_mappings"
    __table_args__ = (
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_tax_gl_account_mappings_date_order",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_tax_gl_account_mappings_status",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_tax_gl_account_mappings_company_id_companies",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["tax_statutory_code_id"],
            ["core.tax_statutory_codes.id"],
            name="fk_tax_gl_account_mappings_statutory_code",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "gl_account_id"],
            ["core.gl_accounts.company_id", "core.gl_accounts.id"],
            name="fk_tax_gl_account_mappings_company_gl_account",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_tax_gl_account_mappings"),
        ExcludeConstraint(
            ("company_id", "="),
            ("tax_statutory_code_id", "="),
            (text("daterange(valid_from, valid_to, '[]')"), "&&"),
            name="ex_tax_gl_account_mappings_period_overlap",
            using="gist",
        ),
        {"schema": "ar"},
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    company_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    tax_statutory_code_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    gl_account_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[AccountingMappingStatus] = mapped_column(
        Enum(
            AccountingMappingStatus,
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
