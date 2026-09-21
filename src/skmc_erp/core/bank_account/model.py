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


class CompanyBankAccountStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class CompanyBankAccount(Base):
    __tablename__ = "company_bank_accounts"
    __table_args__ = (
        CheckConstraint(
            "btrim(account_holder_name) <> ''",
            name="ck_company_bank_accounts_holder_name_not_blank",
        ),
        CheckConstraint(
            "btrim(bank_name) <> ''",
            name="ck_company_bank_accounts_bank_name_not_blank",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_company_bank_accounts_status",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_bank_accounts_company_id_companies",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["currency_code"],
            ["core.currencies.code"],
            name="fk_company_bank_accounts_currency_code_currencies",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "gl_account_id"],
            ["core.gl_accounts.company_id", "core.gl_accounts.id"],
            name="fk_company_bank_accounts_company_gl_account",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_company_bank_accounts"),
        UniqueConstraint(
            "company_id",
            "id",
            name="uq_company_bank_accounts_company_id_id",
        ),
        Index(
            "uq_company_bank_accounts_active_billing_default",
            "company_id",
            "currency_code",
            unique=True,
            postgresql_where=text(
                "is_default_for_billing = true AND status = 'ACTIVE'"
            ),
        ),
        {"schema": "core"},
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    company_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    account_holder_name: Mapped[str] = mapped_column(String(200), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_number: Mapped[str] = mapped_column(String(64), nullable=False)
    branch_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ifsc: Mapped[str | None] = mapped_column(String(11), nullable=True)
    swift: Mapped[str | None] = mapped_column(String(11), nullable=True)
    iban: Mapped[str | None] = mapped_column(String(34), nullable=True)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    account_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    gl_account_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    is_default_for_billing: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    status: Mapped[CompanyBankAccountStatus] = mapped_column(
        Enum(
            CompanyBankAccountStatus,
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
