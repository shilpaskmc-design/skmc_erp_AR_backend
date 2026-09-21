from uuid import uuid4

import pytest
from pydantic import ValidationError

from skmc_erp.core.company_location.schema import CompanyLocationCreate


def _valid_location(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "location_name": "Noida Office",
        "address_line_1": "Sector 62",
        "city": "Noida",
        "country_code": "IN",
        "is_branch": True,
    }
    payload.update(overrides)
    return payload


def test_company_location_create_requires_location_name() -> None:
    payload = _valid_location()
    del payload["location_name"]

    with pytest.raises(ValidationError):
        CompanyLocationCreate.model_validate(payload)


@pytest.mark.parametrize(
    "purposes",
    [
        {"is_registered_office": True, "is_corporate_office": True},
        {"is_corporate_office": True, "is_billing_office": True},
        {"is_warehouse": True},
        {"other_purpose": "Research Centre"},
    ],
)
def test_company_location_create_accepts_approved_purpose_combinations(
    purposes: dict[str, object],
) -> None:
    location = CompanyLocationCreate.model_validate(
        _valid_location(is_branch=False, **purposes)
    )

    assert location.location_name == "Noida Office"


@pytest.mark.parametrize(
    "payload",
    [
        _valid_location(location_name="   "),
        _valid_location(address_line_1="   "),
        _valid_location(address_line_2="   "),
        _valid_location(city="   "),
        _valid_location(country_code="in"),
        _valid_location(country_code="IND"),
        _valid_location(is_branch=False),
        _valid_location(is_branch=False, other_purpose="   "),
    ],
)
def test_company_location_create_rejects_invalid_input(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        CompanyLocationCreate.model_validate(payload)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("id", str(uuid4())),
        ("company_id", str(uuid4())),
        ("tenant_id", str(uuid4())),
        ("status", "ACTIVE"),
        ("created_at", "2026-01-01T00:00:00Z"),
        ("updated_at", "2026-01-01T00:00:00Z"),
    ],
)
def test_company_location_create_rejects_system_controlled_fields(
    field_name: str,
    value: str,
) -> None:
    with pytest.raises(ValidationError):
        CompanyLocationCreate.model_validate(
            _valid_location(**{field_name: value})
        )
