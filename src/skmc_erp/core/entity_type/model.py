from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Enum,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from skmc_erp.model_base import Base


class EntityTypeStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class EntityType(Base):
    __tablename__ = "entity_types"
    __table_args__ = (
        CheckConstraint(
            "country_code ~ '^[A-Z]{2}$'",
            name="ck_entity_types_country_code_format",
        ),
        CheckConstraint(
            "btrim(code) <> ''",
            name="ck_entity_types_code_not_blank",
        ),
        CheckConstraint(
            r"code ~ '^[A-Z0-9]+(?\:_[A-Z0-9]+)*$'",
            name="ck_entity_types_code_format",
        ),
        CheckConstraint(
            "btrim(name) <> ''",
            name="ck_entity_types_name_not_blank",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_entity_types_status",
        ),
        PrimaryKeyConstraint("id", name="pk_entity_types"),
        UniqueConstraint(
            "country_code",
            "code",
            name="uq_entity_types_country_code_code",
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
    status: Mapped[EntityTypeStatus] = mapped_column(
        Enum(
            EntityTypeStatus,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=20,
        ),
        nullable=False,
    )
