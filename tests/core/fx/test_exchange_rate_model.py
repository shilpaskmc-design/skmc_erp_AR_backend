from sqlalchemy import CheckConstraint, ForeignKeyConstraint
from sqlalchemy.dialects.postgresql import ExcludeConstraint

from skmc_erp.core.fx.model import (
    ExchangeRate,
    ExchangeRateStatus,
    ExchangeRateType,
)
from skmc_erp.model_base import Base


def test_exchange_rate_metadata_matches_contract() -> None:
    table = ExchangeRate.__table__

    assert table is Base.metadata.tables["core.exchange_rates"]
    assert table.schema == "core"
    assert list(table.columns.keys()) == [
        "id",
        "company_id",
        "from_currency_code",
        "to_currency_code",
        "rate",
        "rate_type",
        "effective_from",
        "effective_to",
        "source",
        "status",
        "created_at",
        "updated_at",
    ]
    assert table.primary_key.name == "pk_exchange_rates"
    assert table.c.id.type.as_uuid
    assert str(table.c.id.server_default.arg) == "gen_random_uuid()"
    assert table.c.from_currency_code.type.length == 3
    assert table.c.to_currency_code.type.length == 3
    assert table.c.rate.type.precision == 28
    assert table.c.rate.type.scale == 12
    assert table.c.rate.server_default is None
    assert table.c.rate_type.type.length == 20
    assert not table.c.rate_type.type.native_enum
    assert not table.c.effective_from.nullable
    assert table.c.effective_to.nullable
    assert table.c.source.type.length == 100
    assert table.c.source.nullable
    assert table.c.status.type.length == 20
    assert table.c.status.server_default is None
    assert not table.c.status.type.native_enum
    assert not table.indexes

    for timestamp_column in (table.c.created_at, table.c.updated_at):
        assert timestamp_column.type.timezone
        assert not timestamp_column.nullable
        assert str(timestamp_column.server_default.arg) == "CURRENT_TIMESTAMP"


def test_exchange_rate_constraints_match_contract() -> None:
    table = ExchangeRate.__table__
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert checks == {
        "ck_exchange_rates_rate_positive": "rate > 0",
        "ck_exchange_rates_currency_pair": (
            "from_currency_code <> to_currency_code"
        ),
        "ck_exchange_rates_rate_type": (
            "rate_type IN ('CORPORATE', 'SPOT')"
        ),
        "ck_exchange_rates_effective_dates": (
            "effective_to IS NULL OR effective_to >= effective_from"
        ),
        "ck_exchange_rates_status": "status IN ('ACTIVE', 'INACTIVE')",
    }

    foreign_keys = {
        constraint.name: (
            tuple(element.parent.name for element in constraint.elements),
            tuple(element.target_fullname for element in constraint.elements),
            constraint.ondelete,
        )
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    assert foreign_keys == {
        "fk_exchange_rates_company_id_companies": (
            ("company_id",),
            ("core.companies.id",),
            "NO ACTION",
        ),
        "fk_exchange_rates_from_currency_currencies": (
            ("from_currency_code",),
            ("core.currencies.code",),
            "NO ACTION",
        ),
        "fk_exchange_rates_to_currency_currencies": (
            ("to_currency_code",),
            ("core.currencies.code",),
            "NO ACTION",
        ),
    }

    exclusions = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, ExcludeConstraint)
    ]
    assert len(exclusions) == 1
    exclusion = exclusions[0]
    assert exclusion.name == "ex_exchange_rates_active_period_overlap"
    assert exclusion.using == "gist"
    assert str(exclusion.where) == "status = 'ACTIVE'"


def test_exchange_rate_enums_contain_only_approved_values() -> None:
    assert {value.value for value in ExchangeRateType} == {
        "CORPORATE",
        "SPOT",
    }
    assert {value.value for value in ExchangeRateStatus} == {
        "ACTIVE",
        "INACTIVE",
    }
