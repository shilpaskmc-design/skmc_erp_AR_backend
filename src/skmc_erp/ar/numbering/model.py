from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Integer,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from skmc_erp.model_base import Base


class DocumentType(StrEnum):
    PI = "PI"
    TI = "TI"
    CN = "CN"
    DN = "DN"


class DocumentSequenceStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class DocumentSequence(Base):
    __tablename__ = "document_sequences"
    __table_args__ = (
        CheckConstraint(
            "document_type IN ('PI', 'TI', 'CN', 'DN')",
            name="ck_document_sequences_document_type",
        ),
        CheckConstraint(
            "start_number >= 1",
            name="ck_document_sequences_start_number",
        ),
        CheckConstraint(
            "next_number >= start_number",
            name="ck_document_sequences_next_number",
        ),
        CheckConstraint(
            "padding >= 1",
            name="ck_document_sequences_padding",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_document_sequences_status",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_document_sequences_company_id_companies",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "financial_year_id"],
            ["core.financial_years.company_id", "core.financial_years.id"],
            name="fk_document_sequences_company_financial_year",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_document_sequences"),
        UniqueConstraint(
            "company_id",
            "financial_year_id",
            "document_type",
            "series_name",
            name="uq_document_sequences_company_fy_type_name",
        ),
        {"schema": "ar"},
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
    )
    company_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )
    financial_year_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(
            DocumentType,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=10,
        ),
        nullable=False,
    )
    series_name: Mapped[str] = mapped_column(String(100), nullable=False)
    format: Mapped[str] = mapped_column(String(255), nullable=False)
    prefix: Mapped[str | None] = mapped_column(String(50), nullable=True)
    start_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    next_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    padding: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[DocumentSequenceStatus] = mapped_column(
        Enum(
            DocumentSequenceStatus,
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
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class DocumentSequenceCondition(Base):
    __tablename__ = "document_sequence_conditions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["document_sequence_id"],
            ["ar.document_sequences.id"],
            name="fk_document_sequence_conditions_sequence_id_sequences",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_document_sequence_conditions"),
        {"schema": "ar"},
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
    )
    document_sequence_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )
    condition_type: Mapped[str] = mapped_column(String(40), nullable=False)
    operator: Mapped[str] = mapped_column(String(20), nullable=False)
    condition_value: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
