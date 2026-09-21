from uuid import uuid4

import pytest
from pydantic import ValidationError

from skmc_erp.ar.catalogue.schema import (
    ProductCategoryCreate,
    ServiceCategoryCreate,
    ServiceTypeCreate,
    SkuCreate,
)


def test_create_schemas_trim_values_and_apply_safe_defaults() -> None:
    category = ServiceCategoryCreate(name="  Advisory  ", code="  ADV  ")
    service = ServiceTypeCreate(
        service_category_id=uuid4(),
        name="  GST Advisory  ",
        company_hsn_sac_code_id=uuid4(),
        selected_tax_rate_id=uuid4(),
        tax_treatment_id=uuid4(),
    )

    assert category.name == "Advisory"
    assert category.code == "ADV"
    assert service.tcs_check_required is False
    assert service.uom is None


@pytest.mark.parametrize(
    "schema,payload",
    [
        (ServiceCategoryCreate, {"name": "   "}),
        (ProductCategoryCreate, {"name": "Products", "code": "   "}),
        (
            SkuCreate,
            {
                "product_id": str(uuid4()),
                "sku_code": "SKU-1",
                "name": "SKU",
                "uom": "   ",
                "company_hsn_sac_code_id": str(uuid4()),
                "selected_tax_rate_id": str(uuid4()),
                "tax_treatment_id": str(uuid4()),
            },
        ),
    ],
)
def test_create_schemas_reject_blank_values(schema: type, payload: dict) -> None:
    with pytest.raises(ValidationError):
        schema.model_validate(payload)


@pytest.mark.parametrize(
    "field_name",
    ["id", "tenant_id", "company_id", "status", "created_at", "updated_at"],
)
def test_create_schema_rejects_system_controlled_fields(field_name: str) -> None:
    with pytest.raises(ValidationError):
        ServiceCategoryCreate.model_validate(
            {"name": "Advisory", field_name: str(uuid4())}
        )


def test_leaf_schemas_require_statutory_references() -> None:
    with pytest.raises(ValidationError):
        ServiceTypeCreate.model_validate(
            {"service_category_id": str(uuid4()), "name": "Advisory"}
        )
    with pytest.raises(ValidationError):
        SkuCreate.model_validate(
            {
                "product_id": str(uuid4()),
                "sku_code": "SKU-1",
                "name": "SKU",
                "uom": "EA",
            }
        )
