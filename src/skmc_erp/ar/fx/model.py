from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from skmc_erp.model_base import Base


class FXPolicyPurpose(StrEnum):
    BILLING = "BILLING"
    RECEIPT = "RECEIPT"
    REPORTING = "REPORTING"


class FXPolicyRateType(StrEnum):
    CORPORATE = "CORPORATE"
    SPOT = "SPOT"


class FXPolicyStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class FXPolicy(Base):
    __tablename__ = "fx_policies"
    __table_args__ = (
        CheckConstraint(
            "purpose IN ('BILLING', 'RECEIPT', 'REPORTING')",
            name="ck_fx_policies_purpose",
        ),
        CheckConstraint(
            "default_rate_type IN ('CORPORATE', 'SPOT')",
            name="ck_fx_policies_default_rate_type",
        ),
        CheckConstraint(
            "NOT reason_required_for_override OR allow_user_fixed_override",
            name="ck_fx_policies_override_reason_requires_override",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_fx_policies_status",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_fx_policies_company_id_companies",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_fx_policies"),
        UniqueConstraint(
            "company_id",
            "purpose",
            name="uq_fx_policies_company_id_purpose",
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
    purpose: Mapped[FXPolicyPurpose] = mapped_column(
        Enum(
            FXPolicyPurpose,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=20,
        ),
        nullable=False,
    )
    default_rate_type: Mapped[FXPolicyRateType] = mapped_column(
        Enum(
            FXPolicyRateType,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=20,
        ),
        nullable=False,
    )
    allow_user_fixed_override: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    reason_required_for_override: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    status: Mapped[FXPolicyStatus] = mapped_column(
        Enum(
            FXPolicyStatus,
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
