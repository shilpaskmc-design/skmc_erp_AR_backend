from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from skmc_erp.model_base import Base


class StoredFile(Base):
    __tablename__ = "stored_files"
    __table_args__ = (
        CheckConstraint(
            "size_bytes >= 0",
            name="ck_stored_files_size_bytes_nonnegative",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_stored_files_company_id_companies",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_stored_files"),
        UniqueConstraint("object_key", name="uq_stored_files_object_key"),
        UniqueConstraint(
            "company_id",
            "id",
            name="uq_stored_files_company_id_id",
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
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    original_filename: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
