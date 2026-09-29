from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from skmc_erp.ar.compliance.schema import CompanyLutCreate


def test_company_lut_create_accepts_and_trims_valid_reference() -> None:
    lut = CompanyLutCreate(
        gst_registration_id=uuid4(),
        financial_year_id=uuid4(),
        lut_reference="  AD270324000001L  ",
        valid_from=date(2026, 4, 1),
    )
    assert lut.lut_reference == "AD270324000001L"


def test_company_lut_create_accepts_non_arn_business_reference() -> None:
    lut = CompanyLutCreate(
        gst_registration_id=uuid4(),
        financial_year_id=uuid4(),
        lut_reference="REF/2026-27/001",
        valid_from=date(2026, 4, 1),
    )
    assert lut.lut_reference == "REF/2026-27/001"


@pytest.mark.parametrize("invalid_ref", ["", "   ", " \t\n "])
def test_company_lut_create_rejects_blank_reference(invalid_ref: str) -> None:
    with pytest.raises(ValidationError):
        CompanyLutCreate(
            gst_registration_id=uuid4(),
            financial_year_id=uuid4(),
            lut_reference=invalid_ref,
            valid_from=date(2026, 4, 1),
        )
