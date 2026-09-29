import asyncio
import os
from collections.abc import AsyncIterator, Iterator, Mapping
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from skmc_erp.config import get_settings


REVISION = "0019_tax_statutory_codes_rates"
PREVIOUS_REVISION = "0018_gl_account_group_mappings"


@asynccontextmanager
async def _connection(database_url: str) -> AsyncIterator[AsyncConnection]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            yield connection
    finally:
        await engine.dispose()


async def _assert_safe_empty_database(database_url: str) -> None:
    async with _connection(database_url) as connection:
        if await connection.scalar(text("SELECT to_regnamespace('core') IS NOT NULL")):
            pytest.fail(
                "TEST_DATABASE_URL must point to a database without core schema"
            )
        if await connection.scalar(
            text("SELECT to_regclass('public.alembic_version') IS NOT NULL")
        ):
            count = await connection.scalar(
                text("SELECT count(*) FROM public.alembic_version")
            )
            if count:
                pytest.fail("TEST_DATABASE_URL already has an applied Alembic revision")


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    value = os.getenv("TEST_DATABASE_URL")
    if value is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL migration tests")
    if make_url(value).drivername != "postgresql+asyncpg":
        pytest.fail("TEST_DATABASE_URL must use postgresql+asyncpg")

    asyncio.run(_assert_safe_empty_database(value))
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = value
    get_settings.cache_clear()
    config = Config("alembic.ini")

    try:
        command.upgrade(config, PREVIOUS_REVISION)
        yield value
    finally:
        try:
            command.downgrade(config, "base")
        finally:
            if previous is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = previous
            get_settings.cache_clear()


async def _execute(
    database_url: str,
    sql: str,
    parameters: Mapping[str, object] | None = None,
) -> None:
    async with _connection(database_url) as connection:
        async with connection.begin():
            await connection.execute(text(sql), parameters or {})


async def _scalar(
    database_url: str,
    sql: str,
    parameters: Mapping[str, object] | None = None,
) -> object:
    async with _connection(database_url) as connection:
        async with connection.begin():
            return await connection.scalar(text(sql), parameters or {})


async def _rows(
    database_url: str,
    sql: str,
    parameters: Mapping[str, object] | None = None,
) -> list[tuple[object, ...]]:
    async with _connection(database_url) as connection:
        async with connection.begin():
            result = await connection.execute(text(sql), parameters or {})
            return [tuple(row) for row in result.all()]


async def _assert_rejected(
    database_url: str,
    sql: str,
    parameters: Mapping[str, object] | None = None,
) -> None:
    with pytest.raises(DBAPIError):
        await _execute(database_url, sql, parameters)


async def _parent_schema_snapshot(
    database_url: str,
) -> tuple[set[tuple[object, ...]], set[tuple[object, ...]]]:
    columns = set(
        await _rows(
            database_url,
            "SELECT table_name, column_name, ordinal_position, data_type, "
            "is_nullable, column_default FROM information_schema.columns "
            "WHERE table_schema = 'core' "
            "AND table_name IN ('tax_types', 'tax_rates')",
        )
    )
    constraints = set(
        await _rows(
            database_url,
            "SELECT rel.relname, con.conname, con.contype::text "
            "FROM pg_constraint con "
            "JOIN pg_class rel ON rel.oid = con.conrelid "
            "JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace "
            "WHERE nsp.nspname = 'core' "
            "AND rel.relname IN ('tax_types', 'tax_rates')",
        )
    )
    return columns, constraints


async def _seed_prerequisites(database_url: str) -> dict[str, UUID]:
    await _execute(
        database_url,
        "INSERT INTO core.countries (code, name, status) VALUES "
        "('IN', 'India', 'ACTIVE'), ('US', 'United States', 'ACTIVE')",
    )
    identifiers: dict[str, UUID] = {}
    for key, code, name, country in (
        ("gst", "GST", "Goods and Services Tax", "IN"),
        ("tds", "TDS", "Tax Deducted at Source", "IN"),
        ("tds_us", "TDS", "US Withholding Tax", "US"),
    ):
        identifiers[key] = await _scalar(
            database_url,
            "INSERT INTO core.tax_types (code, name, country_code, status) "
            "VALUES (:code, :name, :country, 'ACTIVE') RETURNING id",
            {"code": code, "name": name, "country": country},
        )
    identifiers["ordinary_rate"] = await _scalar(
        database_url,
        "INSERT INTO core.tax_rates "
        "(tax_type_id, rate_percent, country_code, status) "
        "VALUES (:tax_type_id, 18, 'IN', 'ACTIVE') RETURNING id",
        {"tax_type_id": identifiers["gst"]},
    )
    return identifiers


