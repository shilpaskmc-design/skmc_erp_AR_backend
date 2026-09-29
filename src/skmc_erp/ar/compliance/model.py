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
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from skmc_erp.model_base import Base


class CompanyLutStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class CompanyLut(Base):
    __tablename__ = "company_luts"
    __table_args__ = (
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_company_luts_date_order",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_company_luts_status",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_luts_company_id_companies",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "gst_registration_id"],
            [
                "core.company_gst_registrations.company_id",
                "core.company_gst_registrations.id",
            ],
            name="fk_company_luts_company_gst_registration",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "financial_year_id"],
            ["core.financial_years.company_id", "core.financial_years.id"],
            name="fk_company_luts_company_financial_year",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_company_luts"),
        Index(
            "uq_company_luts_active_gst_registration_financial_year",
            "gst_registration_id",
            "financial_year_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
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
    gst_registration_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    financial_year_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    lut_reference: Mapped[str] = mapped_column(String(100), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[CompanyLutStatus] = mapped_column(
        Enum(
            CompanyLutStatus,
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
