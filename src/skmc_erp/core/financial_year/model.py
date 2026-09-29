from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    UniqueConstraint,
    column,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from skmc_erp.model_base import Base


class FiscalYearPattern(StrEnum):
    APR_MAR = "APR_MAR"
    JAN_DEC = "JAN_DEC"
    CUSTOM = "CUSTOM"


class FinancialYearStatus(StrEnum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class CompanyFiscalSettings(Base):
    __tablename__ = "company_fiscal_settings"
    __table_args__ = (
        CheckConstraint(
            "fiscal_year_pattern IN ('APR_MAR', 'JAN_DEC', 'CUSTOM')",
            name="ck_company_fiscal_settings_pattern",
        ),
        CheckConstraint(
            "start_month BETWEEN 1 AND 12",
            name="ck_company_fiscal_settings_start_month",
        ),
        CheckConstraint(
            "start_day BETWEEN 1 AND CASE "
            "WHEN start_month = 2 THEN 28 "
            "WHEN start_month IN (4, 6, 9, 11) THEN 30 "
            "ELSE 31 END",
            name="ck_company_fiscal_settings_recurring_date",
        ),
        CheckConstraint(
            "(fiscal_year_pattern = 'APR_MAR' "
            "AND start_month = 4 AND start_day = 1) "
            "OR (fiscal_year_pattern = 'JAN_DEC' "
            "AND start_month = 1 AND start_day = 1) "
            "OR fiscal_year_pattern = 'CUSTOM'",
            name="ck_company_fiscal_settings_pattern_values",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_fiscal_settings_company_id_companies",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("company_id", name="pk_company_fiscal_settings"),
        {"schema": "core"},
    )

    company_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
    )
    fiscal_year_pattern: Mapped[FiscalYearPattern] = mapped_column(
        Enum(
            FiscalYearPattern,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=20,
        ),
        nullable=False,
    )
    start_month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    start_day: Mapped[int] = mapped_column(SmallInteger, nullable=False)
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


class FinancialYear(Base):
    __tablename__ = "financial_years"
    __table_args__ = (
        CheckConstraint(
            "end_date >= start_date",
            name="ck_financial_years_date_order",
        ),
        CheckConstraint(
            "btrim(display_code) <> ''",
            name="ck_financial_years_display_code_not_blank",
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'OPEN', 'CLOSED')",
            name="ck_financial_years_status",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_financial_years_company_id_companies",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_financial_years"),
        UniqueConstraint(
            "company_id",
            "display_code",
            name="uq_financial_years_company_id_display_code",
        ),
        UniqueConstraint(
            "company_id",
            "id",
            name="uq_financial_years_company_id_id",
        ),
        ExcludeConstraint(
            (column("company_id"), "="),
            (
                func.daterange(
                    column("start_date"),
                    column("end_date"),
                    "[]",
                ),
                "&&",
            ),
            name="ex_financial_years_company_date_overlap",
            using="gist",
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
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    display_code: Mapped[str] = mapped_column(String(30), nullable=False)
    is_transition: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    status: Mapped[FinancialYearStatus] = mapped_column(
        Enum(
            FinancialYearStatus,
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
