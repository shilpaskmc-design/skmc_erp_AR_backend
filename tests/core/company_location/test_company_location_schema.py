from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from skmc_erp.core.company_location.schema import (
    CompanyLocationCreate,
    CompanyLocationUpdate,
    CompanyLocationVersionResponse,
    LocationCostCenterAssignment,
)


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


def test_company_location_create_normalizes_optional_location_code() -> None:
    supplied = CompanyLocationCreate.model_validate(
        _valid_location(location_code="  noida_ro-1  ")
    )
    generated = CompanyLocationCreate.model_validate(_valid_location())

    assert supplied.location_code == "NOIDA_RO-1"
    assert generated.location_code is None

    with pytest.raises(ValidationError):
        CompanyLocationCreate.model_validate(
            _valid_location(location_code="invalid code")
        )


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


def test_company_location_update_accepts_approved_fields() -> None:
    registration_id = uuid4()
    location = CompanyLocationUpdate.model_validate(
        {
            "location_name": "  Updated Branch  ",
            "address_line_1": "  Sector 63  ",
            "is_branch": True,
            "gst_registration_id": str(registration_id),
        }
    )

    assert location.location_name == "Updated Branch"
    assert location.address_line_1 == "Sector 63"
    assert location.gst_registration_id == registration_id


@pytest.mark.parametrize(
    "field_name",
    [
        "id",
        "company_id",
        "tenant_id",
        "location_code",
        "cost_center_location_id",
        "status",
        "created_at",
        "updated_at",
    ],
)
def test_company_location_update_rejects_unapproved_fields(
    field_name: str,
) -> None:
    with pytest.raises(ValidationError):
        CompanyLocationUpdate.model_validate({field_name: "not-allowed"})


@pytest.mark.parametrize(
    "field_name",
    ["location_name", "address_line_1", "city", "country_code"],
)
def test_company_location_update_rejects_null_required_fields(
    field_name: str,
) -> None:
    with pytest.raises(ValidationError):
        CompanyLocationUpdate.model_validate({field_name: None})


def test_location_cost_center_assignment_is_nullable_required_and_narrow() -> None:
    cost_center_id = uuid4()
    assert (
        LocationCostCenterAssignment(
            cost_center_location_id=cost_center_id
        ).cost_center_location_id
        == cost_center_id
    )
    assert (
        LocationCostCenterAssignment(
            cost_center_location_id=None
        ).cost_center_location_id
        is None
    )

    with pytest.raises(ValidationError):
        LocationCostCenterAssignment.model_validate({})
    with pytest.raises(ValidationError):
        LocationCostCenterAssignment.model_validate(
            {"cost_center_location_id": str(cost_center_id), "status": "ACTIVE"}
        )


def test_company_location_version_response_exposes_address_history() -> None:
    version_id = uuid4()
    location_id = uuid4()
    response = CompanyLocationVersionResponse.model_validate(
        {
            "id": version_id,
            "company_location_id": location_id,
            "address_line_1": "Sector 62",
            "address_line_2": None,
            "city": "Noida",
            "district": "Gautam Buddha Nagar",
            "subdivision_code": "IN-UP",
            "country_code": "IN",
            "postal_code": "201309",
            "valid_from": date(2026, 4, 10),
            "valid_to": None,
            "created_at": datetime(2026, 4, 10, tzinfo=UTC),
        }
    )

    assert response.id == version_id
    assert response.company_location_id == location_id
    assert response.valid_from == date(2026, 4, 10)
    assert response.valid_to is None
