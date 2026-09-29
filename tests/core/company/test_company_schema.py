from uuid import uuid4

import pytest
from pydantic import ValidationError

from skmc_erp.core.company.model import CompanyBusinessNature
from skmc_erp.core.company.schema import (
    CompanyCreate,
    CompanyUpdate,
    validate_phone,
)


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


def test_company_update_accepts_approved_profile_fields() -> None:
    company = CompanyUpdate.model_validate(
        {
            "legal_name": "  SKMC Legal Updated  ",
            "display_name": "  SKMC Updated  ",
            "email": "  finance@example.test  ",
            "phone": "  +91 120 555 0100  ",
            "website": "  https://example.test  ",
            "base_timezone": "Asia/Kolkata",
            "business_nature": "BOTH",
        }
    )

    assert company.legal_name == "SKMC Legal Updated"
    assert company.display_name == "SKMC Updated"
    assert company.email == "finance@example.test"
    assert company.business_nature is CompanyBusinessNature.BOTH


@pytest.mark.parametrize(
    "field_name",
    [
        "id",
        "tenant_id",
        "company_code",
        "organisation_id",
        "entity_type_id",
        "country_code",
        "base_currency_code",
        "status",
        "created_at",
        "updated_at",
    ],
)
def test_company_update_rejects_unapproved_fields(field_name: str) -> None:
    with pytest.raises(ValidationError):
        CompanyUpdate.model_validate({field_name: "not-allowed"})


def test_company_update_rejects_invalid_timezone() -> None:
    with pytest.raises(ValidationError):
        CompanyUpdate.model_validate({"base_timezone": "Not/A-Timezone"})


@pytest.mark.parametrize("legal_name", [None, "", "   "])
def test_company_update_rejects_invalid_legal_name(
    legal_name: str | None,
) -> None:
    with pytest.raises(ValidationError):
        CompanyUpdate.model_validate({"legal_name": legal_name})


@pytest.mark.parametrize(
    "email",
    [
        "accounts@example.com",
        "  accounts@example.com  ",
        "user.name+tag@domain.co.uk",
    ],
)
def test_company_email_valid_create_and_update(email: str) -> None:
    c_create = CompanyCreate(legal_name="Test Co", email=email)
    assert c_create.email == email.strip()

    c_update = CompanyUpdate(email=email)
    assert c_update.email == email.strip()


@pytest.mark.parametrize(
    "email",
    [
        "abcxyz",
        "invalid",
        "@example.com",
        "user@.com",
        "user@domain",
    ],
)
def test_company_email_invalid_create_and_update(email: str) -> None:
    with pytest.raises(ValidationError):
        CompanyCreate(legal_name="Test Co", email=email)

    with pytest.raises(ValidationError):
        CompanyUpdate(email=email)


@pytest.mark.parametrize(
    "website",
    [
        "https://www.example.com",
        "http://example.com",
        "  https://example.com/sub  ",
    ],
)
def test_company_website_valid_create_and_update(website: str) -> None:
    c_create = CompanyCreate(legal_name="Test Co", website=website)
    assert c_create.website == website.strip()

    c_update = CompanyUpdate(website=website)
    assert c_update.website == website.strip()


@pytest.mark.parametrize(
    "website",
    [
        "not-a-url",
        "abcxyz",
        "ftp://example.com",
        "ws://example.com",
        "https://",
    ],
)
def test_company_website_invalid_create_and_update(website: str) -> None:
    with pytest.raises(ValidationError):
        CompanyCreate(legal_name="Test Co", website=website)

    with pytest.raises(ValidationError):
        CompanyUpdate(website=website)


@pytest.mark.parametrize(
    ("input_phone", "expected_e164"),
    [
        ("+91 98912 55499", "+919891255499"),
        ("+91-98912-55499", "+919891255499"),
        ("+1 (415) 555-2671", "+14155552671"),
    ],
)
def test_company_phone_valid_create_and_update(
    input_phone: str, expected_e164: str
) -> None:
    c_create = CompanyCreate(legal_name="Test Co", phone=input_phone)
    assert c_create.phone == expected_e164

    c_update = CompanyUpdate(phone=input_phone)
    assert c_update.phone == expected_e164


def test_company_phone_country_aware_create() -> None:
    c_create = CompanyCreate(
        legal_name="Test Co", country_code="IN", phone="9891255499"
    )
    assert c_create.phone == "+919891255499"





@pytest.mark.parametrize(
    "phone",
    [
        "abc",
        "---",
        "phone-number",
        "12345",
        "+91 123",
    ],
)
def test_company_phone_invalid_create_and_service_update(phone: str) -> None:
    # 1. CompanyCreate schema validates with country_code
    with pytest.raises(ValidationError):
        CompanyCreate(legal_name="Test Co", country_code="IN", phone=phone)

    # 2. Service-layer normalization (used by update_company) rejects invalid input
    with pytest.raises(ValueError):
        validate_phone(phone, "IN")


@pytest.mark.parametrize(
    ("create_input", "patch_input", "country", "expected_e164"),
    [
        ("9891255499", "9891255499", "IN", "+919891255499"),
        ("+91 98912 55499", "+91 98912 55499", "IN", "+919891255499"),
        ("+1 (415) 555-2671", "+1 (415) 555-2671", "IN", "+14155552671"),
    ],
)
def test_create_and_patch_produce_identical_phone_normalization(
    create_input: str, patch_input: str, country: str, expected_e164: str
) -> None:
    c_create = CompanyCreate(
        legal_name="Test Co", country_code=country, phone=create_input
    )
    assert c_create.phone == expected_e164

    c_update = CompanyUpdate(phone=patch_input)
    normalized_patch_phone = validate_phone(c_update.phone, country)
    assert normalized_patch_phone == expected_e164
    assert c_create.phone == normalized_patch_phone
