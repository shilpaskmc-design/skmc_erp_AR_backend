from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from skmc_erp.model_base import Base


class CompanyInvoiceDeliverySettings(Base):
    __tablename__ = "company_invoice_delivery_settings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id"],
            ["core.companies.id"],
            name="fk_company_invoice_delivery_settings_company_id_companies",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["email_provider_config_id"],
            ["core.email_provider_configs.id"],
            name="fk_company_invoice_delivery_settings_email_provider",
            ondelete="NO ACTION",
        ),
        PrimaryKeyConstraint(
            "company_id",
            name="pk_company_invoice_delivery_settings",
        ),
        {"schema": "ar"},
    )

    company_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    automatic_sending_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    email_provider_config_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    sender_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    reply_to_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    default_email_template_key: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    default_cc: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(320)), nullable=True
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
