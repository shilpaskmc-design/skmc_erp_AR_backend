from typing import Annotated, Awaitable, Callable, TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.ar.catalogue.schema import (
    BusinessSegmentAssignment,
    ProductCategoryCreate,
    ProductCategoryResponse,
    ProductCategoryUpdate,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    ServiceCategoryCreate,
    ServiceCategoryResponse,
    ServiceCategoryUpdate,
    ServiceTypeCreate,
    ServiceTypeResponse,
    ServiceTypeUpdate,
    SkuCreate,
    SkuResponse,
    SkuUpdate,
)
from skmc_erp.ar.catalogue.service import (
    CatalogueInputError,
    CatalogueNotFoundError,
    CatalogueStateConflictError,
    assign_service_type_business_segment,
    assign_sku_business_segment,
    create_product,
    create_product_category,
    create_service_category,
    create_service_type,
    create_sku,
    get_product,
    get_product_category,
    get_service_category,
    get_service_type,
    get_sku,
    inactivate_product,
    inactivate_product_category,
    inactivate_service_category,
    inactivate_service_type,
    inactivate_sku,
    list_product_categories,
    list_products,
    list_service_categories,
    list_service_types,
    list_skus,
    update_product,
    update_product_category,
    update_service_category,
    update_service_type,
    update_sku,
)
from skmc_erp.core.tenant.dependencies import get_temporary_tenant_context
from skmc_erp.core.tenant.model import Tenant
from skmc_erp.database import get_db_session

router = APIRouter(prefix="/companies/{company_id}", tags=["catalogue"])

ResponseT = TypeVar("ResponseT")


