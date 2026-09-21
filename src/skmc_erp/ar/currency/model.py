from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Index,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from skmc_erp.model_base import Base


class CompanyARCurrencyStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class CompanyARCurrency(Base):
    __tablename__ = "company_ar_currencies"
    __table_args__ = (
        CheckConstraint(
            "NOT is_default_billing OR billing_enabled",
            name="ck_company_ar_currencies_default_billing_enabled",
        ),
        CheckConstraint(
            "NOT is_default_receipt OR receipt_enabled",
            name="ck_company_ar_currencies_default_receipt_enabled",
        ),
        CheckConstraint(
            "status <> 'ACTIVE' OR billing_enabled OR receipt_enabled",
            name="ck_company_ar_currencies_active_use_enabled",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_company_ar_currencies_status",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_ar_currencies_company_id_companies",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["currency_code"],
            ["core.currencies.code"],
            name="fk_company_ar_currencies_currency_code_currencies",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_company_ar_currencies"),
        UniqueConstraint(
            "company_id",
            "currency_code",
            name="uq_company_ar_currencies_company_currency",
        ),
        Index(
            "uq_company_ar_currencies_active_billing_default",
            "company_id",
            unique=True,
            postgresql_where=text(
                "status = 'ACTIVE' AND billing_enabled = true "
                "AND is_default_billing = true"
            ),
        ),
        Index(
            "uq_company_ar_currencies_active_receipt_default",
            "company_id",
            unique=True,
            postgresql_where=text(
                "status = 'ACTIVE' AND receipt_enabled = true "
                "AND is_default_receipt = true"
            ),
        ),
        {"schema": "ar"},
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
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    billing_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    receipt_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    is_default_billing: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    is_default_receipt: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    status: Mapped[CompanyARCurrencyStatus] = mapped_column(
        Enum(
            CompanyARCurrencyStatus,
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
