"""Store catalogue Base GST Nature and make selected GST rates conditional.

Revision ID: 0033_catalogue_base_gst_nature
Revises: 0032_company_location_codes
Create Date: 2026-09-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0033_catalogue_base_gst_nature"
down_revision: str | None = "0032_company_location_codes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AR_SCHEMA = "ar"

_APPROVED_BASE_GST_NATURES = "'TAXABLE', 'NIL_RATED', 'EXEMPT', 'NON_GST'"


def _invalid_catalogue_rows(table_name: str) -> list[tuple[object, ...]]:
    connection = op.get_bind()
    return list(
        connection.execute(
            sa.text(
                f"""
                SELECT item.id, treatment.code, rate.rate_percent
                FROM ar.{table_name} AS item
                JOIN core.tax_treatments AS treatment
                  ON treatment.id = item.tax_treatment_id
                JOIN core.tax_types AS treatment_type
                  ON treatment_type.id = treatment.tax_type_id
                LEFT JOIN core.tax_rates AS rate
                  ON rate.id = item.selected_tax_rate_id
                LEFT JOIN core.tax_types AS rate_type
                  ON rate_type.id = rate.tax_type_id
                WHERE treatment.code NOT IN ({_APPROVED_BASE_GST_NATURES})
                   OR treatment.status <> 'ACTIVE'
                   OR treatment_type.status <> 'ACTIVE'
                   OR treatment_type.code <> 'GST'
                   OR treatment_type.country_code <> treatment.country_code
                   OR (
                        treatment.code IN ('TAXABLE', 'NIL_RATED')
                        AND (
                            item.selected_tax_rate_id IS NULL
                            OR rate.id IS NULL
                            OR rate.status <> 'ACTIVE'
                            OR rate_type.status <> 'ACTIVE'
                            OR rate_type.code <> 'GST'
                            OR rate_type.country_code <> rate.country_code
                            OR treatment.tax_type_id <> rate.tax_type_id
                            OR treatment.country_code <> rate.country_code
                            OR NOT EXISTS (
                                SELECT 1
                                FROM core.company_hsn_sac_tax_rates AS mapping
                                WHERE mapping.company_hsn_sac_code_id =
                                      item.company_hsn_sac_code_id
                                  AND mapping.tax_rate_id = item.selected_tax_rate_id
                                  AND mapping.status = 'ACTIVE'
                            )
                        )
                   )
                   OR (
                        treatment.code = 'NIL_RATED'
                        AND rate.rate_percent <> 0
                   )
                   OR (
                        treatment.code IN ('EXEMPT', 'NON_GST')
                        AND item.selected_tax_rate_id IS NOT NULL
                   )
                ORDER BY item.id
                LIMIT 20
                """
            )
        ).fetchall()
    )


def _validate_upgrade_data() -> None:
    for table_name in ("service_types", "skus"):
        invalid_rows = _invalid_catalogue_rows(table_name)
        if invalid_rows:
            raise RuntimeError(
                f"Cannot migrate ar.{table_name}: existing rows violate the "
                "approved Base GST Nature and selected-rate rules; "
                f"sample row ids: {[str(row[0]) for row in invalid_rows]}"
            )


def upgrade() -> None:
    _validate_upgrade_data()

    op.drop_constraint(
        "fk_service_types_tax_treatment",
        "service_types",
        schema=AR_SCHEMA,
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_skus_tax_treatment",
        "skus",
        schema=AR_SCHEMA,
        type_="foreignkey",
    )

    op.alter_column(
        "service_types",
        "tax_treatment_id",
        new_column_name="base_tax_treatment_id",
        existing_type=sa.Uuid(),
        existing_nullable=False,
        schema=AR_SCHEMA,
    )
    op.alter_column(
        "skus",
        "tax_treatment_id",
        new_column_name="base_tax_treatment_id",
        existing_type=sa.Uuid(),
        existing_nullable=False,
        schema=AR_SCHEMA,
    )
    op.alter_column(
        "service_types",
        "selected_tax_rate_id",
        existing_type=sa.Uuid(),
        nullable=True,
        schema=AR_SCHEMA,
    )
    op.alter_column(
        "skus",
        "selected_tax_rate_id",
        existing_type=sa.Uuid(),
        nullable=True,
        schema=AR_SCHEMA,
    )

    op.create_foreign_key(
        "fk_service_types_base_tax_treatment",
        "service_types",
        "tax_treatments",
        ["base_tax_treatment_id"],
        ["id"],
        source_schema=AR_SCHEMA,
        referent_schema="core",
        ondelete="NO ACTION",
    )
    op.create_foreign_key(
        "fk_skus_base_tax_treatment",
        "skus",
        "tax_treatments",
        ["base_tax_treatment_id"],
        ["id"],
        source_schema=AR_SCHEMA,
        referent_schema="core",
        ondelete="NO ACTION",
    )


def downgrade() -> None:
    connection = op.get_bind()
    for table_name in ("service_types", "skus"):
        null_ids = connection.execute(
            sa.text(
                f"""
                SELECT id
                FROM ar.{table_name}
                WHERE selected_tax_rate_id IS NULL
                ORDER BY id
                LIMIT 20
                """
            )
        ).scalars().all()
        if null_ids:
            raise RuntimeError(
                f"Cannot downgrade ar.{table_name}: selected_tax_rate_id contains "
                "NULL values and the previous schema requires NOT NULL; "
                f"sample row ids: {[str(row_id) for row_id in null_ids]}"
            )

    op.drop_constraint(
        "fk_service_types_base_tax_treatment",
        "service_types",
        schema=AR_SCHEMA,
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_skus_base_tax_treatment",
        "skus",
        schema=AR_SCHEMA,
        type_="foreignkey",
    )

    op.alter_column(
        "service_types",
        "base_tax_treatment_id",
        new_column_name="tax_treatment_id",
        existing_type=sa.Uuid(),
        existing_nullable=False,
        schema=AR_SCHEMA,
    )
    op.alter_column(
        "skus",
        "base_tax_treatment_id",
        new_column_name="tax_treatment_id",
        existing_type=sa.Uuid(),
        existing_nullable=False,
        schema=AR_SCHEMA,
    )
    op.alter_column(
        "service_types",
        "selected_tax_rate_id",
        existing_type=sa.Uuid(),
        nullable=False,
        schema=AR_SCHEMA,
    )
    op.alter_column(
        "skus",
        "selected_tax_rate_id",
        existing_type=sa.Uuid(),
        nullable=False,
        schema=AR_SCHEMA,
    )

    op.create_foreign_key(
        "fk_service_types_tax_treatment",
        "service_types",
        "tax_treatments",
        ["tax_treatment_id"],
        ["id"],
        source_schema=AR_SCHEMA,
        referent_schema="core",
        ondelete="NO ACTION",
    )
    op.create_foreign_key(
        "fk_skus_tax_treatment",
        "skus",
        "tax_treatments",
        ["tax_treatment_id"],
        ["id"],
        source_schema=AR_SCHEMA,
        referent_schema="core",
        ondelete="NO ACTION",
    )
