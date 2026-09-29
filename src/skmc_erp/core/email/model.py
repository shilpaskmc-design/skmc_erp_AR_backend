from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from skmc_erp.model_base import Base


class EmailProviderConfigStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class EmailProviderConfig(Base):
    __tablename__ = "email_provider_configs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_email_provider_configs_status",
        ),
        ForeignKeyConstraint(
            ["tenant_id"],
            ["core.tenants.id"],
            name="fk_email_provider_configs_tenant_id_tenants",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "company_id"],
            ["core.companies.tenant_id", "core.companies.id"],
            name="fk_email_provider_configs_tenant_company",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_email_provider_configs"),
        {"schema": "core"},
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    company_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    provider_type: Mapped[str] = mapped_column(String(30), nullable=False)
    sender_identity: Mapped[str] = mapped_column(String(320), nullable=False)
    secret_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[EmailProviderConfigStatus] = mapped_column(
        Enum(
            EmailProviderConfigStatus,
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
