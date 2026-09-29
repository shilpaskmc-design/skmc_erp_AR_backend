from uuid import uuid4

import pytest
from pydantic import ValidationError

from skmc_erp.ar.catalogue.schema import (
    BusinessSegmentAssignment,
    ProductCategoryCreate,
    ProductCategoryUpdate,
    ProductUpdate,
    ServiceCategoryCreate,
    ServiceCategoryUpdate,
    ServiceTypeCreate,
    ServiceTypeUpdate,
    SkuCreate,
    SkuUpdate,
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


def test_update_schemas_accept_only_approved_mutable_values() -> None:
    classification_id = uuid4()
    tax_rate_id = uuid4()
    treatment_id = uuid4()

    assert ServiceCategoryUpdate(name="  Advisory Services  ").name == (
        "Advisory Services"
    )
    service = ServiceTypeUpdate(
        name="  Updated Service  ",
        description=None,
        uom="  HOUR  ",
        company_hsn_sac_code_id=classification_id,
        selected_tax_rate_id=tax_rate_id,
        tax_treatment_id=treatment_id,
        tcs_check_required=True,
    )
    product = ProductUpdate(name="  Updated Product  ", description=None)
    sku = SkuUpdate(
        name="  Updated SKU  ",
        description=None,
        uom="  EA  ",
        company_hsn_sac_code_id=classification_id,
        selected_tax_rate_id=tax_rate_id,
        tax_treatment_id=treatment_id,
        tcs_check_required=True,
    )

    assert service.name == "Updated Service"
    assert service.uom == "HOUR"
    assert product.name == "Updated Product"
    assert sku.name == "Updated SKU"
    assert sku.uom == "EA"


@pytest.mark.parametrize(
    ("schema", "field_name"),
    [
        (ServiceCategoryUpdate, "code"),
        (ServiceCategoryUpdate, "status"),
        (ServiceTypeUpdate, "code"),
        (ServiceTypeUpdate, "service_category_id"),
        (ServiceTypeUpdate, "business_segment_id"),
        (ServiceTypeUpdate, "status"),
        (ProductCategoryUpdate, "code"),
        (ProductCategoryUpdate, "status"),
        (ProductUpdate, "code"),
        (ProductUpdate, "product_category_id"),
        (ProductUpdate, "status"),
        (SkuUpdate, "sku_code"),
        (SkuUpdate, "product_id"),
        (SkuUpdate, "business_segment_id"),
        (SkuUpdate, "status"),
    ],
)
def test_update_schemas_reject_unapproved_fields(
    schema: type,
    field_name: str,
) -> None:
    with pytest.raises(ValidationError):
        schema.model_validate({field_name: "not-allowed"})


@pytest.mark.parametrize(
    ("schema", "field_name"),
    [
        (ServiceCategoryUpdate, "name"),
        (ServiceTypeUpdate, "name"),
        (ServiceTypeUpdate, "company_hsn_sac_code_id"),
        (ServiceTypeUpdate, "selected_tax_rate_id"),
        (ServiceTypeUpdate, "tax_treatment_id"),
        (ServiceTypeUpdate, "tcs_check_required"),
        (ProductCategoryUpdate, "name"),
        (ProductUpdate, "name"),
        (SkuUpdate, "name"),
        (SkuUpdate, "uom"),
        (SkuUpdate, "company_hsn_sac_code_id"),
        (SkuUpdate, "selected_tax_rate_id"),
        (SkuUpdate, "tax_treatment_id"),
        (SkuUpdate, "tcs_check_required"),
    ],
)
def test_update_schemas_reject_null_required_fields(
    schema: type,
    field_name: str,
) -> None:
    with pytest.raises(ValidationError):
        schema.model_validate({field_name: None})


def test_business_segment_assignment_is_nullable_required_and_narrow() -> None:
    segment_id = uuid4()
    assert (
        BusinessSegmentAssignment(
            business_segment_id=segment_id
        ).business_segment_id
        == segment_id
    )
    assert (
        BusinessSegmentAssignment(
            business_segment_id=None
        ).business_segment_id
        is None
    )

    with pytest.raises(ValidationError):
        BusinessSegmentAssignment.model_validate({})
    with pytest.raises(ValidationError):
        BusinessSegmentAssignment.model_validate(
            {"business_segment_id": str(segment_id), "status": "ACTIVE"}
        )
