from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import ExcludeConstraint

from skmc_erp.ar.accounting.model import RevenueGlMapping, TaxGlAccountMapping
from skmc_erp.ar.compliance.model import CompanyLut
from skmc_erp.ar.delivery.model import CompanyInvoiceDeliverySettings
from skmc_erp.ar.document_presentation.model import CompanyDocumentBranding, CompanyDocumentTemplate
from skmc_erp.ar.reminder.model import ReminderPolicy, ReminderScheduleRule
from skmc_erp.core.access.model import CompanyUserMembership
from skmc_erp.core.accounting.model import CompanyAccountingSettings
from skmc_erp.core.email.model import EmailProviderConfig
from skmc_erp.core.file_storage.model import StoredFile


EXPECTED_COLUMNS = {
    RevenueGlMapping: ["id", "company_id", "service_type_id", "sku_id", "supply_type_code", "company_location_id", "gl_account_id", "valid_from", "valid_to", "status", "created_at", "updated_at"],
    TaxGlAccountMapping: ["id", "company_id", "tax_statutory_code_id", "gl_account_id", "valid_from", "valid_to", "status", "created_at", "updated_at"],
    CompanyAccountingSettings: ["company_id", "default_receivable_gl_account_id", "updated_at", "updated_by"],
    CompanyLut: ["id", "company_id", "gst_registration_id", "financial_year_id", "lut_reference", "valid_from", "valid_to", "status", "created_at", "updated_at"],
    StoredFile: ["id", "company_id", "object_key", "content_hash", "content_type", "size_bytes", "original_filename", "created_at"],
    CompanyDocumentBranding: ["id", "company_id", "logo_file_id", "signature_file_id", "stamp_file_id", "header_text", "footer_text", "status", "created_at", "updated_at"],
    CompanyDocumentTemplate: ["id", "company_id", "document_type", "branding_id", "template_key", "version_no", "show_logo", "show_bank_details", "show_signature", "show_hsn_sac", "show_customer_reference", "status", "created_at", "updated_at"],
    EmailProviderConfig: ["id", "tenant_id", "company_id", "provider_type", "sender_identity", "secret_reference", "status", "created_at", "updated_at"],
    CompanyInvoiceDeliverySettings: ["company_id", "automatic_sending_enabled", "email_provider_config_id", "sender_email", "reply_to_email", "default_email_template_key", "default_cc", "created_at", "updated_at"],
    ReminderPolicy: ["id", "company_id", "enabled", "send_time", "default_template_key", "created_at", "updated_at"],
    ReminderScheduleRule: ["id", "reminder_policy_id", "offset_days", "template_key", "status", "created_at", "updated_at"],
    CompanyUserMembership: ["id", "company_id", "user_subject_id", "status", "created_at", "updated_at"],
}


def _names(model: type, kind: type) -> set[str]:
    return {item.name for item in model.__table__.constraints if isinstance(item, kind)}


def test_all_remaining_foundation_models_have_exact_approved_columns() -> None:
    for model, columns in EXPECTED_COLUMNS.items():
        assert list(model.__table__.columns.keys()) == columns


def test_accounting_configuration_constraints_match_contract() -> None:
    assert _names(RevenueGlMapping, CheckConstraint) == {
        "ck_revenue_gl_mappings_exactly_one_item",
        "ck_revenue_gl_mappings_date_order",
        "ck_revenue_gl_mappings_status",
    }
    assert _names(RevenueGlMapping, ExcludeConstraint) == {
        "ex_revenue_gl_mappings_service_type_overlap",
        "ex_revenue_gl_mappings_sku_overlap",
    }
    assert _names(TaxGlAccountMapping, CheckConstraint) == {
        "ck_tax_gl_account_mappings_date_order", "ck_tax_gl_account_mappings_status"
    }
    assert _names(TaxGlAccountMapping, ExcludeConstraint) == {
        "ex_tax_gl_account_mappings_period_overlap"
    }
    assert len(_names(CompanyAccountingSettings, ForeignKeyConstraint)) == 2


def test_lut_file_and_presentation_constraints_match_contract() -> None:
    assert _names(CompanyLut, CheckConstraint) == {
        "ck_company_luts_date_order", "ck_company_luts_status"
    }
    assert {index.name for index in CompanyLut.__table__.indexes} == {
        "uq_company_luts_active_gst_registration_financial_year"
    }
    assert _names(StoredFile, UniqueConstraint) == {
        "uq_stored_files_object_key", "uq_stored_files_company_id_id"
    }
    assert _names(CompanyDocumentTemplate, CheckConstraint) == {
        "ck_company_document_templates_active_company_wide",
        "ck_company_document_templates_document_type",
        "ck_company_document_templates_version_no_positive",
        "ck_company_document_templates_status",
    }
    assert _names(CompanyDocumentTemplate, UniqueConstraint) == {
        "uq_company_document_templates_company_version"
    }
    assert {index.name for index in CompanyDocumentTemplate.__table__.indexes} == {
        "uq_company_document_templates_active_company"
    }
    assert {
        index.name for index in CompanyDocumentBranding.__table__.indexes
    } == {"uq_company_document_branding_active_company"}
    assert "show_stamp" not in CompanyDocumentTemplate.__table__.columns


def test_delivery_reminder_and_access_constraints_match_contract() -> None:
    assert len(_names(EmailProviderConfig, ForeignKeyConstraint)) == 2
    assert CompanyInvoiceDeliverySettings.__table__.c.automatic_sending_enabled.server_default is not None
    assert _names(ReminderPolicy, UniqueConstraint) == {"uq_reminder_policies_company_id"}
    assert _names(ReminderScheduleRule, UniqueConstraint) == {
        "uq_reminder_schedule_rules_policy_offset"
    }
    assert _names(CompanyUserMembership, UniqueConstraint) == {
        "uq_company_user_memberships_company_user"
    }
    indexes: set[Index] = CompanyUserMembership.__table__.indexes
    assert {index.name for index in indexes} == {
        "idx_company_user_memberships_active_user"
    }


def test_required_fields_and_defaults_match_contract() -> None:
    assert not CompanyLut.__table__.c.status.nullable
    assert CompanyLut.__table__.c.status.server_default is None
    assert not ReminderScheduleRule.__table__.c.offset_days.nullable
    assert ReminderScheduleRule.__table__.c.status.server_default is None
    assert CompanyUserMembership.__table__.c.status.server_default is None
    assert EmailProviderConfig.__table__.c.company_id.nullable
    assert CompanyInvoiceDeliverySettings.__table__.c.email_provider_config_id.nullable
    assert CompanyDocumentTemplate.__table__.c.document_type.nullable
    for column_name in (
        "show_logo",
        "show_bank_details",
        "show_signature",
        "show_hsn_sac",
        "show_customer_reference",
    ):
        assert CompanyDocumentTemplate.__table__.c[column_name].nullable
