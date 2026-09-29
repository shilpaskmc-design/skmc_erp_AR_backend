from uuid import uuid4

import pytest
from pydantic import ValidationError

from skmc_erp.ar.document_presentation.registry import (
    SUPPORTED_BILLING_TEMPLATE_KEYS,
    is_supported_billing_template,
)
from skmc_erp.ar.document_presentation.schema import (
    CompanyDocumentBrandingCreate,
    CompanyDocumentTemplateSelection,
)


def test_code_owned_billing_template_registry_is_small_and_explicit() -> None:
    assert SUPPORTED_BILLING_TEMPLATE_KEYS == {
        "COMPACT_V1",
        "MODERN_V1",
        "STANDARD_V1",
    }
    assert is_supported_billing_template("STANDARD_V1")
    assert not is_supported_billing_template("UNKNOWN_V1")


def test_template_selection_accepts_only_the_company_wide_template_key_field() -> None:
    selection = CompanyDocumentTemplateSelection(
        template_key="  MODERN_V1  "
    )
    assert selection.template_key == "MODERN_V1"

    for extra_field, value in (
        ("document_type", "TI"),
        ("show_logo", True),
        ("show_bank_details", True),
        ("show_signature", True),
        ("show_hsn_sac", True),
        ("show_customer_reference", True),
    ):
        with pytest.raises(ValidationError):
            CompanyDocumentTemplateSelection.model_validate(
                {"template_key": "STANDARD_V1", extra_field: value}
            )


def test_branding_request_is_narrow_and_does_not_expose_presentation_toggles() -> None:
    logo_id = uuid4()
    branding = CompanyDocumentBrandingCreate(
        logo_file_id=logo_id,
        header_text="Header",
    )
    assert branding.logo_file_id == logo_id

    with pytest.raises(ValidationError):
        CompanyDocumentBrandingCreate.model_validate({"show_logo": True})
