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
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from skmc_erp.model_base import Base


class CostCenterStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class TeamStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class CostCenterLocation(Base):
    __tablename__ = "cost_center_locations"
    __table_args__ = (
        CheckConstraint(
            "btrim(name) <> ''",
            name="ck_cost_center_locations_name_not_blank",
        ),
        CheckConstraint(
            "code IS NULL OR btrim(code) <> ''",
            name="ck_cost_center_locations_code_not_blank",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_cost_center_locations_status",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_cost_center_locations_company_id_companies",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_cost_center_locations"),
        UniqueConstraint(
            "company_id",
            "name",
            name="uq_cost_center_locations_company_id_name",
        ),
        UniqueConstraint(
            "company_id",
            "id",
            name="uq_cost_center_locations_company_id_id",
        ),
        Index(
            "uq_cost_center_locations_company_id_code",
            "company_id",
            "code",
            unique=True,
            postgresql_where=text("code IS NOT NULL"),
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
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[CostCenterStatus] = mapped_column(
        Enum(
            CostCenterStatus,
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


class CostCenterBusinessSegment(Base):
    __tablename__ = "cost_center_business_segments"
    __table_args__ = (
        CheckConstraint(
            "btrim(name) <> ''",
            name="ck_cost_center_business_segments_name_not_blank",
        ),
        CheckConstraint(
            "code IS NULL OR btrim(code) <> ''",
            name="ck_cost_center_business_segments_code_not_blank",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_cost_center_business_segments_status",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_cost_center_business_segments_company_id_companies",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_cost_center_business_segments"),
        UniqueConstraint(
            "company_id",
            "name",
            name="uq_cost_center_business_segments_company_id_name",
        ),
        UniqueConstraint(
            "company_id",
            "id",
            name="uq_cost_center_business_segments_company_id_id",
        ),
        Index(
            "uq_cost_center_business_segments_company_id_code",
            "company_id",
            "code",
            unique=True,
            postgresql_where=text("code IS NOT NULL"),
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
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[CostCenterStatus] = mapped_column(
        Enum(
            CostCenterStatus,
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


class CostCenterTeam(Base):
    __tablename__ = "cost_center_teams"
    __table_args__ = (
        CheckConstraint(
            "btrim(name) <> ''",
            name="ck_cost_center_teams_name_not_blank",
        ),
        CheckConstraint(
            "code IS NULL OR btrim(code) <> ''",
            name="ck_cost_center_teams_code_not_blank",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_cost_center_teams_status",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_cost_center_teams_company_id_companies",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_cost_center_teams"),
        UniqueConstraint(
            "company_id",
            "name",
            name="uq_cost_center_teams_company_id_name",
        ),
        UniqueConstraint(
            "company_id",
            "id",
            name="uq_cost_center_teams_company_id_id",
        ),
        Index(
            "uq_cost_center_teams_company_id_code",
            "company_id",
            "code",
            unique=True,
            postgresql_where=text("code IS NOT NULL"),
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
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[CostCenterStatus] = mapped_column(
        Enum(
            CostCenterStatus,
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


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (
        CheckConstraint("btrim(name) <> ''", name="ck_teams_name_not_blank"),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_teams_status",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_teams_company_id_companies",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "cost_center_team_id"],
            ["core.cost_center_teams.company_id", "core.cost_center_teams.id"],
            name="fk_teams_company_cost_center_team",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_teams"),
        UniqueConstraint("company_id", "name", name="uq_teams_company_id_name"),
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
    cost_center_team_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[TeamStatus] = mapped_column(
        Enum(
            TeamStatus,
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


class CompanyCostCenterSettings(Base):
    __tablename__ = "company_cost_center_settings"
    __table_args__ = (
        CheckConstraint(
            "cost_center_reporting_enabled OR "
            "(NOT business_segment_enabled AND NOT team_enabled "
            "AND NOT location_enabled)",
            name="ck_company_cost_center_settings_disabled_bases",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_cost_center_settings_company_id_companies",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint(
            "company_id",
            name="pk_company_cost_center_settings",
        ),
        {"schema": "core"},
    )

    company_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True
    )
    cost_center_reporting_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    business_segment_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    team_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    location_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
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
