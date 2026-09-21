from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
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


class GSTRegistrationTypeStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class CompanyGSTRegistrationStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class GSTRegistrationType(Base):
    __tablename__ = "gst_registration_types"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_gst_registration_types_status",
        ),
        PrimaryKeyConstraint("id", name="pk_gst_registration_types"),
        UniqueConstraint("code", name="uq_gst_registration_types_code"),
        {"schema": "core"},
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[GSTRegistrationTypeStatus] = mapped_column(
        Enum(
            GSTRegistrationTypeStatus,
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


class CompanyGSTRegistration(Base):
    __tablename__ = "company_gst_registrations"
    __table_args__ = (
        CheckConstraint(
            "gstin ~ '^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$'",
            name="ck_company_gst_registrations_gstin_format",
        ),
        CheckConstraint(
            "registered_legal_name IS NULL "
            "OR btrim(registered_legal_name) <> ''",
            name="ck_company_gst_registrations_legal_name_not_blank",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="ck_company_gst_registrations_date_order",
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'INACTIVE')",
            name="ck_company_gst_registrations_status",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_gst_registrations_company_id_companies",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["gst_registration_type_id"],
            ["core.gst_registration_types.id"],
            name="fk_company_gst_registrations_type_id_types",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["subdivision_code"],
            ["core.country_subdivisions.code"],
            name="fk_company_gst_registrations_subdivision_code",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_company_gst_registrations"),
        UniqueConstraint(
            "gstin",
            name="uq_company_gst_registrations_gstin",
        ),
        UniqueConstraint(
            "company_id",
            "id",
            "subdivision_code",
            name="uq_company_gst_registrations_company_id_id_subdivision",
        ),
        Index(
            "ix_company_gst_registrations_company_id",
            "company_id",
        ),
        Index(
            "uq_company_gst_registrations_active_company_subdivision",
            "company_id",
            "subdivision_code",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
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
    gstin: Mapped[str] = mapped_column(String(15), nullable=False)
    registered_legal_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    gst_registration_type_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=True,
    )
    subdivision_code: Mapped[str] = mapped_column(String(10), nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[CompanyGSTRegistrationStatus] = mapped_column(
        Enum(
            CompanyGSTRegistrationStatus,
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
