from datetime import date

import pytest
from pydantic import ValidationError

from skmc_erp.core.company_gst_registration.schema import CompanyGSTRegistrationUpdate
from skmc_erp.core.tax_reference.schema import CompanyHsnSacCodeCreate, CompanyHsnSacCodeUpdate, CompanyHsnSacTaxRateCreate


def test_hsn_sac_schema_preserves_code_text_without_invented_normalization() -> None:
    value = CompanyHsnSacCodeCreate(
        classification_type="HSN",
        code="0012",
        description="Goods",
    )
    assert value.code == "0012"
    with pytest.raises(ValidationError):
        CompanyHsnSacCodeCreate(
            classification_type="SAC", code="   ", description="Services"
        )


def test_hsn_sac_update_exposes_description_only() -> None:
    assert CompanyHsnSacCodeUpdate(description="Updated").description == "Updated"
    for forbidden in ({"code": "99"}, {"classification_type": "SAC"}):
        with pytest.raises(ValidationError):
            CompanyHsnSacCodeUpdate.model_validate(
                {"description": "Updated", **forbidden}
            )


def test_hsn_sac_rate_schema_validates_inclusive_date_order() -> None:
    with pytest.raises(ValidationError):
        CompanyHsnSacTaxRateCreate(
            tax_rate_id="00000000-0000-0000-0000-000000000001",
            valid_from=date(2026, 2, 1),
            valid_to=date(2026, 1, 31),
        )


def test_gst_update_does_not_expose_stable_identity_fields() -> None:
    CompanyGSTRegistrationUpdate(registered_legal_name="Updated")
    for forbidden in ({"gstin": "09ABCDE1234F1Z5"}, {"subdivision_code": "IN-UP"}):
        with pytest.raises(ValidationError):
            CompanyGSTRegistrationUpdate.model_validate(forbidden)
