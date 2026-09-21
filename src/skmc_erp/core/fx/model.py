from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Numeric,
    PrimaryKeyConstraint,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from skmc_erp.model_base import Base


class ExchangeRateType(StrEnum):
    CORPORATE = "CORPORATE"
    SPOT = "SPOT"


class ExchangeRateStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    __table_args__ = (
        CheckConstraint(
            "rate > 0",
            name="ck_exchange_rates_rate_positive",
        ),
        CheckConstraint(
            "from_currency_code <> to_currency_code",
            name="ck_exchange_rates_currency_pair",
        ),
        CheckConstraint(
            "rate_type IN ('CORPORATE', 'SPOT')",
            name="ck_exchange_rates_rate_type",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_exchange_rates_effective_dates",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_exchange_rates_status",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_exchange_rates_company_id_companies",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["from_currency_code"],
            ["core.currencies.code"],
            name="fk_exchange_rates_from_currency_currencies",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["to_currency_code"],
            ["core.currencies.code"],
            name="fk_exchange_rates_to_currency_currencies",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_exchange_rates"),
        ExcludeConstraint(
            ("company_id", "="),
            ("from_currency_code", "="),
            ("to_currency_code", "="),
            ("rate_type", "="),
            (text("daterange(effective_from, effective_to, '[]')"), "&&"),
            name="ex_exchange_rates_active_period_overlap",
            using="gist",
            where=text("status = 'ACTIVE'"),
        ),
        {"schema": "core"},
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    company_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )
    from_currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    to_currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    rate_type: Mapped[ExchangeRateType] = mapped_column(
        Enum(
            ExchangeRateType,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=20,
        ),
        nullable=False,
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[ExchangeRateStatus] = mapped_column(
        Enum(
            ExchangeRateStatus,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=20,
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
