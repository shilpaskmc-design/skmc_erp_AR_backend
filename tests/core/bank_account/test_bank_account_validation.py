import pytest
from pydantic import ValidationError

from skmc_erp.core.bank_account.model import BankAccountType, CompanyBankAccount
from skmc_erp.core.bank_account.schema import (
    CompanyBankAccountCreate,
    CompanyBankAccountUpdate,
)


def test_bank_account_type_enum_values() -> None:
    expected = {"CURRENT", "SAVINGS", "OVERDRAFT", "CASH_CREDIT", "MONEY_MARKET", "OTHER"}
    assert {t.value for t in BankAccountType} == expected


def test_company_bank_account_repr_masks_account_number() -> None:
    account = CompanyBankAccount(
        bank_name="HDFC Bank",
        account_number="123456789012",
    )
    repr_str = repr(account)
    assert "123456789012" not in repr_str
    assert "****9012" in repr_str


def test_create_bank_account_valid_indian_ifsc() -> None:
    data = CompanyBankAccountCreate(
        bank_country_code="in",
        account_holder_name="Acme Corp",
        bank_name="HDFC Bank",
        account_number="1234567890",
        currency_code="INR",
        ifsc="hdfc0001234",
        account_type="savings",
    )
    assert data.bank_country_code == "IN"
    assert data.ifsc == "HDFC0001234"
    assert data.account_type == "SAVINGS"


def test_create_bank_account_invalid_indian_ifsc_rejected() -> None:
    with pytest.raises(ValidationError, match="Invalid IFSC format"):
        CompanyBankAccountCreate(
            bank_country_code="IN",
            account_holder_name="Acme Corp",
            bank_name="HDFC Bank",
            account_number="1234567890",
            currency_code="INR",
            ifsc="SBIN1000000",
        )


def test_foreign_bank_account_does_not_require_ifsc_and_allows_non_ifsc_string() -> None:
    # US bank account without IFSC
    data = CompanyBankAccountCreate(
        bank_country_code="US",
        account_holder_name="Global Inc",
        bank_name="Chase Bank",
        account_number="9876543210",
        currency_code="USD",
        ifsc=None,
    )
    assert data.bank_country_code == "US"
    assert data.ifsc is None


def test_swift_bic_validation() -> None:
    # Valid 8-char SWIFT
    data8 = CompanyBankAccountCreate(
        bank_country_code="DE",
        account_holder_name="Test GmbH",
        bank_name="Deutsche Bank",
        account_number="DE123456789",
        currency_code="EUR",
        swift="deutdedb",
    )
    assert data8.swift == "DEUTDEDB"

    # Valid 11-char SWIFT
    data11 = CompanyBankAccountCreate(
        bank_country_code="DE",
        account_holder_name="Test GmbH",
        bank_name="Deutsche Bank",
        account_number="DE123456789",
        currency_code="EUR",
        swift="deutdedbfra",
    )
    assert data11.swift == "DEUTDEDBFRA"

    # Malformed SWIFT
    with pytest.raises(ValidationError, match="Invalid SWIFT/BIC format"):
        CompanyBankAccountCreate(
            bank_country_code="DE",
            account_holder_name="Test GmbH",
            bank_name="Deutsche Bank",
            account_number="DE123456789",
            currency_code="EUR",
            swift="INVALID_SWIFT",
        )


def test_iban_validation() -> None:
    # Valid German IBAN
    valid_de_iban = "DE89 3704 0044 0532 0130 00"
    data = CompanyBankAccountCreate(
        bank_country_code="DE",
        account_holder_name="Test GmbH",
        bank_name="Commerzbank",
        account_number="DE89370400440532013000",
        currency_code="EUR",
        iban=valid_de_iban,
    )
    assert data.iban == "DE89370400440532013000"

    # Invalid IBAN checksum
    with pytest.raises(ValidationError, match="Invalid IBAN format or checksum"):
        CompanyBankAccountCreate(
            bank_country_code="DE",
            account_holder_name="Test GmbH",
            bank_name="Commerzbank",
            account_number="12345",
            currency_code="EUR",
            iban="DE89370400440532013099",  # bad checksum
        )


def test_controlled_account_types() -> None:
    for acc_type in ["CURRENT", "SAVINGS", "OVERDRAFT", "CASH_CREDIT", "MONEY_MARKET", "OTHER"]:
        data = CompanyBankAccountUpdate(account_type=acc_type.lower())
        assert data.account_type == acc_type

    with pytest.raises(ValidationError, match="Invalid account_type"):
        CompanyBankAccountUpdate(account_type="INVALID_TYPE")


def test_create_bank_account_requires_bank_country_code() -> None:
    with pytest.raises(ValidationError, match="bank_country_code"):
        CompanyBankAccountCreate(
            account_holder_name="Acme Corp",
            bank_name="HDFC Bank",
            account_number="1234567890",
            currency_code="INR",
        )


def test_historical_bank_account_update_without_bank_country_code() -> None:
    # Historical bank account update where bank_country_code is omitted/None
    update_data = CompanyBankAccountUpdate(branch_name="Main Branch")
    assert update_data.bank_country_code is None
    assert update_data.branch_name == "Main Branch"
