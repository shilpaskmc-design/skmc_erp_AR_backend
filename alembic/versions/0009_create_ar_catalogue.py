"""Create the Company-owned goods and services catalogue.

Revision ID: 0009_catalogue
Revises: 0008_tax_reference
Create Date: 2026-09-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_catalogue"
down_revision: str | None = "0008_tax_reference"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AR_SCHEMA = "ar"


def _id_column() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )


def upgrade() -> None:
    op.execute("CREATE SCHEMA ar")

    op.create_table(
        "service_categories",
        _id_column(),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "btrim(name) <> ''", name="ck_service_categories_name_not_blank"
        ),
        sa.CheckConstraint(
            "code IS NULL OR btrim(code) <> ''",
            name="ck_service_categories_code_not_blank",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_service_categories_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_service_categories_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_service_categories"),
        sa.UniqueConstraint(
            "company_id", "name", name="uq_service_categories_company_id_name"
        ),
        sa.UniqueConstraint(
            "company_id", "id", name="uq_service_categories_company_id_id"
        ),
        schema=AR_SCHEMA,
    )
    op.create_index(
        "uq_service_categories_company_id_code",
        "service_categories",
        ["company_id", "code"],
        unique=True,
        schema=AR_SCHEMA,
        postgresql_where=sa.text("code IS NOT NULL"),
    )

    op.create_table(
        "product_categories",
        _id_column(),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "btrim(name) <> ''", name="ck_product_categories_name_not_blank"
        ),
        sa.CheckConstraint(
            "code IS NULL OR btrim(code) <> ''",
            name="ck_product_categories_code_not_blank",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_product_categories_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_product_categories_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_product_categories"),
        sa.UniqueConstraint(
            "company_id", "name", name="uq_product_categories_company_id_name"
        ),
        sa.UniqueConstraint(
            "company_id", "id", name="uq_product_categories_company_id_id"
        ),
        schema=AR_SCHEMA,
    )
    op.create_index(
        "uq_product_categories_company_id_code",
        "product_categories",
        ["company_id", "code"],
        unique=True,
        schema=AR_SCHEMA,
        postgresql_where=sa.text("code IS NOT NULL"),
    )

    op.create_table(
        "service_types",
        _id_column(),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "service_category_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("uom", sa.String(length=30), nullable=True),
        sa.Column(
            "company_hsn_sac_code_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "selected_tax_rate_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "tax_treatment_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "tcs_check_required",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "btrim(name) <> ''", name="ck_service_types_name_not_blank"
        ),
        sa.CheckConstraint(
            "code IS NULL OR btrim(code) <> ''",
            name="ck_service_types_code_not_blank",
        ),
        sa.CheckConstraint(
            "description IS NULL OR btrim(description) <> ''",
            name="ck_service_types_description_not_blank",
        ),
        sa.CheckConstraint(
            "uom IS NULL OR btrim(uom) <> ''",
            name="ck_service_types_uom_not_blank",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_service_types_status",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_service_types_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "service_category_id"],
            ["ar.service_categories.company_id", "ar.service_categories.id"],
            name="fk_service_types_company_service_category",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "company_hsn_sac_code_id"],
            [
                "core.company_hsn_sac_codes.company_id",
                "core.company_hsn_sac_codes.id",
            ],
            name="fk_service_types_company_hsn_sac_code",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["selected_tax_rate_id"],
            ["core.tax_rates.id"],
            name="fk_service_types_selected_tax_rate",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["tax_treatment_id"],
            ["core.tax_treatments.id"],
            name="fk_service_types_tax_treatment",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_service_types"),
        schema=AR_SCHEMA,
    )
    op.create_index(
        "uq_service_types_company_id_code",
        "service_types",
        ["company_id", "code"],
        unique=True,
        schema=AR_SCHEMA,
        postgresql_where=sa.text("code IS NOT NULL"),
    )

    op.create_table(
        "products",
        _id_column(),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "product_category_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("btrim(name) <> ''", name="ck_products_name_not_blank"),
        sa.CheckConstraint(
            "code IS NULL OR btrim(code) <> ''",
            name="ck_products_code_not_blank",
        ),
        sa.CheckConstraint(
            "description IS NULL OR btrim(description) <> ''",
            name="ck_products_description_not_blank",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')", name="ck_products_status"
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_products_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "product_category_id"],
            ["ar.product_categories.company_id", "ar.product_categories.id"],
            name="fk_products_company_product_category",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_products"),
        sa.UniqueConstraint("company_id", "id", name="uq_products_company_id_id"),
        schema=AR_SCHEMA,
    )
    op.create_index(
        "uq_products_company_id_code",
        "products",
        ["company_id", "code"],
        unique=True,
        schema=AR_SCHEMA,
        postgresql_where=sa.text("code IS NOT NULL"),
    )

    op.create_table(
        "skus",
        _id_column(),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku_code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("uom", sa.String(length=30), nullable=False),
        sa.Column(
            "company_hsn_sac_code_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "selected_tax_rate_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "tax_treatment_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "tcs_check_required",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "btrim(sku_code) <> ''", name="ck_skus_sku_code_not_blank"
        ),
        sa.CheckConstraint("btrim(name) <> ''", name="ck_skus_name_not_blank"),
        sa.CheckConstraint(
            "description IS NULL OR btrim(description) <> ''",
            name="ck_skus_description_not_blank",
        ),
        sa.CheckConstraint("btrim(uom) <> ''", name="ck_skus_uom_not_blank"),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')", name="ck_skus_status"
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_skus_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "product_id"],
            ["ar.products.company_id", "ar.products.id"],
            name="fk_skus_company_product",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "company_hsn_sac_code_id"],
            [
                "core.company_hsn_sac_codes.company_id",
                "core.company_hsn_sac_codes.id",
            ],
            name="fk_skus_company_hsn_sac_code",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["selected_tax_rate_id"],
            ["core.tax_rates.id"],
            name="fk_skus_selected_tax_rate",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["tax_treatment_id"],
            ["core.tax_treatments.id"],
            name="fk_skus_tax_treatment",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_skus"),
        sa.UniqueConstraint(
            "company_id", "sku_code", name="uq_skus_company_id_sku_code"
        ),
        schema=AR_SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("skus", schema=AR_SCHEMA)
    op.drop_index(
        "uq_products_company_id_code", table_name="products", schema=AR_SCHEMA
    )
    op.drop_table("products", schema=AR_SCHEMA)
    op.drop_index(
        "uq_service_types_company_id_code",
        table_name="service_types",
        schema=AR_SCHEMA,
    )
    op.drop_table("service_types", schema=AR_SCHEMA)
    op.drop_index(
        "uq_product_categories_company_id_code",
        table_name="product_categories",
        schema=AR_SCHEMA,
    )
    op.drop_table("product_categories", schema=AR_SCHEMA)
    op.drop_index(
        "uq_service_categories_company_id_code",
        table_name="service_categories",
        schema=AR_SCHEMA,
    )
    op.drop_table("service_categories", schema=AR_SCHEMA)
    op.execute("DROP SCHEMA ar")