async def _insert_code(
    database_url: str,
    *,
    tax_type_id: UUID,
    code: str,
    name: str,
    code_kind: str,
    country_code: str = "IN",
    status: str = "ACTIVE",
    description: str | None = None,
) -> UUID:
    return await _scalar(
        database_url,
        "INSERT INTO core.tax_statutory_codes "
        "(tax_type_id, code, name, description, code_kind, country_code, status) "
        "VALUES (:tax_type_id, :code, :name, :description, :code_kind, "
        ":country_code, :status) RETURNING id",
        {
            "tax_type_id": tax_type_id,
            "code": code,
            "name": name,
            "description": description,
            "code_kind": code_kind,
            "country_code": country_code,
            "status": status,
        },
    )


async def _insert_rate(
    database_url: str,
    *,
    statutory_code_id: UUID,
    case_code: str | None,
    rate_percent: Decimal | int | str,
    valid_from: date,
    valid_to: date | None,
    status: str = "ACTIVE",
) -> UUID:
    return await _scalar(
        database_url,
        "INSERT INTO core.tax_statutory_code_rates "
        "(tax_statutory_code_id, case_code, rate_percent, valid_from, "
        "valid_to, status) VALUES (:statutory_code_id, :case_code, "
        ":rate_percent, :valid_from, :valid_to, :status) RETURNING id",
        {
            "statutory_code_id": statutory_code_id,
            "case_code": case_code,
            "rate_percent": rate_percent,
            "valid_from": valid_from,
            "valid_to": valid_to,
            "status": status,
        },
    )


