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


class CompanyIdentifierTypeStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class CompanyIdentifierStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class IdentifierRequirementLevel(StrEnum):
    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"


class CompanyIdentifierType(Base):
    __tablename__ = "company_identifier_types"
    __table_args__ = (
        CheckConstraint(
            "country_code ~ '^[A-Z]{2}$'",
            name="ck_company_identifier_types_country_code_format",
        ),
        CheckConstraint(
            "code ~ '^[A-Z0-9]+(_[A-Z0-9]+)*$'",
            name="ck_company_identifier_types_code_format",
        ),
        CheckConstraint(
            "btrim(name) <> ''",
            name="ck_company_identifier_types_name_not_blank",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_company_identifier_types_status",
        ),
        ForeignKeyConstraint(
            ["country_code"],
            ["core.countries.code"],
            name="fk_company_identifier_types_country_code_countries",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_company_identifier_types"),
        UniqueConstraint(
            "country_code",
            "code",
            name="uq_company_identifier_types_country_code_code",
        ),
        {"schema": "core"},
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[CompanyIdentifierTypeStatus] = mapped_column(
        Enum(
            CompanyIdentifierTypeStatus,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=20,
        ),
        nullable=False,
    )


class CompanyIdentifier(Base):
    __tablename__ = "company_identifiers"
    __table_args__ = (
        CheckConstraint(
            "btrim(identifier_value) <> ''",
            name="ck_company_identifiers_value_not_blank",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_company_identifiers_status",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_identifiers_company_id_companies",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["identifier_type_id"],
            ["core.company_identifier_types.id"],
            name="fk_company_identifiers_type_id_types",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_company_identifiers"),
        UniqueConstraint(
            "company_id",
            "identifier_type_id",
            name="uq_company_identifiers_company_id_type_id",
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
    identifier_type_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    identifier_value: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[CompanyIdentifierStatus] = mapped_column(
        Enum(
            CompanyIdentifierStatus,
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


class EntityTypeIdentifierRule(Base):
    __tablename__ = "entity_type_identifier_rules"
    __table_args__ = (
        CheckConstraint(
            "requirement_level IN ('REQUIRED', 'OPTIONAL')",
            name="ck_entity_type_identifier_rules_requirement_level",
        ),
        ForeignKeyConstraint(
            ["entity_type_id"],
            ["core.entity_types.id"],
            name="fk_entity_type_identifier_rules_entity_type_id_entity_types",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["identifier_type_id"],
            ["core.company_identifier_types.id"],
            name="fk_entity_type_identifier_rules_identifier_type_id_types",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_entity_type_identifier_rules"),
        UniqueConstraint(
            "entity_type_id",
            "identifier_type_id",
            name="uq_entity_type_identifier_rules_entity_type_id_type_id",
        ),
        {"schema": "core"},
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    entity_type_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    identifier_type_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    requirement_level: Mapped[IdentifierRequirementLevel] = mapped_column(
        Enum(
            IdentifierRequirementLevel,
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
