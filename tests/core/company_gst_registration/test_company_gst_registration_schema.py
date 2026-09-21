from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from skmc_erp.core.company_gst_registration.schema import (
    CompanyGSTRegistrationCreate,
)


def _valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "gstin": "09ABCDE1234F1Z5",
        "subdivision_code": "IN-UP",
    }
    payload.update(overrides)
    return payload


def test_create_schema_normalizes_gstin_and_optional_legal_name() -> None:
    request = CompanyGSTRegistrationCreate.model_validate(
        _valid_payload(
            gstin="  09abcde1234f1z5  ",
            registered_legal_name="  Example Private Limited  ",
        )
    )

    assert request.gstin == "09ABCDE1234F1Z5"
    assert request.registered_legal_name == "Example Private Limited"
    assert request.gst_registration_type_id is None
    assert request.valid_from is None
    assert request.valid_to is None


@pytest.mark.parametrize(
    "gstin",
    [
        "09ABCDE1234F1Z",
        "9ABCDE1234F1Z55",
        "AAABCDE1234F1Z5",
        "09AB1DE1234F1Z5",
        "09ABCDE123AF1Z5",
        "09ABCDE1234F0Z5",
        "09ABCDE1234F1Y5",
        "09ABCDE1234F1Z!",
    ],
)
def test_create_schema_rejects_malformed_gstin(gstin: str) -> None:
    with pytest.raises(ValidationError):
        CompanyGSTRegistrationCreate.model_validate(_valid_payload(gstin=gstin))


def test_create_schema_validates_optional_values_and_date_order() -> None:
    valid = CompanyGSTRegistrationCreate.model_validate(
        _valid_payload(valid_from="2026-01-01", valid_to="2026-12-31")
    )
    assert valid.valid_from == date(2026, 1, 1)
    assert valid.valid_to == date(2026, 12, 31)

    for overrides in (
        {"registered_legal_name": "   "},
        {"valid_from": "2026-12-31", "valid_to": "2026-01-01"},
        {"subdivision_code": "in-up"},
    ):
        with pytest.raises(ValidationError):
            CompanyGSTRegistrationCreate.model_validate(
                _valid_payload(**overrides)
            )


@pytest.mark.parametrize(
    "field_name",
    ["id", "company_id", "tenant_id", "status", "created_at", "updated_at"],
)
def test_create_schema_rejects_system_controlled_fields(field_name: str) -> None:
    with pytest.raises(ValidationError):
        CompanyGSTRegistrationCreate.model_validate(
            _valid_payload(**{field_name: str(uuid4())})
        )
