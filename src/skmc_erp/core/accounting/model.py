from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    Boolean,
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
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from skmc_erp.model_base import Base


class AccountHierarchyPurpose(StrEnum):
    ACCOUNTING = "ACCOUNTING"


class AccountHierarchyStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class AccountGroupStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class AccountHierarchy(Base):
    __tablename__ = "account_hierarchies"
    __table_args__ = (
        CheckConstraint(
            "btrim(hierarchy_name) <> ''",
            name="ck_account_hierarchies_name_not_blank",
        ),
        CheckConstraint(
            "purpose_code = 'ACCOUNTING'",
            name="ck_account_hierarchies_purpose_code",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_account_hierarchies_status",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_account_hierarchies_company_id_companies",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_account_hierarchies"),
        UniqueConstraint(
            "company_id",
            "id",
            name="uq_account_hierarchies_company_id_id",
        ),
        UniqueConstraint(
            "company_id",
            "purpose_code",
            "hierarchy_name",
            name="uq_account_hierarchies_company_purpose_name",
        ),
        Index(
            "uq_account_hierarchies_active_primary_accounting",
            "company_id",
            unique=True,
            postgresql_where=text(
                "purpose_code = 'ACCOUNTING' "
                "AND status = 'ACTIVE' "
                "AND is_primary = true"
            ),
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
    hierarchy_name: Mapped[str] = mapped_column(String(150), nullable=False)
    purpose_code: Mapped[AccountHierarchyPurpose] = mapped_column(
        Enum(
            AccountHierarchyPurpose,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=30,
        ),
        nullable=False,
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    status: Mapped[AccountHierarchyStatus] = mapped_column(
        Enum(
            AccountHierarchyStatus,
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


class CompanyAccountingSettings(Base):
    __tablename__ = "company_accounting_settings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_accounting_settings_company_id_companies",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "default_receivable_gl_account_id"],
            ["core.gl_accounts.company_id", "core.gl_accounts.id"],
            name="fk_company_accounting_settings_company_receivable_gl",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("company_id", name="pk_company_accounting_settings"),
        {"schema": "core"},
    )

    company_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    default_receivable_gl_account_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_by: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )


class AccountGroup(Base):
    __tablename__ = "account_groups"
    __table_args__ = (
        CheckConstraint(
            "btrim(group_name) <> ''",
            name="ck_account_groups_name_not_blank",
        ),
        CheckConstraint(
            "group_code IS NULL OR btrim(group_code) <> ''",
            name="ck_account_groups_code_not_blank",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_account_groups_status",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_account_groups_company_id_companies",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "hierarchy_id"],
            [
                "core.account_hierarchies.company_id",
                "core.account_hierarchies.id",
            ],
            name="fk_account_groups_company_hierarchy",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_account_groups"),
        UniqueConstraint(
            "company_id",
            "hierarchy_id",
            "group_name",
            name="uq_account_groups_company_hierarchy_name",
        ),
        UniqueConstraint(
            "company_id",
            "hierarchy_id",
            "id",
            name="uq_account_groups_company_hierarchy_id",
        ),
        Index(
            "uq_account_groups_company_hierarchy_code",
            "company_id",
            "hierarchy_id",
            "group_code",
            unique=True,
            postgresql_where=text("group_code IS NOT NULL"),
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
    hierarchy_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    group_name: Mapped[str] = mapped_column(String(200), nullable=False)
    group_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[AccountGroupStatus] = mapped_column(
        Enum(
            AccountGroupStatus,
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


class AccountGroupRelationship(Base):
    __tablename__ = "account_group_relationships"
    __table_args__ = (
        CheckConstraint(
            "child_group_id <> parent_group_id",
            name="ck_account_group_relationships_not_self_parent",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_account_group_relationships_valid_range",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_account_group_relationships_company_id_companies",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "hierarchy_id"],
            [
                "core.account_hierarchies.company_id",
                "core.account_hierarchies.id",
            ],
            name="fk_account_group_relationships_company_hierarchy",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "hierarchy_id", "child_group_id"],
            [
                "core.account_groups.company_id",
                "core.account_groups.hierarchy_id",
                "core.account_groups.id",
            ],
            name="fk_account_group_relationships_child_group",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "hierarchy_id", "parent_group_id"],
            [
                "core.account_groups.company_id",
                "core.account_groups.hierarchy_id",
                "core.account_groups.id",
            ],
            name="fk_account_group_relationships_parent_group",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_account_group_relationships"),
        ExcludeConstraint(
            ("child_group_id", "="),
            (text("daterange(valid_from, valid_to, '[]')"), "&&"),
            name="ex_account_group_relationships_child_period_overlap",
            using="gist",
        ),
        Index(
            "ix_account_group_relationships_company_hierarchy_parent_dates",
            "company_id",
            "hierarchy_id",
            "parent_group_id",
            "valid_from",
            "valid_to",
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
    hierarchy_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    child_group_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    parent_group_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
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


class GlAccountStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class GlAccount(Base):
    __tablename__ = "gl_accounts"
    __table_args__ = (
        CheckConstraint(
            "account_code IS NULL OR btrim(account_code) <> ''",
            name="ck_gl_accounts_code_not_blank",
        ),
        CheckConstraint(
            "btrim(account_name) <> ''",
            name="ck_gl_accounts_name_not_blank",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_gl_accounts_valid_range",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_gl_accounts_status",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_gl_accounts_company_id_companies",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_gl_accounts"),
        UniqueConstraint(
            "company_id",
            "id",
            name="uq_gl_accounts_company_id_id",
        ),
        Index(
            "uq_gl_accounts_company_id_account_code",
            "company_id",
            "account_code",
            unique=True,
            postgresql_where=text("account_code IS NOT NULL"),
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
    account_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    account_name: Mapped[str] = mapped_column(String(200), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[GlAccountStatus] = mapped_column(
        Enum(
            GlAccountStatus,
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


class AccountGroupMapping(Base):
    __tablename__ = "gl_account_group_mappings"
    __table_args__ = (
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_gl_account_group_mappings_valid_range",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_gl_account_group_mappings_company_id_companies",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "hierarchy_id"],
            [
                "core.account_hierarchies.company_id",
                "core.account_hierarchies.id",
            ],
            name="fk_gl_account_group_mappings_company_hierarchy",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "gl_account_id"],
            [
                "core.gl_accounts.company_id",
                "core.gl_accounts.id",
            ],
            name="fk_gl_account_group_mappings_company_gl_account",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "hierarchy_id", "account_group_id"],
            [
                "core.account_groups.company_id",
                "core.account_groups.hierarchy_id",
                "core.account_groups.id",
            ],
            name="fk_gl_account_group_mappings_company_hierarchy_group",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_gl_account_group_mappings"),
        ExcludeConstraint(
            ("gl_account_id", "="),
            ("hierarchy_id", "="),
            (text("daterange(valid_from, valid_to, '[]')"), "&&"),
            name="ex_gl_account_group_mappings_gl_hierarchy_period_overlap",
            using="gist",
        ),
        Index(
            "ix_gl_account_group_mappings_company_hierarchy_group_dates",
            "company_id",
            "hierarchy_id",
            "account_group_id",
            "valid_from",
            "valid_to",
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
    hierarchy_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    gl_account_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    account_group_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
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