async def _translate_service_errors(operation: Callable[[], Awaitable[ResponseT]]) -> ResponseT:
    try:
        return await operation()
    except CatalogueNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except CatalogueInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except CatalogueStateConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.post(
    "/service-categories",
    response_model=ServiceCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_service_category_endpoint(
    company_id: UUID,
    category_data: ServiceCategoryCreate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ServiceCategoryResponse:
    category = await _translate_service_errors(
        lambda: create_service_category(
            session=session,
            tenant=tenant,
            company_id=company_id,
            category_data=category_data,
        )
    )
    return ServiceCategoryResponse.model_validate(category)


@router.post(
    "/service-types",
    response_model=ServiceTypeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_service_type_endpoint(
    company_id: UUID,
    service_data: ServiceTypeCreate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ServiceTypeResponse:
    service_type = await _translate_service_errors(
        lambda: create_service_type(
            session=session,
            tenant=tenant,
            company_id=company_id,
            service_data=service_data,
        )
    )
    return ServiceTypeResponse.model_validate(service_type)


@router.post(
    "/product-categories",
    response_model=ProductCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_product_category_endpoint(
    company_id: UUID,
    category_data: ProductCategoryCreate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProductCategoryResponse:
    category = await _translate_service_errors(
        lambda: create_product_category(
            session=session,
            tenant=tenant,
            company_id=company_id,
            category_data=category_data,
        )
    )
    return ProductCategoryResponse.model_validate(category)


@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_product_endpoint(
    company_id: UUID,
    product_data: ProductCreate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProductResponse:
    product = await _translate_service_errors(
        lambda: create_product(
            session=session,
            tenant=tenant,
            company_id=company_id,
            product_data=product_data,
        )
    )
    return ProductResponse.model_validate(product)


@router.post(
    "/skus",
    response_model=SkuResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_sku_endpoint(
    company_id: UUID,
    sku_data: SkuCreate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SkuResponse:
    sku = await _translate_service_errors(
        lambda: create_sku(
            session=session,
            tenant=tenant,
            company_id=company_id,
            sku_data=sku_data,
        )
    )
    return SkuResponse.model_validate(sku)


@router.get(
    "/service-categories",
    response_model=list[ServiceCategoryResponse],
)
async def list_service_categories_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ServiceCategoryResponse]:
    categories = await _translate_service_errors(
        lambda: list_service_categories(
            session=session,
            tenant=tenant,
            company_id=company_id,
        )
    )
    return [
        ServiceCategoryResponse.model_validate(category)
        for category in categories
    ]


@router.get(
    "/service-categories/{category_id}",
    response_model=ServiceCategoryResponse,
)
async def get_service_category_endpoint(
    company_id: UUID,
    category_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ServiceCategoryResponse:
    category = await get_service_category(
        session=session,
        tenant=tenant,
        company_id=company_id,
        category_id=category_id,
    )
    if category is None:
        raise HTTPException(status_code=404, detail="Service Category not found")
    return ServiceCategoryResponse.model_validate(category)


@router.patch(
    "/service-categories/{category_id}",
    response_model=ServiceCategoryResponse,
)
async def update_service_category_endpoint(
    company_id: UUID,
    category_id: UUID,
    category_data: ServiceCategoryUpdate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ServiceCategoryResponse:
    category = await _translate_service_errors(
        lambda: update_service_category(
            session=session,
            tenant=tenant,
            company_id=company_id,
            category_id=category_id,
            category_data=category_data,
        )
    )
    if category is None:
        raise HTTPException(status_code=404, detail="Service Category not found")
    return ServiceCategoryResponse.model_validate(category)


@router.post(
    "/service-categories/{category_id}/inactivate",
    response_model=ServiceCategoryResponse,
)
async def inactivate_service_category_endpoint(
    company_id: UUID,
    category_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ServiceCategoryResponse:
    category = await _translate_service_errors(
        lambda: inactivate_service_category(
            session=session,
            tenant=tenant,
            company_id=company_id,
            category_id=category_id,
        )
    )
    if category is None:
        raise HTTPException(status_code=404, detail="Service Category not found")
    return ServiceCategoryResponse.model_validate(category)


@router.get("/service-types", response_model=list[ServiceTypeResponse])
async def list_service_types_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    service_category_id: UUID | None = None,
) -> list[ServiceTypeResponse]:
    service_types = await _translate_service_errors(
        lambda: list_service_types(
            session=session,
            tenant=tenant,
            company_id=company_id,
            service_category_id=service_category_id,
        )
    )
    return [
        ServiceTypeResponse.model_validate(service_type)
        for service_type in service_types
    ]


@router.get(
    "/service-types/{service_type_id}",
    response_model=ServiceTypeResponse,
)
async def get_service_type_endpoint(
    company_id: UUID,
    service_type_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ServiceTypeResponse:
    service_type = await get_service_type(
        session=session,
        tenant=tenant,
        company_id=company_id,
        service_type_id=service_type_id,
    )
    if service_type is None:
        raise HTTPException(status_code=404, detail="Service Type not found")
    return ServiceTypeResponse.model_validate(service_type)


@router.patch(
    "/service-types/{service_type_id}",
    response_model=ServiceTypeResponse,
)
async def update_service_type_endpoint(
    company_id: UUID,
    service_type_id: UUID,
    service_data: ServiceTypeUpdate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ServiceTypeResponse:
    service_type = await _translate_service_errors(
        lambda: update_service_type(
            session=session,
            tenant=tenant,
            company_id=company_id,
            service_type_id=service_type_id,
            service_data=service_data,
        )
    )
    if service_type is None:
        raise HTTPException(status_code=404, detail="Service Type not found")
    return ServiceTypeResponse.model_validate(service_type)


@router.put(
    "/service-types/{service_type_id}/business-segment",
    response_model=ServiceTypeResponse,
)
async def assign_service_type_business_segment_endpoint(
    company_id: UUID,
    service_type_id: UUID,
    assignment_data: BusinessSegmentAssignment,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ServiceTypeResponse:
    service_type = await _translate_service_errors(
        lambda: assign_service_type_business_segment(
            session=session,
            tenant=tenant,
            company_id=company_id,
            service_type_id=service_type_id,
            assignment_data=assignment_data,
        )
    )
    if service_type is None:
        raise HTTPException(status_code=404, detail="Service Type not found")
    return ServiceTypeResponse.model_validate(service_type)


@router.post(
    "/service-types/{service_type_id}/inactivate",
    response_model=ServiceTypeResponse,
)
async def inactivate_service_type_endpoint(
    company_id: UUID,
    service_type_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ServiceTypeResponse:
    service_type = await _translate_service_errors(
        lambda: inactivate_service_type(
            session=session,
            tenant=tenant,
            company_id=company_id,
            service_type_id=service_type_id,
        )
    )
    if service_type is None:
        raise HTTPException(status_code=404, detail="Service Type not found")
    return ServiceTypeResponse.model_validate(service_type)


@router.get(
    "/product-categories",
    response_model=list[ProductCategoryResponse],
)
async def list_product_categories_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ProductCategoryResponse]:
    categories = await _translate_service_errors(
        lambda: list_product_categories(
            session=session,
            tenant=tenant,
            company_id=company_id,
        )
    )
    return [
        ProductCategoryResponse.model_validate(category)
        for category in categories
    ]


@router.get(
    "/product-categories/{category_id}",
    response_model=ProductCategoryResponse,
)
async def get_product_category_endpoint(
    company_id: UUID,
    category_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProductCategoryResponse:
    category = await get_product_category(
        session=session,
        tenant=tenant,
        company_id=company_id,
        category_id=category_id,
    )
    if category is None:
        raise HTTPException(status_code=404, detail="Product Category not found")
    return ProductCategoryResponse.model_validate(category)


@router.patch(
    "/product-categories/{category_id}",
    response_model=ProductCategoryResponse,
)
async def update_product_category_endpoint(
    company_id: UUID,
    category_id: UUID,
    category_data: ProductCategoryUpdate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProductCategoryResponse:
    category = await _translate_service_errors(
        lambda: update_product_category(
            session=session,
            tenant=tenant,
            company_id=company_id,
            category_id=category_id,
            category_data=category_data,
        )
    )
    if category is None:
        raise HTTPException(status_code=404, detail="Product Category not found")
    return ProductCategoryResponse.model_validate(category)


@router.post(
    "/product-categories/{category_id}/inactivate",
    response_model=ProductCategoryResponse,
)
async def inactivate_product_category_endpoint(
    company_id: UUID,
    category_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProductCategoryResponse:
    category = await _translate_service_errors(
        lambda: inactivate_product_category(
            session=session,
            tenant=tenant,
            company_id=company_id,
            category_id=category_id,
        )
    )
    if category is None:
        raise HTTPException(status_code=404, detail="Product Category not found")
    return ProductCategoryResponse.model_validate(category)


@router.get("/products", response_model=list[ProductResponse])
async def list_products_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    product_category_id: UUID | None = None,
) -> list[ProductResponse]:
    products = await _translate_service_errors(
        lambda: list_products(
            session=session,
            tenant=tenant,
            company_id=company_id,
            product_category_id=product_category_id,
        )
    )
    return [ProductResponse.model_validate(product) for product in products]


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product_endpoint(
    company_id: UUID,
    product_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProductResponse:
    product = await get_product(
        session=session,
        tenant=tenant,
        company_id=company_id,
        product_id=product_id,
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse.model_validate(product)


@router.patch("/products/{product_id}", response_model=ProductResponse)
async def update_product_endpoint(
    company_id: UUID,
    product_id: UUID,
    product_data: ProductUpdate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProductResponse:
    product = await _translate_service_errors(
        lambda: update_product(
            session=session,
            tenant=tenant,
            company_id=company_id,
            product_id=product_id,
            product_data=product_data,
        )
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse.model_validate(product)


@router.post(
    "/products/{product_id}/inactivate",
    response_model=ProductResponse,
)
async def inactivate_product_endpoint(
    company_id: UUID,
    product_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProductResponse:
    product = await _translate_service_errors(
        lambda: inactivate_product(
            session=session,
            tenant=tenant,
            company_id=company_id,
            product_id=product_id,
        )
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse.model_validate(product)


@router.get("/skus", response_model=list[SkuResponse])
async def list_skus_endpoint(
    company_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    product_id: UUID | None = None,
) -> list[SkuResponse]:
    skus = await _translate_service_errors(
        lambda: list_skus(
            session=session,
            tenant=tenant,
            company_id=company_id,
            product_id=product_id,
        )
    )
    return [SkuResponse.model_validate(sku) for sku in skus]


@router.get("/skus/{sku_id}", response_model=SkuResponse)
async def get_sku_endpoint(
    company_id: UUID,
    sku_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SkuResponse:
    sku = await get_sku(
        session=session,
        tenant=tenant,
        company_id=company_id,
        sku_id=sku_id,
    )
    if sku is None:
        raise HTTPException(status_code=404, detail="SKU not found")
    return SkuResponse.model_validate(sku)


@router.patch("/skus/{sku_id}", response_model=SkuResponse)
async def update_sku_endpoint(
    company_id: UUID,
    sku_id: UUID,
    sku_data: SkuUpdate,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SkuResponse:
    sku = await _translate_service_errors(
        lambda: update_sku(
            session=session,
            tenant=tenant,
            company_id=company_id,
            sku_id=sku_id,
            sku_data=sku_data,
        )
    )
    if sku is None:
        raise HTTPException(status_code=404, detail="SKU not found")
    return SkuResponse.model_validate(sku)


@router.put(
    "/skus/{sku_id}/business-segment",
    response_model=SkuResponse,
)
async def assign_sku_business_segment_endpoint(
    company_id: UUID,
    sku_id: UUID,
    assignment_data: BusinessSegmentAssignment,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SkuResponse:
    sku = await _translate_service_errors(
        lambda: assign_sku_business_segment(
            session=session,
            tenant=tenant,
            company_id=company_id,
            sku_id=sku_id,
            assignment_data=assignment_data,
        )
    )
    if sku is None:
        raise HTTPException(status_code=404, detail="SKU not found")
    return SkuResponse.model_validate(sku)


@router.post("/skus/{sku_id}/inactivate", response_model=SkuResponse)
async def inactivate_sku_endpoint(
    company_id: UUID,
    sku_id: UUID,
    tenant: Annotated[Tenant, Depends(get_temporary_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SkuResponse:
    sku = await _translate_service_errors(
        lambda: inactivate_sku(
            session=session,
            tenant=tenant,
            company_id=company_id,
            sku_id=sku_id,
        )
    )
    if sku is None:
        raise HTTPException(status_code=404, detail="SKU not found")
    return SkuResponse.model_validate(sku)