async def _assert_schema_contract(database_url: str) -> None:
    for table_name in ("tax_statutory_codes", "tax_statutory_code_rates"):
        assert await _scalar(
            database_url,
            "SELECT to_regclass(:table_name) IS NOT NULL",
            {"table_name": f"core.{table_name}"},
        )

    code_columns = await _rows(
        database_url,
        "SELECT column_name, data_type, character_maximum_length, "
        "numeric_precision, numeric_scale, is_nullable, column_default "
        "FROM information_schema.columns WHERE table_schema = 'core' "
        "AND table_name = 'tax_statutory_codes' ORDER BY ordinal_position",
    )
    assert code_columns == [
        ("id", "uuid", None, None, None, "NO", "gen_random_uuid()"),
        ("tax_type_id", "uuid", None, None, None, "NO", None),
        ("code", "character varying", 50, None, None, "NO", None),
        ("name", "character varying", 150, None, None, "NO", None),
        ("description", "character varying", 500, None, None, "YES", None),
        ("code_kind", "character varying", 20, None, None, "NO", None),
        ("country_code", "character varying", 2, None, None, "NO", None),
        ("status", "character varying", 20, None, None, "NO", None),
        (
            "created_at",
            "timestamp with time zone",
            None,
            None,
            None,
            "NO",
            "CURRENT_TIMESTAMP",
        ),
        (
            "updated_at",
            "timestamp with time zone",
            None,
            None,
            None,
            "NO",
            "CURRENT_TIMESTAMP",
        ),
    ]

    rate_columns = await _rows(
        database_url,
        "SELECT column_name, data_type, character_maximum_length, "
        "numeric_precision, numeric_scale, is_nullable, column_default "
        "FROM information_schema.columns WHERE table_schema = 'core' "
        "AND table_name = 'tax_statutory_code_rates' ORDER BY ordinal_position",
    )
    assert rate_columns == [
        ("id", "uuid", None, None, None, "NO", "gen_random_uuid()"),
        ("tax_statutory_code_id", "uuid", None, None, None, "NO", None),
        ("case_code", "character varying", 50, None, None, "YES", None),
        ("rate_percent", "numeric", None, 9, 6, "NO", None),
        ("valid_from", "date", None, None, None, "NO", None),
        ("valid_to", "date", None, None, None, "YES", None),
        ("status", "character varying", 20, None, None, "NO", None),
        (
            "created_at",
            "timestamp with time zone",
            None,
            None,
            None,
            "NO",
            "CURRENT_TIMESTAMP",
        ),
        (
            "updated_at",
            "timestamp with time zone",
            None,
            None,
            None,
            "NO",
            "CURRENT_TIMESTAMP",
        ),
    ]

    code_constraints = dict(
        await _rows(
            database_url,
            "SELECT con.conname, con.contype::text FROM pg_constraint con "
            "JOIN pg_class rel ON rel.oid = con.conrelid "
            "JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace "
            "WHERE nsp.nspname = 'core' "
            "AND rel.relname = 'tax_statutory_codes' "
            "AND con.contype IN ('p', 'c', 'f', 'x', 'u')",
        )
    )
    assert code_constraints == {
        "pk_tax_statutory_codes": "p",
        "ck_tax_statutory_codes_code_not_blank": "c",
        "ck_tax_statutory_codes_name_not_blank": "c",
        "ck_tax_statutory_codes_code_kind": "c",
        "ck_tax_statutory_codes_country_code_format": "c",
        "ck_tax_statutory_codes_status": "c",
        "fk_tax_statutory_codes_tax_type_id_tax_types": "f",
        "uq_tax_statutory_codes_tax_type_country_kind_code": "u",
    }
    rate_constraints = dict(
        await _rows(
            database_url,
            "SELECT con.conname, con.contype::text FROM pg_constraint con "
            "JOIN pg_class rel ON rel.oid = con.conrelid "
            "JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace "
            "WHERE nsp.nspname = 'core' "
            "AND rel.relname = 'tax_statutory_code_rates' "
            "AND con.contype IN ('p', 'c', 'f', 'x', 'u')",
        )
    )
    assert rate_constraints == {
        "pk_tax_statutory_code_rates": "p",
        "ck_tax_statutory_code_rates_case_code_not_blank": "c",
        "ck_tax_statutory_code_rates_rate_percent_range": "c",
        "ck_tax_statutory_code_rates_date_order": "c",
        "ck_tax_statutory_code_rates_status": "c",
        "fk_tax_statutory_code_rates_statutory_code": "f",
        "ex_tax_statutory_code_rates_active_named_overlap": "x",
        "ex_tax_statutory_code_rates_active_default_overlap": "x",
    }

    unique_columns = await _rows(
        database_url,
        "SELECT array_agg(att.attname ORDER BY key_columns.ordinality) "
        "FROM pg_constraint con "
        "JOIN pg_class rel ON rel.oid = con.conrelid "
        "JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace "
        "CROSS JOIN LATERAL unnest(con.conkey) WITH ORDINALITY "
        "AS key_columns(attnum, ordinality) "
        "JOIN pg_attribute att ON att.attrelid = rel.oid "
        "AND att.attnum = key_columns.attnum "
        "WHERE nsp.nspname = 'core' "
        "AND rel.relname = 'tax_statutory_codes' "
        "AND con.conname = 'uq_tax_statutory_codes_tax_type_country_kind_code' "
        "GROUP BY con.oid",
    )
    assert unique_columns == [
        (["tax_type_id", "country_code", "code_kind", "code"],)
    ]

    foreign_keys = await _rows(
        database_url,
        "SELECT rel.relname, con.conname, target_nsp.nspname, target.relname, "
        "con.confdeltype::text, con.confmatchtype::text "
        "FROM pg_constraint con "
        "JOIN pg_class rel ON rel.oid = con.conrelid "
        "JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace "
        "JOIN pg_class target ON target.oid = con.confrelid "
        "JOIN pg_namespace target_nsp ON target_nsp.oid = target.relnamespace "
        "WHERE nsp.nspname = 'core' AND con.contype = 'f' "
        "AND rel.relname IN "
        "('tax_statutory_codes', 'tax_statutory_code_rates')",
    )
    assert set(foreign_keys) == {
        (
            "tax_statutory_codes",
            "fk_tax_statutory_codes_tax_type_id_tax_types",
            "core",
            "tax_types",
            "a",
            "s",
        ),
        (
            "tax_statutory_code_rates",
            "fk_tax_statutory_code_rates_statutory_code",
            "core",
            "tax_statutory_codes",
            "a",
            "s",
        ),
    }

    exclusion_definitions = dict(
        await _rows(
            database_url,
            "SELECT con.conname, pg_get_constraintdef(con.oid) "
            "FROM pg_constraint con "
            "JOIN pg_class rel ON rel.oid = con.conrelid "
            "JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace "
            "WHERE nsp.nspname = 'core' "
            "AND rel.relname = 'tax_statutory_code_rates' "
            "AND con.contype = 'x'",
        )
    )
    named = exclusion_definitions[
        "ex_tax_statutory_code_rates_active_named_overlap"
    ]
    default = exclusion_definitions[
        "ex_tax_statutory_code_rates_active_default_overlap"
    ]
    assert "tax_statutory_code_id WITH =" in named
    assert "case_code WITH =" in named
    assert "daterange(valid_from, valid_to, '[]'::text) WITH &&" in named
    assert "case_code IS NOT NULL" in named
    assert "tax_statutory_code_id WITH =" in default
    assert "case_code WITH =" not in default
    assert "daterange(valid_from, valid_to, '[]'::text) WITH &&" in default
    assert "case_code IS NULL" in default

    code_indexes = dict(
        await _rows(
            database_url,
            "SELECT indexname, indexdef FROM pg_indexes "
            "WHERE schemaname = 'core' AND tablename = 'tax_statutory_codes'",
        )
    )
    assert set(code_indexes) == {
        "pk_tax_statutory_codes",
        "uq_tax_statutory_codes_tax_type_country_kind_code",
    }
    rate_indexes = dict(
        await _rows(
            database_url,
            "SELECT indexname, indexdef FROM pg_indexes "
            "WHERE schemaname = 'core' "
            "AND tablename = 'tax_statutory_code_rates'",
        )
    )
    assert set(rate_indexes) == {
        "pk_tax_statutory_code_rates",
        "ex_tax_statutory_code_rates_active_named_overlap",
        "ex_tax_statutory_code_rates_active_default_overlap",
    }


