import asyncio
from logging.config import fileConfig
from typing import Any

from sqlalchemy import (
    Column,
    MetaData,
    PrimaryKeyConstraint,
    String,
    Table,
    inspect,
    pool,
    text,
)
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from alembic.ddl.postgresql import PostgresqlImpl
from skmc_erp.config import get_settings
from skmc_erp.core.company import model as company_model  # noqa: F401
from skmc_erp.core.cost_center import model as cost_center_model  # noqa: F401
from skmc_erp.core.company_location import model as company_location_model  # noqa: F401
from skmc_erp.core.accounting import model as accounting_model  # noqa: F401
from skmc_erp.core.bank_account import model as bank_account_model  # noqa: F401
from skmc_erp.core.company_gst_registration import (  # noqa: F401
    model as company_gst_registration_model,
)
from skmc_erp.core.currency import model as currency_model  # noqa: F401
from skmc_erp.core.entity_type import model as entity_type_model  # noqa: F401
from skmc_erp.core.financial_year import model as financial_year_model  # noqa: F401
from skmc_erp.core.fx import model as fx_model  # noqa: F401
from skmc_erp.core.geography import model as geography_model  # noqa: F401
from skmc_erp.core.organisation import model as organisation_model  # noqa: F401
from skmc_erp.core.tenant import model as tenant_model  # noqa: F401
from skmc_erp.core.tax_reference import model as tax_reference_model  # noqa: F401
from skmc_erp.ar.catalogue import model as catalogue_model  # noqa: F401
from skmc_erp.ar.currency import model as ar_currency_model  # noqa: F401
from skmc_erp.ar.fx import model as ar_fx_model  # noqa: F401
from skmc_erp.ar.payment_term import model as payment_term_model  # noqa: F401
from skmc_erp.model_base import Base

ALEMBIC_VERSION_TABLE = "alembic_version"
ALEMBIC_VERSION_COLUMN_LENGTH = 255


class SKMCPostgresqlImpl(PostgresqlImpl):
    """Use durable storage for descriptive Alembic revision identifiers."""

    __dialect__ = "postgresql"

    def version_table_impl(
        self,
        *,
        version_table: str,
        version_table_schema: str | None,
        version_table_pk: bool,
        **kw: Any,
    ) -> Table:
        table = Table(
            version_table,
            MetaData(),
            Column(
                "version_num",
                String(ALEMBIC_VERSION_COLUMN_LENGTH),
                nullable=False,
            ),
            schema=version_table_schema,
        )
        if version_table_pk:
            table.append_constraint(
                PrimaryKeyConstraint(
                    "version_num",
                    name=f"{version_table}_pkc",
                )
            )
        return table

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

config.set_main_option(
    "sqlalchemy.url",
    get_settings().database_url.replace("%", "%%"),
)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def ensure_alembic_version_capacity(connection: Connection) -> None:
    """Widen a legacy Alembic version column before revision bookkeeping."""
    with connection.begin():
        inspector = inspect(connection)
        if not inspector.has_table(ALEMBIC_VERSION_TABLE):
            return

        columns = {
            column["name"]: column
            for column in inspector.get_columns(ALEMBIC_VERSION_TABLE)
        }
        version_column = columns.get("version_num")
        if version_column is None:
            raise RuntimeError(
                "alembic_version exists without the required version_num column"
            )

        current_length = getattr(version_column["type"], "length", None)
        if (
            current_length is None
            or current_length >= ALEMBIC_VERSION_COLUMN_LENGTH
        ):
            return

        connection.execute(
            text(
                "ALTER TABLE alembic_version "
                "ALTER COLUMN version_num TYPE VARCHAR(255)"
            )
        )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table=ALEMBIC_VERSION_TABLE,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    ensure_alembic_version_capacity(connection)
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        version_table=ALEMBIC_VERSION_TABLE,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
