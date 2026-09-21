from sqlalchemy import ForeignKeyConstraint, UniqueConstraint

from skmc_erp.ar.catalogue.model import (
    CatalogueStatus,
    Product,
    ProductCategory,
    ServiceCategory,
    ServiceType,
    Sku,
)
from skmc_erp.core.tax_reference.model import CompanyHsnSacCode, TaxRate, TaxTreatment
from skmc_erp.core.cost_center.model import CostCenterBusinessSegment
from skmc_erp.model_base import Base


def test_catalogue_metadata_maps_to_ar_schema_with_leaf_segment_links() -> None:
    assert CompanyHsnSacCode.__table__ is Base.metadata.tables[
        "core.company_hsn_sac_codes"
    ]
    assert TaxRate.__table__ is Base.metadata.tables["core.tax_rates"]
    assert TaxTreatment.__table__ is Base.metadata.tables["core.tax_treatments"]
    assert CostCenterBusinessSegment.__table__ is Base.metadata.tables[
        "core.cost_center_business_segments"
    ]
    for model in (ServiceCategory, ServiceType, ProductCategory, Product, Sku):
        assert model.__table__.schema == "ar"
        assert str(model.__table__.c.id.server_default.arg) == "gen_random_uuid()"
        assert model.__table__.c.status.server_default is None
    assert ServiceType.__table__.c.business_segment_id.nullable
    assert Sku.__table__.c.business_segment_id.nullable
    assert "business_segment_id" not in ServiceCategory.__table__.columns
    assert "business_segment_id" not in ProductCategory.__table__.columns
    assert "business_segment_id" not in Product.__table__.columns


def test_catalogue_uniqueness_and_defaults_match_contract() -> None:
    service_category_uniques = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in ServiceCategory.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert service_category_uniques[
        "uq_service_categories_company_id_name"
    ] == ("company_id", "name")
    assert ServiceType.__table__.c.tcs_check_required.server_default.arg.text == "false"
    assert Sku.__table__.c.tcs_check_required.server_default.arg.text == "false"
    assert Sku.__table__.c.uom.nullable is False
    assert ServiceType.__table__.c.uom.nullable is True


def test_catalogue_composite_foreign_keys_enforce_same_company_hierarchy() -> None:
    expected = {
        ServiceType: {
            "fk_service_types_company_service_category",
            "fk_service_types_company_hsn_sac_code",
            "fk_service_types_company_business_segment",
        },
        Product: {"fk_products_company_product_category"},
        Sku: {
            "fk_skus_company_product",
            "fk_skus_company_hsn_sac_code",
            "fk_skus_company_business_segment",
        },
    }
    for model, names in expected.items():
        actual = {
            constraint.name
            for constraint in model.__table__.constraints
            if isinstance(constraint, ForeignKeyConstraint)
            and len(constraint.elements) == 2
        }
        assert actual == names


def test_catalogue_status_contains_only_approved_values() -> None:
    assert {value.value for value in CatalogueStatus} == {"ACTIVE", "INACTIVE"}
