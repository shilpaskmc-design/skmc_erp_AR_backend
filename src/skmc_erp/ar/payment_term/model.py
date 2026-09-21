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
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from skmc_erp.model_base import Base


class PaymentTermType(StrEnum):
    IMMEDIATE = "IMMEDIATE"
    NET_DAYS = "NET_DAYS"


class PaymentTermStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class PaymentTerm(Base):
    __tablename__ = "payment_terms"
    __table_args__ = (
        CheckConstraint(
            "btrim(name) <> ''",
            name="ck_payment_terms_name_not_blank",
        ),
        CheckConstraint(
            "term_type IN ('IMMEDIATE', 'NET_DAYS')",
            name="ck_payment_terms_term_type",
        ),
        CheckConstraint(
            "(term_type = 'IMMEDIATE' AND credit_days = 0) OR "
            "(term_type = 'NET_DAYS' AND credit_days > 0)",
            name="ck_payment_terms_credit_days",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_payment_terms_status",
        ),
        CheckConstraint(
            "NOT is_default OR status = 'ACTIVE'",
            name="ck_payment_terms_default_active",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_payment_terms_company_id_companies",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_payment_terms"),
        UniqueConstraint(
            "company_id",
            "code",
            name="uq_payment_terms_company_id_code",
        ),
        Index(
            "uq_payment_terms_active_default_company",
            "company_id",
            unique=True,
            postgresql_where=text("is_default = true AND status = 'ACTIVE'"),
        ),
        {"schema": "ar"},
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    company_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    term_type: Mapped[PaymentTermType] = mapped_column(
        Enum(
            PaymentTermType,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=20,
        ),
        nullable=False,
    )
    credit_days: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    status: Mapped[PaymentTermStatus] = mapped_column(
        Enum(
            PaymentTermStatus,
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
