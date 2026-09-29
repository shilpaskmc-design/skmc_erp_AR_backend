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
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from skmc_erp.model_base import Base


class DocumentPresentationStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class CompanyDocumentBranding(Base):
    __tablename__ = "company_document_branding"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_company_document_branding_status",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_document_branding_company_id_companies",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "logo_file_id"],
            ["core.stored_files.company_id", "core.stored_files.id"],
            name="fk_company_document_branding_company_logo_file",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "signature_file_id"],
            ["core.stored_files.company_id", "core.stored_files.id"],
            name="fk_company_document_branding_company_signature_file",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "stamp_file_id"],
            ["core.stored_files.company_id", "core.stored_files.id"],
            name="fk_company_document_branding_company_stamp_file",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_company_document_branding"),
        UniqueConstraint(
            "company_id",
            "id",
            name="uq_company_document_branding_company_id_id",
        ),
        Index(
            "uq_company_document_branding_active_company",
            "company_id",
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
    logo_file_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    signature_file_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    stamp_file_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    header_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    footer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[DocumentPresentationStatus] = mapped_column(
        Enum(
            DocumentPresentationStatus,
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


class CompanyDocumentTemplate(Base):
    __tablename__ = "company_document_templates"
    __table_args__ = (
        CheckConstraint(
            "document_type IN ('PI', 'TI', 'CN', 'DN')",
            name="ck_company_document_templates_document_type",
        ),
        CheckConstraint(
            "version_no >= 1",
            name="ck_company_document_templates_version_no_positive",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_company_document_templates_status",
        ),
        CheckConstraint(
            "status <> 'ACTIVE' OR document_type IS NULL",
            name="ck_company_document_templates_active_company_wide",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_document_templates_company_id_companies",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "branding_id"],
            [
                "ar.company_document_branding.company_id",
                "ar.company_document_branding.id",
            ],
            name="fk_company_document_templates_company_branding",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_company_document_templates"),
        UniqueConstraint(
            "company_id",
            "version_no",
            name="uq_company_document_templates_company_version",
        ),
        Index(
            "uq_company_document_templates_active_company",
            "company_id",
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
    document_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    branding_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    template_key: Mapped[str] = mapped_column(String(100), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    show_logo: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    show_bank_details: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    show_signature: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    show_hsn_sac: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    show_customer_reference: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True
    )
    status: Mapped[DocumentPresentationStatus] = mapped_column(
        Enum(
            DocumentPresentationStatus,
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
