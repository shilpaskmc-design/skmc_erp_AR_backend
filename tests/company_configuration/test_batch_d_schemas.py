from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from skmc_erp.ar.delivery.schema import CompanyInvoiceDeliverySettingsPut
from skmc_erp.ar.fx.schema import FXPolicyPut
from skmc_erp.ar.reminder.schema import ReminderScheduleRuleCreate
from skmc_erp.core.fx.schema import ExchangeRateCreate


def test_delivery_schema_validates_all_email_fields() -> None:
    value = CompanyInvoiceDeliverySettingsPut(
        sender_email=" sender@example.com ",
        reply_to_email="reply@example.com",
        default_cc=["one@example.com", "two@example.org"],
    )
    assert value.sender_email == "sender@example.com"

    for payload in (
        {"sender_email": "invalid"},
        {"reply_to_email": "missing-domain@"},
        {"default_cc": ["valid@example.com", "bad"]},
    ):
        with pytest.raises(ValidationError):
            CompanyInvoiceDeliverySettingsPut.model_validate(payload)


def test_exchange_rate_schema_enforces_approved_value_contract() -> None:
    value = ExchangeRateCreate(
        from_currency_code="USD",
        to_currency_code="INR",
        rate=Decimal("83.25"),
        rate_type="CORPORATE",
        effective_from=date(2026, 1, 1),
    )
    assert value.rate == Decimal("83.25")

    for update in (
        {"rate": 0},
        {"to_currency_code": "USD"},
        {"rate_type": "USER_FIXED"},
        {"effective_to": "2025-12-31"},
    ):
        payload = {
            "from_currency_code": "USD",
            "to_currency_code": "INR",
            "rate": "1.0",
            "rate_type": "SPOT",
            "effective_from": "2026-01-01",
            **update,
        }
        with pytest.raises(ValidationError):
            ExchangeRateCreate.model_validate(payload)


def test_fx_policy_schema_enforces_override_reason_invariant() -> None:
    with pytest.raises(ValidationError):
        FXPolicyPut(
            default_rate_type="CORPORATE",
            allow_user_fixed_override=False,
            reason_required_for_override=True,
        )


def test_reminder_offset_accepts_negative_zero_and_positive_values() -> None:
    assert [
        ReminderScheduleRuleCreate(offset_days=value).offset_days
        for value in (-3, 0, 3)
    ] == [-3, 0, 3]
