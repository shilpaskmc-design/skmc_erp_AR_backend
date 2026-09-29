"""Add stable Company-scoped Location Codes.

Revision ID: 0032_company_location_codes
Revises: 0031_uom_and_bank_account_hardening
Create Date: 2026-09-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0032_company_location_codes"
down_revision: str | None = "0031_uom_and_bank_account_hardening"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CORE_SCHEMA = "core"


def upgrade() -> None:
    op.add_column(
        "company_locations",
        sa.Column("location_code", sa.String(length=50), nullable=True),
        schema=CORE_SCHEMA,
    )

    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY company_id
                       ORDER BY created_at, id
                   ) AS location_number
            FROM core.company_locations
        )
        UPDATE core.company_locations AS location
        SET location_code = 'LOC-' || lpad(
            ranked.location_number::text,
            GREATEST(4, length(ranked.location_number::text)),
            '0'
        )
        FROM ranked
        WHERE ranked.id = location.id
        """
    )

    op.alter_column(
        "company_locations",
        "location_code",
        existing_type=sa.String(length=50),
        nullable=False,
        schema=CORE_SCHEMA,
    )
    op.create_check_constraint(
        "ck_company_locations_code_format",
        "company_locations",
        "location_code ~ '^[A-Z0-9][A-Z0-9_-]{0,49}$'",
        schema=CORE_SCHEMA,
    )
    op.create_index(
        "uq_company_locations_company_id_location_code",
        "company_locations",
        ["company_id", "location_code"],
        unique=True,
        schema=CORE_SCHEMA,
    )

    op.create_table(
        "company_location_code_counters",
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("next_value", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "next_value >= 1",
            name="ck_company_location_code_counters_next_value",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_location_code_counters_company_id_companies",
            ondelete="NO ACTION",
        ),
        sa.PrimaryKeyConstraint(
            "company_id",
            name="pk_company_location_code_counters",
        ),
        schema=CORE_SCHEMA,
    )
    op.execute(
        """
        INSERT INTO core.company_location_code_counters (company_id, next_value)
        SELECT company_id, count(*) + 1
        FROM core.company_locations
        GROUP BY company_id
        """
    )
    op.execute(
        """
        CREATE FUNCTION core.next_company_location_code(p_company_id uuid)
        RETURNS varchar(50)
        LANGUAGE plpgsql
        VOLATILE
        AS $$
        DECLARE
            allocated bigint;
            candidate varchar(50);
        BEGIN
            LOOP
                INSERT INTO core.company_location_code_counters
                    (company_id, next_value)
                VALUES (p_company_id, 2)
                ON CONFLICT (company_id) DO UPDATE
                SET next_value =
                    core.company_location_code_counters.next_value + 1
                RETURNING next_value - 1 INTO allocated;

                candidate := 'LOC-' || lpad(
                    allocated::text,
                    GREATEST(4, length(allocated::text)),
                    '0'
                );
                IF NOT EXISTS (
                    SELECT 1
                    FROM core.company_locations
                    WHERE company_id = p_company_id
                      AND location_code = candidate
                ) THEN
                    RETURN candidate;
                END IF;
            END LOOP;
        END
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION core.enforce_company_location_code()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF TG_OP = 'UPDATE' AND NEW.location_code IS DISTINCT FROM OLD.location_code THEN
                RAISE EXCEPTION 'Company Location code is immutable';
            END IF;
            IF NEW.location_code IS NULL OR btrim(NEW.location_code) = '' THEN
                NEW.location_code := core.next_company_location_code(NEW.company_id);
            ELSE
                NEW.location_code := upper(btrim(NEW.location_code));
            END IF;
            RETURN NEW;
        END
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_company_locations_location_code
        BEFORE INSERT OR UPDATE OF location_code
        ON core.company_locations
        FOR EACH ROW
        EXECUTE FUNCTION core.enforce_company_location_code()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER trg_company_locations_location_code "
        "ON core.company_locations"
    )
    op.execute("DROP FUNCTION core.enforce_company_location_code()")
    op.execute("DROP FUNCTION core.next_company_location_code(uuid)")
    op.drop_table("company_location_code_counters", schema=CORE_SCHEMA)
    op.drop_index(
        "uq_company_locations_company_id_location_code",
        table_name="company_locations",
        schema=CORE_SCHEMA,
    )
    op.drop_constraint(
        "ck_company_locations_code_format",
        "company_locations",
        schema=CORE_SCHEMA,
        type_="check",
    )
    op.drop_column("company_locations", "location_code", schema=CORE_SCHEMA)
