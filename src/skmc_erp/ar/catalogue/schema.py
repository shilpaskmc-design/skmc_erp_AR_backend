from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

from skmc_erp.ar.catalogue.model import CatalogueStatus


CategoryName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)
]
ItemName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
OptionalCode = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)
]
SkuCode = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)
]
OptionalDescription = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]
Uom = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)
]


class ServiceCategoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: CategoryName
    code: OptionalCode | None = None


class ServiceCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    code: str | None
    status: CatalogueStatus
    created_at: datetime
    updated_at: datetime


class ServiceTypeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_category_id: UUID
    name: ItemName
    code: OptionalCode | None = None
    description: OptionalDescription | None = None
    uom: Uom | None = None
    company_hsn_sac_code_id: UUID
    selected_tax_rate_id: UUID
    tax_treatment_id: UUID
    tcs_check_required: bool = False


class ServiceTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    service_category_id: UUID
    name: str
    code: str | None
    description: str | None
    uom: str | None
    company_hsn_sac_code_id: UUID
    selected_tax_rate_id: UUID
    tax_treatment_id: UUID
    tcs_check_required: bool
    status: CatalogueStatus
    created_at: datetime
    updated_at: datetime


class ProductCategoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: CategoryName
    code: OptionalCode | None = None


class ProductCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    code: str | None
    status: CatalogueStatus
    created_at: datetime
    updated_at: datetime


class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_category_id: UUID
    name: ItemName
    code: OptionalCode | None = None
    description: OptionalDescription | None = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    product_category_id: UUID
    name: str
    code: str | None
    description: str | None
    status: CatalogueStatus
    created_at: datetime
    updated_at: datetime


class SkuCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: UUID
    sku_code: SkuCode
    name: ItemName
    description: OptionalDescription | None = None
    uom: Uom
    company_hsn_sac_code_id: UUID
    selected_tax_rate_id: UUID
    tax_treatment_id: UUID
    tcs_check_required: bool = False


class SkuResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    product_id: UUID
    sku_code: str
    name: str
    description: str | None
    uom: str
    company_hsn_sac_code_id: UUID
    selected_tax_rate_id: UUID
    tax_treatment_id: UUID
    tcs_check_required: bool
    status: CatalogueStatus
    created_at: datetime
    updated_at: datetime
