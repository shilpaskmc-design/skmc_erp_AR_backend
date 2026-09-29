"""UOM master and Bank Account validation hardening.

Revision ID: 0031_uom_and_bank_account_hardening
Revises: 0030_company_legal_name_history
Create Date: 2026-09-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031_uom_and_bank_account_hardening"
down_revision: str | None = "0030_company_legal_name_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CORE_SCHEMA = "core"
AR_SCHEMA = "ar"


def upgrade() -> None:
    # 1. Create core.uoms table
    op.create_table(
        "uoms",
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=True),
        sa.Column("uqc_code", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="ACTIVE", nullable=False),
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
        sa.CheckConstraint("code ~ '^[A-Z0-9_]{1,20}$'", name="ck_uoms_code_format"),
        sa.CheckConstraint("btrim(name) <> ''", name="ck_uoms_name_not_blank"),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_uoms_status"),
        sa.PrimaryKeyConstraint("code", name="pk_uoms"),
        schema=CORE_SCHEMA,
    )

    # 2. Seed core.uoms table (Controlled vocabulary only, SAC is excluded)
    uom_table = sa.table(
        "uoms",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("symbol", sa.String),
        sa.column("uqc_code", sa.String),
        sa.column("status", sa.String),
        schema=CORE_SCHEMA,
    )
    op.bulk_insert(
        uom_table,
        [
            {"code": "NOS", "name": "Numbers", "symbol": "nos", "uqc_code": "NOS", "status": "ACTIVE"},
            {"code": "EA", "name": "Each", "symbol": "ea", "uqc_code": "NOS", "status": "ACTIVE"},
            {"code": "KGS", "name": "Kilograms", "symbol": "kg", "uqc_code": "KGS", "status": "ACTIVE"},
            {"code": "MTR", "name": "Meters", "symbol": "m", "uqc_code": "MTR", "status": "ACTIVE"},
            {"code": "BOX", "name": "Boxes", "symbol": "box", "uqc_code": "BOX", "status": "ACTIVE"},
            {"code": "SET", "name": "Sets", "symbol": "set", "uqc_code": "SET", "status": "ACTIVE"},
            {"code": "PCS", "name": "Pieces", "symbol": "pcs", "uqc_code": "PCS", "status": "ACTIVE"},
            {"code": "LTR", "name": "Liters", "symbol": "l", "uqc_code": "LTR", "status": "ACTIVE"},
            {"code": "SQM", "name": "Square Meters", "symbol": "sqm", "uqc_code": "SQM", "status": "ACTIVE"},
            {"code": "CBM", "name": "Cubic Meters", "symbol": "cbm", "uqc_code": "CBM", "status": "ACTIVE"},
            {"code": "TON", "name": "Metric Tonnes", "symbol": "ton", "uqc_code": "TON", "status": "ACTIVE"},
            {"code": "HRS", "name": "Hours", "symbol": "hr", "uqc_code": None, "status": "ACTIVE"},
            {"code": "HOUR", "name": "Hour", "symbol": "hr", "uqc_code": "HRS", "status": "ACTIVE"},
            {"code": "UNIT", "name": "Unit", "symbol": "unit", "uqc_code": "UNT", "status": "ACTIVE"},
            {"code": "DAY", "name": "Days", "symbol": "day", "uqc_code": None, "status": "ACTIVE"},
            {"code": "MTH", "name": "Months", "symbol": "mth", "uqc_code": None, "status": "ACTIVE"},
            {"code": "JOB", "name": "Job", "symbol": "job", "uqc_code": None, "status": "ACTIVE"},
        ],
    )

    # 3. Data migration for service_types and skus
    op.execute(
        f"UPDATE {AR_SCHEMA}.service_types SET uom = UPPER(TRIM(uom)) WHERE uom IS NOT NULL"
    )
    op.execute(
        f"UPDATE {AR_SCHEMA}.skus SET uom = UPPER(TRIM(uom)) WHERE uom IS NOT NULL"
    )

    # Validate that all existing UOM values match core.uoms
    conn = op.get_bind()
    invalid_st = conn.execute(
        sa.text(
            f"SELECT DISTINCT uom FROM {AR_SCHEMA}.service_types WHERE uom IS NOT NULL AND uom NOT IN (SELECT code FROM {CORE_SCHEMA}.uoms)"
        )
    ).fetchall()
    if invalid_st:
        raise RuntimeError(
            f"Cannot migrate ar.service_types: invalid UOM values found: {[r[0] for r in invalid_st]}"
        )

    invalid_sku = conn.execute(
        sa.text(
            f"SELECT DISTINCT uom FROM {AR_SCHEMA}.skus WHERE uom IS NOT NULL AND uom NOT IN (SELECT code FROM {CORE_SCHEMA}.uoms)"
        )
    ).fetchall()
    if invalid_sku:
        raise RuntimeError(
            f"Cannot migrate ar.skus: invalid UOM values found: {[r[0] for r in invalid_sku]}"
        )

    # 4. Add UOM Foreign Keys
    op.create_foreign_key(
        "fk_service_types_uom_uoms",
        "service_types",
        "uoms",
        ["uom"],
        ["code"],
        source_schema=AR_SCHEMA,
        referent_schema=CORE_SCHEMA,
        ondelete="NO ACTION",
    )
    op.create_foreign_key(
        "fk_skus_uom_uoms",
        "skus",
        "uoms",
        ["uom"],
        ["code"],
        source_schema=AR_SCHEMA,
        referent_schema=CORE_SCHEMA,
        ondelete="NO ACTION",
    )

    # 5. Bank Account Hardening
    op.add_column(
        "company_bank_accounts",
        sa.Column("bank_country_code", sa.String(length=2), nullable=True),
        schema=CORE_SCHEMA,
    )
    op.create_foreign_key(
        "fk_company_bank_accounts_bank_country_code_countries",
        "company_bank_accounts",
        "countries",
        ["bank_country_code"],
        ["code"],
        source_schema=CORE_SCHEMA,
        referent_schema=CORE_SCHEMA,
        ondelete="NO ACTION",
    )

    # Normalize existing account_type and validate that no unknown types exist
    op.execute(
        f"UPDATE {CORE_SCHEMA}.company_bank_accounts SET account_type = UPPER(TRIM(account_type)) WHERE account_type IS NOT NULL"
    )
    invalid_types = conn.execute(
        sa.text(
            f"SELECT DISTINCT account_type FROM {CORE_SCHEMA}.company_bank_accounts WHERE account_type IS NOT NULL AND account_type NOT IN ('CURRENT', 'SAVINGS', 'OVERDRAFT', 'CASH_CREDIT', 'MONEY_MARKET', 'OTHER')"
        )
    ).fetchall()
    if invalid_types:
        raise RuntimeError(
            f"Cannot migrate core.company_bank_accounts: invalid account_type values found: {[r[0] for r in invalid_types]}"
        )

    op.create_check_constraint(
        "ck_company_bank_accounts_account_type",
        "company_bank_accounts",
        "account_type IS NULL OR account_type IN ('CURRENT', 'SAVINGS', 'OVERDRAFT', 'CASH_CREDIT', 'MONEY_MARKET', 'OTHER')",
        schema=CORE_SCHEMA,
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_company_bank_accounts_account_type",
        "company_bank_accounts",
        schema=CORE_SCHEMA,
        type_="check",
    )
    op.drop_constraint(
        "fk_company_bank_accounts_bank_country_code_countries",
        "company_bank_accounts",
        schema=CORE_SCHEMA,
        type_="foreignkey",
    )
    op.drop_column("company_bank_accounts", "bank_country_code", schema=CORE_SCHEMA)

    op.drop_constraint(
        "fk_skus_uom_uoms",
        "skus",
        schema=AR_SCHEMA,
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_service_types_uom_uoms",
        "service_types",
        schema=AR_SCHEMA,
        type_="foreignkey",
    )

    op.drop_table("uoms", schema=CORE_SCHEMA)