async def _run_code_contract(
    database_url: str,
    identifiers: Mapping[str, UUID],
) -> dict[str, UUID]:
    component_id = await _insert_code(
        database_url,
        tax_type_id=identifiers["gst"],
        code="CGST",
        name="Central GST",
        code_kind="COMPONENT",
    )
    section_id = await _insert_code(
        database_url,
        tax_type_id=identifiers["tds"],
        code="194C",
        name="Contractor Payment",
        code_kind="SECTION",
    )
    assert isinstance(component_id, UUID)
    assert isinstance(section_id, UUID)

    required_values: dict[str, object] = {
        "tax_type_id": identifiers["tds"],
        "code": "REQ",
        "name": "Required Fields",
        "code_kind": "SECTION",
        "country_code": "IN",
        "status": "ACTIVE",
    }
    required_insert = (
        "INSERT INTO core.tax_statutory_codes "
        "(tax_type_id, code, name, code_kind, country_code, status) "
        "VALUES (:tax_type_id, :code, :name, :code_kind, :country_code, :status)"
    )
    for column_name in required_values:
        invalid_values = dict(required_values)
        invalid_values[column_name] = None
        await _assert_rejected(database_url, required_insert, invalid_values)

    for code in ("", "   "):
        await _assert_rejected(
            database_url,
            required_insert,
            {**required_values, "code": code},
        )
    for name in ("", "   "):
        await _assert_rejected(
            database_url,
            required_insert,
            {**required_values, "name": name},
        )
    await _assert_rejected(
        database_url,
        required_insert,
        {**required_values, "code_kind": "OTHER"},
    )
    await _assert_rejected(
        database_url,
        required_insert,
        {**required_values, "status": "DRAFT"},
    )
    for country_code in ("in", "In", "I1", "I", "IND"):
        await _assert_rejected(
            database_url,
            required_insert,
            {**required_values, "country_code": country_code},
        )

    preserved_id = await _insert_code(
        database_url,
        tax_type_id=identifiers["tds"],
        code="  Mixed Code  ",
        name="  Mixed Name  ",
        code_kind="SECTION",
        country_code="ZZ",
    )
    assert await _rows(
        database_url,
        "SELECT code, name, country_code FROM core.tax_statutory_codes "
        "WHERE id = :id",
        {"id": preserved_id},
    ) == [("  Mixed Code  ", "  Mixed Name  ", "ZZ")]

    await _assert_rejected(
        database_url,
        required_insert,
        {
            **required_values,
            "code": "194C",
            "name": "Duplicate Tuple",
        },
    )
    await _insert_code(
        database_url,
        tax_type_id=identifiers["gst"],
        code="194C",
        name="Same Code Different Tax Type",
        code_kind="SECTION",
    )
    await _insert_code(
        database_url,
        tax_type_id=identifiers["tds"],
        code="194C",
        name="Same Code Different Country",
        code_kind="SECTION",
        country_code="ZZ",
    )
    await _insert_code(
        database_url,
        tax_type_id=identifiers["tds"],
        code="194C",
        name="Same Code Different Kind",
        code_kind="COMPONENT",
    )
    await _insert_code(
        database_url,
        tax_type_id=identifiers["tds"],
        code="194c",
        name="Case-sensitive Code",
        code_kind="SECTION",
    )
    await _insert_code(
        database_url,
        tax_type_id=identifiers["tds"],
        code="194J",
        name="Contractor Payment",
        code_kind="SECTION",
    )
    await _assert_rejected(
        database_url,
        required_insert,
        {**required_values, "tax_type_id": uuid4()},
    )

    return {"component": component_id, "section": section_id}


