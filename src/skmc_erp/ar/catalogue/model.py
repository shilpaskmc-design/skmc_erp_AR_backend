from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Index,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from skmc_erp.model_base import Base


class CatalogueStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class ServiceCategory(Base):
    __tablename__ = "service_categories"
    __table_args__ = (
        CheckConstraint(
            "btrim(name) <> ''", name="ck_service_categories_name_not_blank"
        ),
        CheckConstraint(
            "code IS NULL OR btrim(code) <> ''",
            name="ck_service_categories_code_not_blank",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_service_categories_status",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_service_categories_company_id_companies",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_service_categories"),
        UniqueConstraint(
            "company_id", "name", name="uq_service_categories_company_id_name"
        ),
        UniqueConstraint(
            "company_id", "id", name="uq_service_categories_company_id_id"
        ),
        Index(
            "uq_service_categories_company_id_code",
            "company_id",
            "code",
            unique=True,
            postgresql_where=text("code IS NOT NULL"),
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
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[CatalogueStatus] = mapped_column(
        Enum(
            CatalogueStatus,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=20,
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class ServiceType(Base):
    __tablename__ = "service_types"
    __table_args__ = (
        CheckConstraint(
            "btrim(name) <> ''", name="ck_service_types_name_not_blank"
        ),
        CheckConstraint(
            "code IS NULL OR btrim(code) <> ''",
            name="ck_service_types_code_not_blank",
        ),
        CheckConstraint(
            "description IS NULL OR btrim(description) <> ''",
            name="ck_service_types_description_not_blank",
        ),
        CheckConstraint(
            "uom IS NULL OR btrim(uom) <> ''",
            name="ck_service_types_uom_not_blank",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_service_types_status",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_service_types_company_id_companies",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "service_category_id"],
            ["ar.service_categories.company_id", "ar.service_categories.id"],
            name="fk_service_types_company_service_category",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "business_segment_id"],
            [
                "core.cost_center_business_segments.company_id",
                "core.cost_center_business_segments.id",
            ],
            name="fk_service_types_company_business_segment",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "company_hsn_sac_code_id"],
            [
                "core.company_hsn_sac_codes.company_id",
                "core.company_hsn_sac_codes.id",
            ],
            name="fk_service_types_company_hsn_sac_code",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["selected_tax_rate_id"],
            ["core.tax_rates.id"],
            name="fk_service_types_selected_tax_rate",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["base_tax_treatment_id"],
            ["core.tax_treatments.id"],
            name="fk_service_types_base_tax_treatment",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["uom"],
            ["core.uoms.code"],
            name="fk_service_types_uom_uoms",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_service_types"),
        Index(
            "uq_service_types_company_id_code",
            "company_id",
            "code",
            unique=True,
            postgresql_where=text("code IS NOT NULL"),
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
    service_category_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    business_segment_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    uom: Mapped[str | None] = mapped_column(String(30), nullable=True)
    company_hsn_sac_code_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    selected_tax_rate_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    base_tax_treatment_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    tcs_check_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    status: Mapped[CatalogueStatus] = mapped_column(
        Enum(
            CatalogueStatus,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=20,
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class ProductCategory(Base):
    __tablename__ = "product_categories"
    __table_args__ = (
        CheckConstraint(
            "btrim(name) <> ''", name="ck_product_categories_name_not_blank"
        ),
        CheckConstraint(
            "code IS NULL OR btrim(code) <> ''",
            name="ck_product_categories_code_not_blank",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_product_categories_status",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_product_categories_company_id_companies",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_product_categories"),
        UniqueConstraint(
            "company_id", "name", name="uq_product_categories_company_id_name"
        ),
        UniqueConstraint(
            "company_id", "id", name="uq_product_categories_company_id_id"
        ),
        Index(
            "uq_product_categories_company_id_code",
            "company_id",
            "code",
            unique=True,
            postgresql_where=text("code IS NOT NULL"),
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
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[CatalogueStatus] = mapped_column(
        Enum(
            CatalogueStatus,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=20,
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("btrim(name) <> ''", name="ck_products_name_not_blank"),
        CheckConstraint(
            "code IS NULL OR btrim(code) <> ''",
            name="ck_products_code_not_blank",
        ),
        CheckConstraint(
            "description IS NULL OR btrim(description) <> ''",
            name="ck_products_description_not_blank",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')", name="ck_products_status"
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_products_company_id_companies",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "product_category_id"],
            ["ar.product_categories.company_id", "ar.product_categories.id"],
            name="fk_products_company_product_category",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_products"),
        UniqueConstraint("company_id", "id", name="uq_products_company_id_id"),
        Index(
            "uq_products_company_id_code",
            "company_id",
            "code",
            unique=True,
            postgresql_where=text("code IS NOT NULL"),
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
    product_category_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[CatalogueStatus] = mapped_column(
        Enum(
            CatalogueStatus,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=20,
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class Sku(Base):
    __tablename__ = "skus"
    __table_args__ = (
        CheckConstraint("btrim(sku_code) <> ''", name="ck_skus_sku_code_not_blank"),
        CheckConstraint("btrim(name) <> ''", name="ck_skus_name_not_blank"),
        CheckConstraint(
            "description IS NULL OR btrim(description) <> ''",
            name="ck_skus_description_not_blank",
        ),
        CheckConstraint("btrim(uom) <> ''", name="ck_skus_uom_not_blank"),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')", name="ck_skus_status"
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_skus_company_id_companies",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "product_id"],
            ["ar.products.company_id", "ar.products.id"],
            name="fk_skus_company_product",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "business_segment_id"],
            [
                "core.cost_center_business_segments.company_id",
                "core.cost_center_business_segments.id",
            ],
            name="fk_skus_company_business_segment",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "company_hsn_sac_code_id"],
            [
                "core.company_hsn_sac_codes.company_id",
                "core.company_hsn_sac_codes.id",
            ],
            name="fk_skus_company_hsn_sac_code",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["selected_tax_rate_id"],
            ["core.tax_rates.id"],
            name="fk_skus_selected_tax_rate",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["base_tax_treatment_id"],
            ["core.tax_treatments.id"],
            name="fk_skus_base_tax_treatment",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["uom"],
            ["core.uoms.code"],
            name="fk_skus_uom_uoms",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_skus"),
        UniqueConstraint(
            "company_id", "sku_code", name="uq_skus_company_id_sku_code"
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
    product_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    business_segment_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    sku_code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    uom: Mapped[str] = mapped_column(String(30), nullable=False)
    company_hsn_sac_code_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    selected_tax_rate_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    base_tax_treatment_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    tcs_check_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    status: Mapped[CatalogueStatus] = mapped_column(
        Enum(
            CatalogueStatus,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=20,
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
