from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, Enum, PrimaryKeyConstraint, String, text
from sqlalchemy.orm import Mapped, mapped_column

from skmc_erp.model_base import Base


class UomStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class Uom(Base):
    __tablename__ = "uoms"
    __table_args__ = (
        CheckConstraint(
            "code ~ '^[A-Z0-9_]{1,20}$'",
            name="ck_uoms_code_format",
        ),
        CheckConstraint(
            "btrim(name) <> ''",
            name="ck_uoms_name_not_blank",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_uoms_status",
        ),
        PrimaryKeyConstraint("code", name="pk_uoms"),
        {"schema": "core"},
    )

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    uqc_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[UomStatus] = mapped_column(
        Enum(
            UomStatus,
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