async def _run_rate_contract(
    database_url: str,
    identifiers: Mapping[str, UUID],
    statutory_codes: Mapping[str, UUID],
) -> None:
    section_rate_id = await _insert_rate(
        database_url,
        statutory_code_id=statutory_codes["section"],
        case_code=None,
        rate_percent=Decimal("2.000000"),
        valid_from=date(2026, 1, 1),
        valid_to=date(2026, 12, 31),
    )
    component_rate_id = await _insert_rate(
        database_url,
        statutory_code_id=statutory_codes["component"],
        case_code="STANDARD",
        rate_percent=Decimal("9.000000"),
        valid_from=date(2026, 1, 1),
        valid_to=None,
    )
    assert isinstance(section_rate_id, UUID)
    assert isinstance(component_rate_id, UUID)
    preserved_case_id = await _insert_rate(
        database_url,
        statutory_code_id=statutory_codes["section"],
        case_code="  Mixed Case  ",
        rate_percent=1,
        valid_from=date(2025, 1, 1),
        valid_to=date(2025, 12, 31),
    )
    assert await _scalar(
        database_url,
        "SELECT case_code FROM core.tax_statutory_code_rates WHERE id = :id",
        {"id": preserved_case_id},
    ) == "  Mixed Case  "

    required_values: dict[str, object] = {
        "statutory_code_id": statutory_codes["section"],
        "case_code": "REQUIRED",
        "rate_percent": Decimal("1.000000"),
        "valid_from": date(2027, 1, 1),
        "valid_to": date(2027, 12, 31),
        "status": "ACTIVE",
    }
    rate_insert = (
        "INSERT INTO core.tax_statutory_code_rates "
        "(tax_statutory_code_id, case_code, rate_percent, valid_from, "
        "valid_to, status) VALUES (:statutory_code_id, :case_code, "
        ":rate_percent, :valid_from, :valid_to, :status)"
    )
    for column_name in (
        "statutory_code_id",
        "rate_percent",
        "valid_from",
        "status",
    ):
        invalid_values = dict(required_values)
        invalid_values[column_name] = None
        await _assert_rejected(database_url, rate_insert, invalid_values)

    for case_code in ("", "   "):
        await _assert_rejected(
            database_url,
            rate_insert,
            {**required_values, "case_code": case_code},
        )
    for rate_percent in (Decimal("-0.000001"), Decimal("100.000001")):
        await _assert_rejected(
            database_url,
            rate_insert,
            {**required_values, "rate_percent": rate_percent},
        )
    await _assert_rejected(
        database_url,
        rate_insert,
        {**required_values, "status": "DRAFT"},
    )
    await _assert_rejected(
        database_url,
        rate_insert,
        {
            **required_values,
            "valid_from": date(2027, 2, 1),
            "valid_to": date(2027, 1, 31),
        },
    )
    await _assert_rejected(
        database_url,
        rate_insert,
        {**required_values, "statutory_code_id": uuid4()},
    )

    for case_code, rate_percent, valid_from, valid_to in (
        ("ZERO", 0, date(2027, 1, 1), date(2027, 12, 31)),
        ("HUNDRED", 100, date(2027, 1, 1), date(2027, 12, 31)),
        ("ONE_DAY", 1, date(2028, 1, 1), date(2028, 1, 1)),
        ("OPEN", 1, date(2028, 1, 1), None),
    ):
        await _insert_rate(
            database_url,
            statutory_code_id=statutory_codes["section"],
            case_code=case_code,
            rate_percent=rate_percent,
            valid_from=valid_from,
            valid_to=valid_to,
        )

    for valid_from, valid_to in (
        (date(2020, 1, 1), date(2020, 12, 31)),
        (date(2021, 1, 1), date(2021, 12, 31)),
        (date(2022, 1, 1), date(2022, 12, 31)),
    ):
        await _insert_rate(
            database_url,
            statutory_code_id=statutory_codes["section"],
            case_code="HISTORY",
            rate_percent=1,
            valid_from=valid_from,
            valid_to=valid_to,
        )

    await _insert_rate(
        database_url,
        statutory_code_id=statutory_codes["section"],
        case_code="NAMED_OVERLAP",
        rate_percent=1,
        valid_from=date(2030, 1, 1),
        valid_to=date(2030, 12, 31),
    )
    await _assert_rejected(
        database_url,
        rate_insert,
        {
            **required_values,
            "case_code": "NAMED_OVERLAP",
            "valid_from": date(2030, 12, 31),
            "valid_to": date(2031, 12, 31),
        },
    )

    default_code = await _insert_code(
        database_url,
        tax_type_id=identifiers["tds"],
        code="DEFAULT_CASE",
        name="Default Case Overlap",
        code_kind="SECTION",
    )
    await _insert_rate(
        database_url,
        statutory_code_id=default_code,
        case_code=None,
        rate_percent=1,
        valid_from=date(2030, 1, 1),
        valid_to=None,
    )
    await _assert_rejected(
        database_url,
        rate_insert,
        {
            **required_values,
            "statutory_code_id": default_code,
            "case_code": None,
            "valid_from": date(2030, 6, 1),
            "valid_to": date(2030, 6, 1),
        },
    )

    for case_code in ("CASE_A", "CASE_B"):
        await _insert_rate(
            database_url,
            statutory_code_id=statutory_codes["section"],
            case_code=case_code,
            rate_percent=1,
            valid_from=date(2032, 1, 1),
            valid_to=date(2032, 12, 31),
        )

    for status in ("INACTIVE", "INACTIVE"):
        await _insert_rate(
            database_url,
            statutory_code_id=statutory_codes["section"],
            case_code="INACTIVE_OVERLAP",
            rate_percent=1,
            valid_from=date(2033, 1, 1),
            valid_to=date(2033, 12, 31),
            status=status,
        )
    await _insert_rate(
        database_url,
        statutory_code_id=statutory_codes["section"],
        case_code="ACTIVE_INACTIVE",
        rate_percent=1,
        valid_from=date(2034, 1, 1),
        valid_to=date(2034, 12, 31),
        status="ACTIVE",
    )
    await _insert_rate(
        database_url,
        statutory_code_id=statutory_codes["section"],
        case_code="ACTIVE_INACTIVE",
        rate_percent=1,
        valid_from=date(2034, 6, 1),
        valid_to=date(2035, 6, 1),
        status="INACTIVE",
    )

    await _assert_rejected(
        database_url,
        "DELETE FROM core.tax_types WHERE id = :id",
        {"id": identifiers["tds"]},
    )
    await _assert_rejected(
        database_url,
        "DELETE FROM core.tax_statutory_codes WHERE id = :id",
        {"id": statutory_codes["section"]},
    )
    assert await _scalar(
        database_url,
        "SELECT count(*) = 1 FROM core.tax_types WHERE id = :id",
        {"id": identifiers["tds"]},
    )
    assert await _scalar(
        database_url,
        "SELECT count(*) = 1 FROM core.tax_statutory_codes WHERE id = :id",
        {"id": statutory_codes["section"]},
    )
    assert await _scalar(
        database_url,
        "SELECT count(*) = 1 FROM core.tax_statutory_code_rates WHERE id = :id",
        {"id": section_rate_id},
    )


