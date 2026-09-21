from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from skmc_erp.model_base import Base


class CurrencyStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class CompanyReportingCurrencyStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class Currency(Base):
    __tablename__ = "currencies"
    __table_args__ = (
        CheckConstraint(
            "code ~ '^[A-Z]{3}$'",
            name="ck_currencies_code_format",
        ),
        CheckConstraint(
            "btrim(name) <> ''",
            name="ck_currencies_name_not_blank",
        ),
        CheckConstraint(
            "symbol IS NULL OR btrim(symbol) <> ''",
            name="ck_currencies_symbol_not_blank",
        ),
        CheckConstraint(
            "minor_units BETWEEN 0 AND 4",
            name="ck_currencies_minor_units_range",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_currencies_status",
        ),
        PrimaryKeyConstraint("code", name="pk_currencies"),
        {"schema": "core"},
    )

    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(16), nullable=True)
    minor_units: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[CurrencyStatus] = mapped_column(
        Enum(
            CurrencyStatus,
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


class CompanyReportingCurrency(Base):
    __tablename__ = "company_reporting_currencies"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_company_reporting_currencies_status",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_reporting_currencies_company_id_companies",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["currency_code"],
            ["core.currencies.code"],
            name="fk_company_reporting_currencies_currency_code_currencies",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint(
            "company_id",
            "currency_code",
            name="pk_company_reporting_currencies",
        ),
        {"schema": "core"},
    )

    company_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
    )
    currency_code: Mapped[str] = mapped_column(
        String(3),
        primary_key=True,
    )
    status: Mapped[CompanyReportingCurrencyStatus] = mapped_column(
        Enum(
            CompanyReportingCurrencyStatus,
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
