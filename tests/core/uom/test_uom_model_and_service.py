from datetime import UTC, datetime

import pytest
from sqlalchemy import CheckConstraint

from skmc_erp.core.uom.model import Uom, UomStatus
from skmc_erp.core.uom.schema import UomResponse
from skmc_erp.core.uom.service import UomInputError, validate_uom_code
from skmc_erp.model_base import Base


def test_uom_metadata_matches_contract() -> None:
    table = Uom.__table__
    assert table is Base.metadata.tables["core.uoms"]
    assert table.schema == "core"
    assert list(table.columns.keys()) == [
        "code",
        "name",
        "symbol",
        "uqc_code",
        "status",
        "created_at",
        "updated_at",
    ]
    assert table.c.code.primary_key
    assert table.c.symbol.nullable
    assert table.c.uqc_code.nullable
    assert table.c.status.server_default is None


def test_uom_constraints_match_contract() -> None:
    table = Uom.__table__
    checks = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert checks == {
        "ck_uoms_code_format",
        "ck_uoms_name_not_blank",
        "ck_uoms_status",
    }


def test_uom_status_enum_values() -> None:
    assert {status.value for status in UomStatus} == {"ACTIVE", "INACTIVE"}


def test_uom_schema_response() -> None:
    now = datetime.now(UTC)
    response = UomResponse(
        code="NOS",
        name="Numbers",
        symbol="nos",
        uqc_code="NOS",
        status=UomStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    assert response.code == "NOS"
    assert response.uqc_code == "NOS"


@pytest.mark.asyncio
async def test_validate_uom_code_normalization_and_validation() -> None:
    class DummySession:
        async def get(self, model, key):
            if key == "NOS":
                return Uom(
                    code="NOS",
                    name="Numbers",
                    symbol="nos",
                    uqc_code="NOS",
                    status=UomStatus.ACTIVE,
                )
            if key == "INACTIVE_UOM":
                return Uom(
                    code="INACTIVE_UOM",
                    name="Inactive",
                    symbol="in",
                    uqc_code=None,
                    status=UomStatus.INACTIVE,
                )
            return None

    session = DummySession()

    # Empty/whitespace -> raises UomInputError
    with pytest.raises(UomInputError, match="cannot be blank"):
        await validate_uom_code(session=session, uom_code="   ")

    # Lowercase string normalized to uppercase
    result = await validate_uom_code(session=session, uom_code=" nos ")
    assert result == "NOS"

    # Non-existent UOM -> raises UomInputError
    with pytest.raises(UomInputError, match="does not exist"):
        await validate_uom_code(session=session, uom_code="UNKNOWN")

    # Inactive UOM -> raises UomInputError
    with pytest.raises(UomInputError, match="is inactive"):
        await validate_uom_code(session=session, uom_code="INACTIVE_UOM")

    # SAC is a Service Classification Code (HSN/SAC), not a UOM -> raises UomInputError
    with pytest.raises(UomInputError, match="does not exist"):
        await validate_uom_code(session=session, uom_code="SAC")
