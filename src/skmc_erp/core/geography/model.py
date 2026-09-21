from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
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


class CountryStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class Country(Base):
    __tablename__ = "countries"
    __table_args__ = (
        CheckConstraint(
            "code ~ '^[A-Z]{2}$'",
            name="ck_countries_code_format",
        ),
        CheckConstraint(
            "btrim(name) <> ''",
            name="ck_countries_name_not_blank",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_countries_status",
        ),
        PrimaryKeyConstraint("code", name="pk_countries"),
        {"schema": "core"},
    )

    code: Mapped[str] = mapped_column(String(2), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[CountryStatus] = mapped_column(
        Enum(
            CountryStatus,
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


class CountrySubdivisionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class CountrySubdivision(Base):
    __tablename__ = "country_subdivisions"
    __table_args__ = (
        CheckConstraint(
            "code ~ '^[A-Z]{2}-[A-Z0-9]{1,3}$'",
            name="ck_country_subdivisions_code_format",
        ),
        CheckConstraint(
            "left(code, 2) = country_code",
            name="ck_country_subdivisions_country_prefix",
        ),
        CheckConstraint(
            "btrim(name) <> ''",
            name="ck_country_subdivisions_name_not_blank",
        ),
        CheckConstraint(
            "subdivision_type ~ '^[A-Z]+(_[A-Z]+)*$'",
            name="ck_country_subdivisions_type_format",
        ),
        CheckConstraint(
            "gst_state_code IS NULL OR gst_state_code ~ '^[0-9]{2}$'",
            name="ck_country_subdivisions_gst_state_code_format",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_country_subdivisions_status",
        ),
        ForeignKeyConstraint(
            ["country_code"],
            ["core.countries.code"],
            name="fk_country_subdivisions_country_code_countries",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_country_subdivisions"),
        UniqueConstraint(
            "code",
            name="uq_country_subdivisions_code",
        ),
        UniqueConstraint(
            "country_code",
            "code",
            name="uq_country_subdivisions_country_code_code",
        ),
        Index(
            "ix_country_subdivisions_country_code",
            "country_code",
        ),
        Index(
            "uq_country_subdivisions_country_gst_state_code",
            "country_code",
            "gst_state_code",
            unique=True,
            postgresql_where=text("gst_state_code IS NOT NULL"),
        ),
        {"schema": "core"},
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    code: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    subdivision_type: Mapped[str] = mapped_column(String(50), nullable=False)
    gst_state_code: Mapped[str | None] = mapped_column(
        String(2),
        nullable=True,
    )
    status: Mapped[CountrySubdivisionStatus] = mapped_column(
        Enum(
            CountrySubdivisionStatus,
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
