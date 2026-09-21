from uuid import uuid4

import pytest
from pydantic import ValidationError

from skmc_erp.core.company.model import CompanyBusinessNature
from skmc_erp.core.company.schema import CompanyCreate


def test_company_create_accepts_and_normalizes_approved_input() -> None:
    company = CompanyCreate(
        legal_name="  SKMC Example Private Limited  ",
        display_name="  SKMC Example  ",
        country_code="IN",
        base_currency_code="INR",
        base_timezone="Asia/Kolkata",
        business_nature="SERVICES",
    )

    assert company.legal_name == "SKMC Example Private Limited"
    assert company.display_name == "SKMC Example"
    assert company.business_nature is CompanyBusinessNature.SERVICES


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("tenant_id", str(uuid4())),
        ("company_code", "COM000001"),
        ("status", "ACTIVE"),
        ("id", str(uuid4())),
        ("created_at", "2026-01-01T00:00:00Z"),
        ("updated_at", "2026-01-01T00:00:00Z"),
    ],
)
def test_company_create_rejects_system_controlled_fields(
    field_name: str,
    value: str,
) -> None:
    with pytest.raises(ValidationError):
        CompanyCreate.model_validate(
            {"legal_name": "Example Company", field_name: value}
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"legal_name": "   "},
        {"legal_name": "Example", "display_name": "   "},
        {"legal_name": "Example", "email": "   "},
        {"legal_name": "Example", "phone": "   "},
        {"legal_name": "Example", "website": "   "},
        {"legal_name": "Example", "country_code": "in"},
        {"legal_name": "Example", "country_code": "IND"},
        {"legal_name": "Example", "base_currency_code": "inr"},
        {"legal_name": "Example", "base_currency_code": "IN"},
        {"legal_name": "Example", "base_timezone": "Not/A-Timezone"},
    ],
)
def test_company_create_rejects_invalid_values(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        CompanyCreate.model_validate(payload)