async def _assert_downgrade(
    database_url: str,
    identifiers: Mapping[str, UUID],
    parent_snapshot: tuple[set[tuple[object, ...]], set[tuple[object, ...]]],
) -> None:
    assert not await _scalar(
        database_url,
        "SELECT to_regclass('core.tax_statutory_code_rates') IS NOT NULL",
    )
    assert not await _scalar(
        database_url,
        "SELECT to_regclass('core.tax_statutory_codes') IS NOT NULL",
    )
    for table_name in (
        "tax_types",
        "tax_rates",
        "company_hsn_sac_codes",
        "company_hsn_sac_tax_rates",
        "gl_account_group_mappings",
    ):
        assert await _scalar(
            database_url,
            "SELECT to_regclass(:table_name) IS NOT NULL",
            {"table_name": f"core.{table_name}"},
        )
    assert await _parent_schema_snapshot(database_url) == parent_snapshot
    assert await _scalar(
        database_url,
        "SELECT count(*) = 1 FROM core.tax_types WHERE id = :id",
        {"id": identifiers["gst"]},
    )
    assert await _scalar(
        database_url,
        "SELECT count(*) = 1 FROM core.tax_rates WHERE id = :id",
        {"id": identifiers["ordinary_rate"]},
    )
    assert await _scalar(
        database_url,
        "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'btree_gist')",
    )
    assert await _scalar(
        database_url,
        "SELECT version_num FROM public.alembic_version",
    ) == PREVIOUS_REVISION


