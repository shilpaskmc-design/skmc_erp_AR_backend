"""Revenue GL mapping enhancement and deterministic resolution.

Revision ID: 0028_revenue_gl_mapping_enhancement
Revises: 0027_company_document_presentation
Create Date: 2026-09-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0028_revenue_gl_mapping_enhancement"
down_revision: str | None = "0027_company_document_presentation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AR_SCHEMA = "ar"
CORE_SCHEMA = "core"


def upgrade() -> None:
    # 1. Unique constraints on referenced targets if not present
    op.create_unique_constraint(
        "uq_service_types_company_id_id",
        "service_types",
        ["company_id", "id"],
        schema=AR_SCHEMA,
    )
    op.create_unique_constraint(
        "uq_skus_company_id_id",
        "skus",
        ["company_id", "id"],
        schema=AR_SCHEMA,
    )
    op.create_unique_constraint(
        "uq_company_locations_company_id_id",
        "company_locations",
        ["company_id", "id"],
        schema=CORE_SCHEMA,
    )

    # 2. Retire legacy 0020 development configuration rows that lack item specification
    op.execute(sa.text("DELETE FROM ar.revenue_gl_mappings"))

    # 3. Drop old exclusion constraints and old HSN/SAC FK
    op.execute(
        sa.text(
            "ALTER TABLE ar.revenue_gl_mappings "
            "DROP CONSTRAINT ex_revenue_gl_mappings_specific_period_overlap"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE ar.revenue_gl_mappings "
            "DROP CONSTRAINT ex_revenue_gl_mappings_general_period_overlap"
        )
    )
    op.drop_constraint(
        "fk_revenue_gl_mappings_company_hsn_sac_code",
        "revenue_gl_mappings",
        type_="foreignkey",
        schema=AR_SCHEMA,
    )

    # 4. Drop obsolete column company_hsn_sac_code_id
    op.drop_column("revenue_gl_mappings", "company_hsn_sac_code_id", schema=AR_SCHEMA)

    # 5. Make supply_type_code optional (nullable)
    op.alter_column(
        "revenue_gl_mappings",
        "supply_type_code",
        existing_type=sa.String(length=30),
        nullable=True,
        schema=AR_SCHEMA,
    )

    # 6. Add new item and location columns
    op.add_column(
        "revenue_gl_mappings",
        sa.Column(
            "service_type_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        schema=AR_SCHEMA,
    )
    op.add_column(
        "revenue_gl_mappings",
        sa.Column("sku_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema=AR_SCHEMA,
    )
    op.add_column(
        "revenue_gl_mappings",
        sa.Column(
            "company_location_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        schema=AR_SCHEMA,
    )

    # 7. Add CHECK constraint enforcing exactly one of service_type_id or sku_id
    op.create_check_constraint(
        "ck_revenue_gl_mappings_exactly_one_item",
        "revenue_gl_mappings",
        "(service_type_id IS NOT NULL AND sku_id IS NULL) OR (service_type_id IS NULL AND sku_id IS NOT NULL)",
        schema=AR_SCHEMA,
    )

    # 8. Foreign keys ensuring same-Company ownership
    op.create_foreign_key(
        "fk_revenue_gl_mappings_company_service_type",
        "revenue_gl_mappings",
        "service_types",
        ["company_id", "service_type_id"],
        ["company_id", "id"],
        source_schema=AR_SCHEMA,
        referent_schema=AR_SCHEMA,
        ondelete="NO ACTION",
    )
    op.create_foreign_key(
        "fk_revenue_gl_mappings_company_sku",
        "revenue_gl_mappings",
        "skus",
        ["company_id", "sku_id"],
        ["company_id", "id"],
        source_schema=AR_SCHEMA,
        referent_schema=AR_SCHEMA,
        ondelete="NO ACTION",
    )
    op.create_foreign_key(
        "fk_revenue_gl_mappings_company_location",
        "revenue_gl_mappings",
        "company_locations",
        ["company_id", "company_location_id"],
        ["company_id", "id"],
        source_schema=AR_SCHEMA,
        referent_schema=CORE_SCHEMA,
        ondelete="NO ACTION",
    )

    # 9. Overlap protection for active date ranges with exact same criteria tuple
    op.execute(
        sa.text(
            """
            ALTER TABLE ar.revenue_gl_mappings
            ADD CONSTRAINT ex_revenue_gl_mappings_service_type_overlap
            EXCLUDE USING gist (
                company_id WITH =,
                service_type_id WITH =,
                COALESCE(supply_type_code, '__NULL__') WITH =,
                COALESCE(
                    company_location_id,
                    '00000000-0000-0000-0000-000000000000'::uuid
                ) WITH =,
                daterange(valid_from, valid_to, '[]') WITH &&
            )
            WHERE (service_type_id IS NOT NULL AND status = 'ACTIVE')
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE ar.revenue_gl_mappings
            ADD CONSTRAINT ex_revenue_gl_mappings_sku_overlap
            EXCLUDE USING gist (
                company_id WITH =,
                sku_id WITH =,
                COALESCE(supply_type_code, '__NULL__') WITH =,
                COALESCE(
                    company_location_id,
                    '00000000-0000-0000-0000-000000000000'::uuid
                ) WITH =,
                daterange(valid_from, valid_to, '[]') WITH &&
            )
            WHERE (sku_id IS NOT NULL AND status = 'ACTIVE')
            """
        )
    )


def downgrade() -> None:
    # G3 item/location mappings cannot be represented by the 0027 contract.
    op.execute(sa.text("DELETE FROM ar.revenue_gl_mappings"))

    op.execute(
        sa.text(
            "ALTER TABLE ar.revenue_gl_mappings "
            "DROP CONSTRAINT ex_revenue_gl_mappings_sku_overlap"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE ar.revenue_gl_mappings "
            "DROP CONSTRAINT ex_revenue_gl_mappings_service_type_overlap"
        )
    )
    op.drop_constraint(
        "fk_revenue_gl_mappings_company_location",
        "revenue_gl_mappings",
        type_="foreignkey",
        schema=AR_SCHEMA,
    )
    op.drop_constraint(
        "fk_revenue_gl_mappings_company_sku",
        "revenue_gl_mappings",
        type_="foreignkey",
        schema=AR_SCHEMA,
    )
    op.drop_constraint(
        "fk_revenue_gl_mappings_company_service_type",
        "revenue_gl_mappings",
        type_="foreignkey",
        schema=AR_SCHEMA,
    )
    op.drop_constraint(
        "ck_revenue_gl_mappings_exactly_one_item",
        "revenue_gl_mappings",
        type_="check",
        schema=AR_SCHEMA,
    )
    op.drop_column("revenue_gl_mappings", "company_location_id", schema=AR_SCHEMA)
    op.drop_column("revenue_gl_mappings", "sku_id", schema=AR_SCHEMA)
    op.drop_column("revenue_gl_mappings", "service_type_id", schema=AR_SCHEMA)

    op.execute(
        sa.text(
            "UPDATE ar.revenue_gl_mappings SET supply_type_code = 'B2B' WHERE supply_type_code IS NULL"
        )
    )
    op.alter_column(
        "revenue_gl_mappings",
        "supply_type_code",
        existing_type=sa.String(length=30),
        nullable=False,
        schema=AR_SCHEMA,
    )
    op.add_column(
        "revenue_gl_mappings",
        sa.Column(
            "company_hsn_sac_code_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        schema=AR_SCHEMA,
    )
    op.create_foreign_key(
        "fk_revenue_gl_mappings_company_hsn_sac_code",
        "revenue_gl_mappings",
        "company_hsn_sac_codes",
        ["company_id", "company_hsn_sac_code_id"],
        ["company_id", "id"],
        source_schema=AR_SCHEMA,
        referent_schema=CORE_SCHEMA,
        ondelete="NO ACTION",
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE ar.revenue_gl_mappings
            ADD CONSTRAINT ex_revenue_gl_mappings_specific_period_overlap
            EXCLUDE USING gist (
                company_id WITH =,
                supply_type_code WITH =,
                company_hsn_sac_code_id WITH =,
                daterange(valid_from, valid_to, '[]') WITH &&
            )
            WHERE (company_hsn_sac_code_id IS NOT NULL)
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE ar.revenue_gl_mappings
            ADD CONSTRAINT ex_revenue_gl_mappings_general_period_overlap
            EXCLUDE USING gist (
                company_id WITH =,
                supply_type_code WITH =,
                daterange(valid_from, valid_to, '[]') WITH &&
            )
            WHERE (company_hsn_sac_code_id IS NULL)
            """
        )
    )

    op.drop_constraint(
        "uq_company_locations_company_id_id",
        "company_locations",
        type_="unique",
        schema=CORE_SCHEMA,
    )
    op.drop_constraint(
        "uq_skus_company_id_id",
        "skus",
        type_="unique",
        schema=AR_SCHEMA,
    )
    op.drop_constraint(
        "uq_service_types_company_id_id",
        "service_types",
        type_="unique",
        schema=AR_SCHEMA,
    )
