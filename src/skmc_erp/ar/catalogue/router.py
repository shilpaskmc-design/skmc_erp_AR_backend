from typing import Annotated, Awaitable, Callable, TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.ar.catalogue.schema import (
    ProductCategoryCreate,
    ProductCategoryResponse,
    ProductCreate,
    ProductResponse,
    ServiceCategoryCreate,
    ServiceCategoryResponse,
    ServiceTypeCreate,
    ServiceTypeResponse,
    SkuCreate,
    SkuResponse,
)
from skmc_erp.ar.catalogue.service import (
    CatalogueInputError,
    CatalogueNotFoundError,
    CatalogueStateConflictError,
    create_product,
    create_product_category,
    create_service_category,
    create_service_type,
    create_sku,
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