async def _assert_reupgrade(
    database_url: str,
    parent_snapshot: tuple[set[tuple[object, ...]], set[tuple[object, ...]]],
) -> None:
    await _assert_schema_contract(database_url)
    assert await _parent_schema_snapshot(database_url) == parent_snapshot
    assert await _scalar(
        database_url,
        "SELECT version_num FROM public.alembic_version",
    ) == REVISION


def test_tax_statutory_code_migration_contract(database_url: str) -> None:
    config = Config("alembic.ini")
    identifiers = asyncio.run(_seed_prerequisites(database_url))
    parent_snapshot = asyncio.run(_parent_schema_snapshot(database_url))

    command.upgrade(config, REVISION)
    asyncio.run(_assert_schema_contract(database_url))
    statutory_codes = asyncio.run(
        _run_code_contract(database_url, identifiers)
    )
    asyncio.run(_run_rate_contract(database_url, identifiers, statutory_codes))
    assert asyncio.run(_parent_schema_snapshot(database_url)) == parent_snapshot

    command.downgrade(config, PREVIOUS_REVISION)
    asyncio.run(_assert_downgrade(database_url, identifiers, parent_snapshot))

    command.upgrade(config, REVISION)
    asyncio.run(_assert_reupgrade(database_url, parent_snapshot))

    script = ScriptDirectory.from_config(config)
    assert len(script.get_heads()) == 1
