from uuid import uuid4

from sqlalchemy import text

from tests.integration.company_configuration_migration_support import (
    connection,
    rejected,
    run_migration_case,
    scalar,
    seed_company,
)


REVISION = "0029_document_numbering_configuration"
PREVIOUS_REVISION = "0028_revenue_gl_mapping_enhancement"


async def _exercise(database_url: str) -> None:
    async with connection(database_url) as value:
        columns = await value.execute(
            text(
                """
                SELECT table_name, column_name, data_type,
                       character_maximum_length, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'ar'
                  AND table_name IN (
                      'document_sequences',
                      'document_sequence_conditions'
                  )
                ORDER BY table_name, ordinal_position
                """
            )
        )
        actual_columns = [tuple(row) for row in columns]
        constraints = await value.execute(
            text(
                """
                SELECT rel.relname, con.conname, con.contype::text
                FROM pg_constraint con
                JOIN pg_class rel ON rel.oid = con.conrelid
                JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
                WHERE nsp.nspname = 'ar'
                  AND rel.relname IN (
                      'document_sequences',
                      'document_sequence_conditions'
                  )
                  AND con.contype IN ('p', 'c', 'f', 'u')
                """
            )
        )
        actual = {
            (row.relname, row.conname, row.contype)
            for row in constraints
        }
        delete_actions = await value.execute(
            text(
                """
                SELECT con.conname, con.confdeltype::text
                FROM pg_constraint con
                JOIN pg_class rel ON rel.oid = con.conrelid
                JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
                WHERE nsp.nspname = 'ar'
                  AND rel.relname IN (
                      'document_sequences',
                      'document_sequence_conditions'
                  )
                  AND con.contype = 'f'
                """
            )
        )
        actual_delete_actions = {
            row.conname: row.confdeltype for row in delete_actions
        }
        indexes = await value.execute(
            text(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'ar'
                  AND tablename IN (
                      'document_sequences',
                      'document_sequence_conditions'
                  )
                """
            )
        )
        actual_indexes = {row.indexname for row in indexes}
    assert actual_columns == [
        ("document_sequence_conditions", "id", "uuid", None, "NO", None),
        (
            "document_sequence_conditions",
            "document_sequence_id",
            "uuid",
            None,
            "NO",
            None,
        ),
        (
            "document_sequence_conditions",
            "condition_type",
            "character varying",
            40,
            "NO",
            None,
        ),
        (
            "document_sequence_conditions",
            "operator",
            "character varying",
            20,
            "NO",
            None,
        ),
        (
            "document_sequence_conditions",
            "condition_value",
            "character varying",
            255,
            "NO",
            None,
        ),
        (
            "document_sequence_conditions",
            "created_at",
            "timestamp with time zone",
            None,
            "NO",
            None,
        ),
        (
            "document_sequence_conditions",
            "updated_at",
            "timestamp with time zone",
            None,
            "NO",
            None,
        ),
        ("document_sequences", "id", "uuid", None, "NO", None),
        ("document_sequences", "company_id", "uuid", None, "NO", None),
        (
            "document_sequences",
            "financial_year_id",
            "uuid",
            None,
            "NO",
            None,
        ),
        (
            "document_sequences",
            "document_type",
            "character varying",
            10,
            "NO",
            None,
        ),
        (
            "document_sequences",
            "series_name",
            "character varying",
            100,
            "NO",
            None,
        ),
        (
            "document_sequences",
            "format",
            "character varying",
            255,
            "NO",
            None,
        ),
        (
            "document_sequences",
            "prefix",
            "character varying",
            50,
            "YES",
            None,
        ),
        ("document_sequences", "start_number", "bigint", None, "NO", None),
        ("document_sequences", "next_number", "bigint", None, "NO", None),
        ("document_sequences", "padding", "smallint", None, "NO", None),
        ("document_sequences", "priority", "integer", None, "YES", None),
        (
            "document_sequences",
            "status",
            "character varying",
            20,
            "NO",
            None,
        ),
        (
            "document_sequences",
            "created_at",
            "timestamp with time zone",
            None,
            "NO",
            None,
        ),
        (
            "document_sequences",
            "updated_at",
            "timestamp with time zone",
            None,
            "NO",
            None,
        ),
    ]
    assert actual == {
        ("document_sequences", "pk_document_sequences", "p"),
        (
            "document_sequences",
            "uq_document_sequences_company_fy_type_name",
            "u",
        ),
        (
            "document_sequences",
            "fk_document_sequences_company_id_companies",
            "f",
        ),
        (
            "document_sequences",
            "fk_document_sequences_company_financial_year",
            "f",
        ),
        (
            "document_sequences",
            "ck_document_sequences_document_type",
            "c",
        ),
        (
            "document_sequences",
            "ck_document_sequences_start_number",
            "c",
        ),
        (
            "document_sequences",
            "ck_document_sequences_next_number",
            "c",
        ),
        ("document_sequences", "ck_document_sequences_padding", "c"),
        ("document_sequences", "ck_document_sequences_status", "c"),
        (
            "document_sequence_conditions",
            "pk_document_sequence_conditions",
            "p",
        ),
        (
            "document_sequence_conditions",
            "fk_document_sequence_conditions_sequence_id_sequences",
            "f",
        ),
    }
    assert actual_delete_actions == {
        "fk_document_sequences_company_id_companies": "a",
        "fk_document_sequences_company_financial_year": "a",
        "fk_document_sequence_conditions_sequence_id_sequences": "a",
    }
    assert actual_indexes == {
        "pk_document_sequences",
        "uq_document_sequences_company_fy_type_name",
        "pk_document_sequence_conditions",
    }

    _, company_id = await seed_company(database_url)
    _, other_company_id = await seed_company(database_url)
    financial_year_id = await scalar(
        database_url,
        """
        INSERT INTO core.financial_years
            (company_id, start_date, end_date, display_code, status)
        VALUES
            (:company_id, '2026-04-01', '2027-03-31', 'FY26', 'OPEN')
        RETURNING id
        """,
        {"company_id": company_id},
    )
    other_financial_year_id = await scalar(
        database_url,
        """
        INSERT INTO core.financial_years
            (company_id, start_date, end_date, display_code, status)
        VALUES
            (:company_id, '2026-04-01', '2027-03-31', 'FY26', 'OPEN')
        RETURNING id
        """,
        {"company_id": other_company_id},
    )
    sequence_id = await scalar(
        database_url,
        """
        INSERT INTO ar.document_sequences
            (id, company_id, financial_year_id, document_type, series_name,
             format, prefix, start_number, next_number, padding, priority,
             status, created_at, updated_at)
        VALUES
            (:id, :company_id, :financial_year_id, 'TI', 'Main',
             '{PREFIX}/{NUMBER}', 'INV', 1, 1, 6, NULL,
             'ACTIVE', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        RETURNING id
        """,
        {
            "id": uuid4(),
            "company_id": company_id,
            "financial_year_id": financial_year_id,
        },
    )
    await scalar(
        database_url,
        """
        INSERT INTO ar.document_sequence_conditions
            (id, document_sequence_id, condition_type, operator,
             condition_value, created_at, updated_at)
        VALUES
            (:id, :sequence_id, 'LOCATION', 'EQUALS', :value,
             CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        RETURNING id
        """,
        {"id": uuid4(), "sequence_id": sequence_id, "value": str(uuid4())},
    )

    base = {
        "id": uuid4(),
        "company_id": company_id,
        "financial_year_id": financial_year_id,
    }
    insert_sql = """
        INSERT INTO ar.document_sequences
            (id, company_id, financial_year_id, document_type, series_name,
             format, start_number, next_number, padding, status,
             created_at, updated_at)
        VALUES
            (:id, :company_id, :financial_year_id, :document_type,
             :series_name, '{NUMBER}', :start_number, :next_number,
             :padding, :status, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """
    for overrides in (
        {"document_type": "BAD"},
        {"start_number": 0},
        {"start_number": 2, "next_number": 1},
        {"padding": 0},
        {"status": "DRAFT"},
    ):
        await rejected(
            database_url,
            insert_sql,
            {
                **base,
                "id": uuid4(),
                "document_type": "PI",
                "series_name": str(uuid4()),
                "start_number": 1,
                "next_number": 1,
                "padding": 1,
                "status": "ACTIVE",
                **overrides,
            },
        )

    await rejected(
        database_url,
        insert_sql,
        {
            **base,
            "id": uuid4(),
            "document_type": "TI",
            "series_name": "Main",
            "start_number": 1,
            "next_number": 1,
            "padding": 1,
            "status": "ACTIVE",
        },
    )
    await rejected(
        database_url,
        """
        INSERT INTO ar.document_sequences
            (id, company_id, financial_year_id, document_type, series_name,
             format, start_number, next_number, padding,
             created_at, updated_at)
        VALUES
            (:id, :company_id, :financial_year_id, 'PI', 'Missing Status',
             '{NUMBER}', 1, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        {
            **base,
            "id": uuid4(),
        },
    )
    await rejected(
        database_url,
        insert_sql,
        {
            **base,
            "id": uuid4(),
            "financial_year_id": other_financial_year_id,
            "document_type": "PI",
            "series_name": "Cross Company",
            "start_number": 1,
            "next_number": 1,
            "padding": 1,
            "status": "ACTIVE",
        },
    )
    await rejected(
        database_url,
        """
        INSERT INTO ar.document_sequence_conditions
            (id, document_sequence_id, condition_type, operator,
             condition_value, created_at, updated_at)
        VALUES
            (:id, :sequence_id, 'LOCATION', 'EQUALS', 'missing',
             CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        {"id": uuid4(), "sequence_id": uuid4()},
    )
    await rejected(
        database_url,
        "DELETE FROM ar.document_sequences WHERE id = :id",
        {"id": sequence_id},
    )


def test_document_numbering_migration_contract() -> None:
    run_migration_case(
        REVISION,
        PREVIOUS_REVISION,
        ("ar.document_sequences", "ar.document_sequence_conditions"),
        _exercise,
    )
