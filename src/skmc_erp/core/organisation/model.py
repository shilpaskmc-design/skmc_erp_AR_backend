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
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from skmc_erp.model_base import Base


class OrganisationStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class Organisation(Base):
    __tablename__ = "organisations"
    __table_args__ = (
        CheckConstraint(
            "btrim(name) <> ''",
            name="ck_organisations_name_not_blank",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_organisations_status",
        ),
        ForeignKeyConstraint(
            ["tenant_id"],
            ["core.tenants.id"],
            name="fk_organisations_tenant_id_tenants",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_organisations"),
        UniqueConstraint(
            "tenant_id",
            "name",
            name="uq_organisations_tenant_id_name",
        ),
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_organisations_tenant_id_id",
        ),
        {"schema": "core"},
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[OrganisationStatus] = mapped_column(
        Enum(
            OrganisationStatus,
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
