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
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from skmc_erp.model_base import Base


class CompanyLocationStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class CompanyLocation(Base):
    __tablename__ = "company_locations"
    __table_args__ = (
        CheckConstraint(
            "location_code ~ '^[A-Z0-9][A-Z0-9_-]{0,49}$'",
            name="ck_company_locations_code_format",
        ),
        CheckConstraint(
            "btrim(location_name) <> ''",
            name="ck_company_locations_name_not_blank",
        ),
        CheckConstraint(
            "btrim(address_line_1) <> ''",
            name="ck_company_locations_address_line_1_not_blank",
        ),
        CheckConstraint(
            "address_line_2 IS NULL OR btrim(address_line_2) <> ''",
            name="ck_company_locations_address_line_2_not_blank",
        ),
        CheckConstraint(
            "btrim(city) <> ''",
            name="ck_company_locations_city_not_blank",
        ),
        CheckConstraint(
            "district IS NULL OR btrim(district) <> ''",
            name="ck_company_locations_district_not_blank",
        ),
        CheckConstraint(
            "postal_code IS NULL OR btrim(postal_code) <> ''",
            name="ck_company_locations_postal_code_not_blank",
        ),
        CheckConstraint(
            "other_purpose IS NULL OR btrim(other_purpose) <> ''",
            name="ck_company_locations_other_purpose_not_blank",
        ),
        CheckConstraint(
            "is_registered_office OR is_corporate_office OR is_branch "
            "OR is_billing_office OR is_warehouse "
            "OR other_purpose IS NOT NULL",
            name="ck_company_locations_at_least_one_purpose",
        ),
        CheckConstraint(
            "country_code ~ '^[A-Z]{2}$'",
            name="ck_company_locations_country_code_format",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_company_locations_status",
        ),
        CheckConstraint(
            "gst_registration_id IS NULL OR subdivision_code IS NOT NULL",
            name="ck_company_locations_gst_requires_subdivision",
        ),
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_locations_company_id_companies",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["country_code"],
            ["core.countries.code"],
            name="fk_company_locations_country_code_countries",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["country_code", "subdivision_code"],
            [
                "core.country_subdivisions.country_code",
                "core.country_subdivisions.code",
            ],
            name="fk_company_locations_country_subdivision",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "gst_registration_id", "subdivision_code"],
            [
                "core.company_gst_registrations.company_id",
                "core.company_gst_registrations.id",
                "core.company_gst_registrations.subdivision_code",
            ],
            name="fk_company_locations_gst_registration_jurisdiction",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["company_id", "cost_center_location_id"],
            [
                "core.cost_center_locations.company_id",
                "core.cost_center_locations.id",
            ],
            name="fk_company_locations_company_cost_center_location",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_company_locations"),
        Index(
            "uq_company_locations_company_id_location_code",
            "company_id",
            "location_code",
            unique=True,
        ),
        Index(
            "ix_company_locations_company_id",
            "company_id",
        ),
        Index(
            "ix_company_locations_gst_registration_id",
            "gst_registration_id",
        ),
        Index(
            "uq_company_locations_active_registered_office",
            "company_id",
            unique=True,
            postgresql_where=text(
                "status = 'ACTIVE' AND is_registered_office"
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
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )
    location_code: Mapped[str] = mapped_column(String(50), nullable=False)
    location_name: Mapped[str] = mapped_column(String(150), nullable=False)
    address_line_1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line_2: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subdivision_code: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    gst_registration_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=True,
    )
    cost_center_location_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=True,
    )
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_registered_office: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    is_corporate_office: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    is_branch: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    is_billing_office: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    is_warehouse: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    other_purpose: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )
    status: Mapped[CompanyLocationStatus] = mapped_column(
        Enum(
            CompanyLocationStatus,
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


class CompanyLocationVersion(Base):
    __tablename__ = "company_location_versions"
    __table_args__ = (
        CheckConstraint(
            "btrim(address_line_1) <> ''",
            name="ck_company_location_versions_address_line_1_not_blank",
        ),
        CheckConstraint(
            "address_line_2 IS NULL OR btrim(address_line_2) <> ''",
            name="ck_company_location_versions_address_line_2_not_blank",
        ),
        CheckConstraint(
            "btrim(city) <> ''",
            name="ck_company_location_versions_city_not_blank",
        ),
        CheckConstraint(
            "district IS NULL OR btrim(district) <> ''",
            name="ck_company_location_versions_district_not_blank",
        ),
        CheckConstraint(
            "postal_code IS NULL OR btrim(postal_code) <> ''",
            name="ck_company_location_versions_postal_code_not_blank",
        ),
        CheckConstraint(
            "country_code ~ '^[A-Z]{2}$'",
            name="ck_company_location_versions_country_code_format",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_company_location_versions_date_order",
        ),
        ForeignKeyConstraint(
            ["company_location_id"],
            ["core.company_locations.id"],
            name="fk_company_location_versions_location_id_locations",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["country_code"],
            ["core.countries.code"],
            name="fk_company_location_versions_country_code_countries",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["country_code", "subdivision_code"],
            [
                "core.country_subdivisions.country_code",
                "core.country_subdivisions.code",
            ],
            name="fk_company_location_versions_country_subdivision",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint("id", name="pk_company_location_versions"),
        ExcludeConstraint(
            ("company_location_id", "="),
            (text("daterange(valid_from, valid_to, '[]')"), "&&"),
            name="ex_company_location_versions_location_effective_range",
            using="gist",
        ),
        Index(
            "ix_company_location_versions_location_valid_from",
            "company_location_id",
            "valid_from",
        ),
        Index(
            "uq_company_location_versions_open_location",
            "company_location_id",
            unique=True,
            postgresql_where=text("valid_to IS NULL"),
        ),
        {"schema": "core"},
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    company_location_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )
    address_line_1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line_2: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subdivision_code: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
