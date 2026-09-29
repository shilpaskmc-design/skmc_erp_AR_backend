from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKeyConstraint, Index, PrimaryKeyConstraint, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from skmc_erp.model_base import Base


class CompanyUserMembershipStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class CompanyUserMembership(Base):
    __tablename__ = "company_user_memberships"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_company_user_memberships_status"),
        ForeignKeyConstraint(["company_id"], ["core.companies.id"], name="fk_company_user_memberships_company_id_companies", ondelete="NO ACTION"),
        PrimaryKeyConstraint("id", name="pk_company_user_memberships"),
        UniqueConstraint("company_id", "user_subject_id", name="uq_company_user_memberships_company_user"),
        Index("idx_company_user_memberships_active_user", "user_subject_id", "company_id", postgresql_where=text("status = 'ACTIVE'")),
        {"schema": "core"},
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    user_subject_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[CompanyUserMembershipStatus] = mapped_column(
        Enum(CompanyUserMembershipStatus, native_enum=False, create_constraint=False, validate_strings=True, length=20), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
