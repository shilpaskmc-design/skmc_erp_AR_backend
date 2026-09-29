from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.ar.catalogue.model import (
    CatalogueStatus,
    Product,
    ProductCategory,
    ServiceCategory,
    ServiceType,
    Sku,
)
from skmc_erp.ar.catalogue.schema import (
    BusinessSegmentAssignment,
    ProductCategoryCreate,
    ProductCategoryUpdate,
    ProductCreate,
    ProductUpdate,
    ServiceCategoryCreate,
    ServiceCategoryUpdate,
    ServiceTypeCreate,
    ServiceTypeUpdate,
    SkuCreate,
    SkuUpdate,
)
from skmc_erp.core.company.model import (
    Company,
    CompanyBusinessNature,
    CompanyStatus,
)
from skmc_erp.core.cost_center.model import (
    CostCenterBusinessSegment,
    CostCenterStatus,
)
from skmc_erp.core.tax_reference.model import (
    CompanyHsnSacCode,
    CompanyHsnSacTaxRate,
    HsnSacClassificationType,
    TaxRate,
    TaxReferenceStatus,
    TaxTreatment,
    TaxType,
)
from skmc_erp.core.tenant.model import Tenant
from skmc_erp.core.uom.service import UomInputError, validate_uom_code


_CATALOGUE_BASE_GST_NATURE_CODES = frozenset(
    {"TAXABLE", "NIL_RATED", "EXEMPT", "NON_GST"}
)


class CatalogueNotFoundError(Exception):
    """The Company is not visible within the resolved Tenant."""


class CatalogueInputError(Exception):
    """A supplied catalogue value or relationship is invalid."""


class CatalogueStateConflictError(Exception):
    """The requested catalogue change conflicts with current business state."""


async def _get_visible_company(
    *, session: AsyncSession, tenant: Tenant, company_id: UUID
) -> Company:
    company = await session.scalar(
        select(Company).where(
            Company.id == company_id,
            Company.tenant_id == tenant.id,
        )
    )
    if company is None:
        raise CatalogueNotFoundError("Company not found")
    return company


async def _get_company(
    *, session: AsyncSession, tenant: Tenant, company_id: UUID
) -> Company:
    company = await _get_visible_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    if company.status is CompanyStatus.INACTIVE:
        raise CatalogueStateConflictError("Company is inactive")
    return company


def _require_service_business(company: Company) -> None:
    if company.business_nature not in (
        CompanyBusinessNature.SERVICES,
        CompanyBusinessNature.BOTH,
    ):
        raise CatalogueStateConflictError(
            "Company business nature does not allow service catalogue setup"
        )


def _require_goods_business(company: Company) -> None:
    if company.business_nature not in (
        CompanyBusinessNature.GOODS,
        CompanyBusinessNature.BOTH,
    ):
        raise CatalogueStateConflictError(
            "Company business nature does not allow goods catalogue setup"
        )


async def _validate_tax_configuration(
    *,
    session: AsyncSession,
    company: Company,
    hsn_sac_code_id: UUID,
    expected_classification: HsnSacClassificationType,
    base_tax_treatment_id: UUID,
    tax_rate_id: UUID | None,
) -> None:
    classification = await session.get(CompanyHsnSacCode, hsn_sac_code_id)
    if classification is None or classification.company_id != company.id:
        raise CatalogueInputError(
            "HSN/SAC classification does not exist for the Company"
        )
    if classification.status is not TaxReferenceStatus.ACTIVE:
        raise CatalogueStateConflictError("HSN/SAC classification is not active")
    if classification.classification_type is not expected_classification:
        raise CatalogueInputError(
            f"{expected_classification.value} classification is required"
        )

    treatment_row = (
        await session.execute(
            select(TaxTreatment, TaxType)
            .join(TaxType, TaxType.id == TaxTreatment.tax_type_id)
            .where(TaxTreatment.id == base_tax_treatment_id)
        )
    ).one_or_none()
    if treatment_row is None:
        raise CatalogueInputError("Base GST Nature does not exist")
    treatment, treatment_tax_type = treatment_row
    if (
        treatment.status is not TaxReferenceStatus.ACTIVE
        or treatment_tax_type.status is not TaxReferenceStatus.ACTIVE
    ):
        raise CatalogueStateConflictError("Base GST Nature is not active")
    if treatment_tax_type.code != "GST":
        raise CatalogueInputError("Base GST Nature must belong to GST")
    if treatment_tax_type.country_code != treatment.country_code:
        raise CatalogueInputError(
            "Base GST Nature does not match its GST jurisdiction"
        )
    if treatment.code not in _CATALOGUE_BASE_GST_NATURE_CODES:
        raise CatalogueInputError(
            "Base GST Nature must be TAXABLE, NIL_RATED, EXEMPT, or NON_GST"
        )

    if treatment.code in {"EXEMPT", "NON_GST"}:
        if tax_rate_id is not None:
            raise CatalogueInputError(
                f"Selected Tax Rate must be null for {treatment.code} Base GST Nature"
            )
        return

    if tax_rate_id is None:
        raise CatalogueInputError(
            f"Selected Tax Rate is required for {treatment.code} Base GST Nature"
        )

    tax_rate_row = (
        await session.execute(
            select(TaxRate, TaxType)
            .join(TaxType, TaxType.id == TaxRate.tax_type_id)
            .where(TaxRate.id == tax_rate_id)
        )
    ).one_or_none()
    if tax_rate_row is None:
        raise CatalogueInputError("Tax Rate does not exist")
    tax_rate, rate_tax_type = tax_rate_row
    if (
        tax_rate.status is not TaxReferenceStatus.ACTIVE
        or rate_tax_type.status is not TaxReferenceStatus.ACTIVE
    ):
        raise CatalogueStateConflictError("Tax Rate is not active")
    if rate_tax_type.code != "GST":
        raise CatalogueInputError("Tax Rate must belong to GST")
    if rate_tax_type.country_code != tax_rate.country_code:
        raise CatalogueInputError("Tax Rate does not match its GST jurisdiction")
    if (
        treatment.tax_type_id != tax_rate.tax_type_id
        or treatment.country_code != tax_rate.country_code
    ):
        raise CatalogueInputError(
            "Tax Rate and Base GST Nature must belong to the same GST jurisdiction"
        )

    if treatment.code == "NIL_RATED" and tax_rate.rate_percent != 0:
        raise CatalogueInputError(
            "NIL_RATED Base GST Nature requires a 0% selected GST rate"
        )

    eligible_mapping = await session.scalar(
        select(CompanyHsnSacTaxRate.id).where(
            CompanyHsnSacTaxRate.company_hsn_sac_code_id == classification.id,
            CompanyHsnSacTaxRate.tax_rate_id == tax_rate.id,
            CompanyHsnSacTaxRate.status == TaxReferenceStatus.ACTIVE,
        )
    )
    if eligible_mapping is None:
        raise CatalogueInputError(
            "Tax Rate is not an active eligible rate for the HSN/SAC classification"
        )


async def _commit(session: AsyncSession, conflict_message: str) -> None:
    try:
        await session.flush()
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise CatalogueStateConflictError(conflict_message) from exc


async def create_service_category(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    category_data: ServiceCategoryCreate,
) -> ServiceCategory:
    company = await _get_company(
        session=session, tenant=tenant, company_id=company_id
    )
    _require_service_business(company)
    category = ServiceCategory(
        company_id=company.id,
        name=category_data.name,
        code=category_data.code,
        status=CatalogueStatus.ACTIVE,
    )
    session.add(category)
    await _commit(session, "Service Category conflicts with existing catalogue data")
    await session.refresh(category)
    return category


async def create_service_type(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    service_data: ServiceTypeCreate,
) -> ServiceType:
    company = await _get_company(
        session=session, tenant=tenant, company_id=company_id
    )
    _require_service_business(company)
    category = await session.get(ServiceCategory, service_data.service_category_id)
    if category is None or category.company_id != company.id:
        raise CatalogueInputError(
            "Service Category does not exist for the Company"
        )
    if category.status is not CatalogueStatus.ACTIVE:
        raise CatalogueStateConflictError("Service Category is not active")
    await _validate_tax_configuration(
        session=session,
        company=company,
        hsn_sac_code_id=service_data.company_hsn_sac_code_id,
        expected_classification=HsnSacClassificationType.SAC,
        base_tax_treatment_id=service_data.base_tax_treatment_id,
        tax_rate_id=service_data.selected_tax_rate_id,
    )
    if service_data.uom:
        try:
            norm_uom = await validate_uom_code(session=session, uom_code=service_data.uom)
        except UomInputError as exc:
            raise CatalogueInputError(str(exc)) from exc
    else:
        norm_uom = None
    service_type = ServiceType(
        company_id=company.id,
        service_category_id=category.id,
        name=service_data.name,
        code=service_data.code,
        description=service_data.description,
        uom=norm_uom,
        company_hsn_sac_code_id=service_data.company_hsn_sac_code_id,
        base_tax_treatment_id=service_data.base_tax_treatment_id,
        selected_tax_rate_id=service_data.selected_tax_rate_id,
        tcs_check_required=service_data.tcs_check_required,
        status=CatalogueStatus.ACTIVE,
    )
    session.add(service_type)
    await _commit(session, "Service Type conflicts with existing catalogue data")
    await session.refresh(service_type)
    return service_type


async def create_product_category(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    category_data: ProductCategoryCreate,
) -> ProductCategory:
    company = await _get_company(
        session=session, tenant=tenant, company_id=company_id
    )
    _require_goods_business(company)
    category = ProductCategory(
        company_id=company.id,
        name=category_data.name,
        code=category_data.code,
        status=CatalogueStatus.ACTIVE,
    )
    session.add(category)
    await _commit(session, "Product Category conflicts with existing catalogue data")
    await session.refresh(category)
    return category


async def create_product(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    product_data: ProductCreate,
) -> Product:
    company = await _get_company(
        session=session, tenant=tenant, company_id=company_id
    )
    _require_goods_business(company)
    category = await session.get(ProductCategory, product_data.product_category_id)
    if category is None or category.company_id != company.id:
        raise CatalogueInputError(
            "Product Category does not exist for the Company"
        )
    if category.status is not CatalogueStatus.ACTIVE:
        raise CatalogueStateConflictError("Product Category is not active")
    product = Product(
        company_id=company.id,
        product_category_id=category.id,
        name=product_data.name,
        code=product_data.code,
        description=product_data.description,
        status=CatalogueStatus.ACTIVE,
    )
    session.add(product)
    await _commit(session, "Product conflicts with existing catalogue data")
    await session.refresh(product)
    return product


async def create_sku(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    sku_data: SkuCreate,
) -> Sku:
    company = await _get_company(
        session=session, tenant=tenant, company_id=company_id
    )
    _require_goods_business(company)
    product = await session.get(Product, sku_data.product_id)
    if product is None or product.company_id != company.id:
        raise CatalogueInputError("Product does not exist for the Company")
    if product.status is not CatalogueStatus.ACTIVE:
        raise CatalogueStateConflictError("Product is not active")
    await _validate_tax_configuration(
        session=session,
        company=company,
        hsn_sac_code_id=sku_data.company_hsn_sac_code_id,
        expected_classification=HsnSacClassificationType.HSN,
        base_tax_treatment_id=sku_data.base_tax_treatment_id,
        tax_rate_id=sku_data.selected_tax_rate_id,
    )
    if not sku_data.uom or not sku_data.uom.strip():
        raise CatalogueInputError("UOM is required for SKU")
    try:
        norm_uom = await validate_uom_code(session=session, uom_code=sku_data.uom)
    except UomInputError as exc:
        raise CatalogueInputError(str(exc)) from exc
    if norm_uom is None:
        raise CatalogueInputError("UOM is required for SKU")
    sku = Sku(
        company_id=company.id,
        product_id=product.id,
        sku_code=sku_data.sku_code,
        name=sku_data.name,
        description=sku_data.description,
        uom=norm_uom,
        company_hsn_sac_code_id=sku_data.company_hsn_sac_code_id,
        base_tax_treatment_id=sku_data.base_tax_treatment_id,
        selected_tax_rate_id=sku_data.selected_tax_rate_id,
        tcs_check_required=sku_data.tcs_check_required,
        status=CatalogueStatus.ACTIVE,
    )
    session.add(sku)
    await _commit(session, "SKU conflicts with existing catalogue data")
    await session.refresh(sku)
    return sku


async def list_service_categories(
    *, session: AsyncSession, tenant: Tenant, company_id: UUID
) -> Sequence[ServiceCategory]:
    await _get_visible_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    result = await session.scalars(
        select(ServiceCategory)
        .where(ServiceCategory.company_id == company_id)
        .order_by(ServiceCategory.name, ServiceCategory.id)
    )
    return result.all()


async def get_service_category(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    category_id: UUID,
) -> ServiceCategory | None:
    return await session.scalar(
        select(ServiceCategory)
        .join(Company, ServiceCategory.company_id == Company.id)
        .where(
            ServiceCategory.id == category_id,
            ServiceCategory.company_id == company_id,
            Company.tenant_id == tenant.id,
        )
    )


async def update_service_category(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    category_id: UUID,
    category_data: ServiceCategoryUpdate,
) -> ServiceCategory | None:
    await _get_company(session=session, tenant=tenant, company_id=company_id)
    category = await get_service_category(
        session=session,
        tenant=tenant,
        company_id=company_id,
        category_id=category_id,
    )
    if category is None:
        return None
    if category.status is CatalogueStatus.INACTIVE:
        raise CatalogueStateConflictError(
            "Inactive Service Category cannot be changed"
        )
    for field, value in category_data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    category.updated_at = datetime.now(UTC)
    await _commit(
        session,
        "Service Category conflicts with existing catalogue data",
    )
    await session.refresh(category)
    return category


async def inactivate_service_category(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    category_id: UUID,
) -> ServiceCategory | None:
    await _get_company(session=session, tenant=tenant, company_id=company_id)
    category = await get_service_category(
        session=session,
        tenant=tenant,
        company_id=company_id,
        category_id=category_id,
    )
    if category is None:
        return None
    if category.status is CatalogueStatus.INACTIVE:
        return category

    active_child_id = await session.scalar(
        select(ServiceType.id)
        .where(
            ServiceType.service_category_id == category.id,
            ServiceType.status == CatalogueStatus.ACTIVE,
        )
        .limit(1)
    )
    if active_child_id is not None:
        raise CatalogueStateConflictError(
            "Service Category cannot be inactivated while it has active Service Types"
        )

    category.status = CatalogueStatus.INACTIVE
    category.updated_at = datetime.now(UTC)
    await _commit(session, "Service Category could not be inactivated")
    await session.refresh(category)
    return category


async def list_service_types(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    service_category_id: UUID | None = None,
) -> Sequence[ServiceType]:
    await _get_visible_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    statement = select(ServiceType).where(ServiceType.company_id == company_id)
    if service_category_id is not None:
        statement = statement.where(
            ServiceType.service_category_id == service_category_id
        )
    result = await session.scalars(
        statement.order_by(ServiceType.name, ServiceType.id)
    )
    return result.all()


async def get_service_type(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    service_type_id: UUID,
) -> ServiceType | None:
    return await session.scalar(
        select(ServiceType)
        .join(Company, ServiceType.company_id == Company.id)
        .where(
            ServiceType.id == service_type_id,
            ServiceType.company_id == company_id,
            Company.tenant_id == tenant.id,
        )
    )


async def update_service_type(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    service_type_id: UUID,
    service_data: ServiceTypeUpdate,
) -> ServiceType | None:
    company = await _get_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    service_type = await get_service_type(
        session=session,
        tenant=tenant,
        company_id=company_id,
        service_type_id=service_type_id,
    )
    if service_type is None:
        return None
    if service_type.status is CatalogueStatus.INACTIVE:
        raise CatalogueStateConflictError("Inactive Service Type cannot be changed")

    changes = service_data.model_dump(exclude_unset=True)
    tax_fields = {
        "company_hsn_sac_code_id",
        "base_tax_treatment_id",
        "selected_tax_rate_id",
    }
    if tax_fields.intersection(changes):
        await _validate_tax_configuration(
            session=session,
            company=company,
            hsn_sac_code_id=changes.get(
                "company_hsn_sac_code_id",
                service_type.company_hsn_sac_code_id,
            ),
            expected_classification=HsnSacClassificationType.SAC,
            base_tax_treatment_id=changes.get(
                "base_tax_treatment_id",
                service_type.base_tax_treatment_id,
            ),
            tax_rate_id=changes.get(
                "selected_tax_rate_id",
                service_type.selected_tax_rate_id,
            ),
        )
    if "uom" in changes:
        uom_val = changes["uom"]
        if uom_val is not None:
            try:
                changes["uom"] = await validate_uom_code(
                    session=session, uom_code=uom_val
                )
            except UomInputError as exc:
                raise CatalogueInputError(str(exc)) from exc
    for field, value in changes.items():
        setattr(service_type, field, value)
    service_type.updated_at = datetime.now(UTC)
    await _commit(session, "Service Type conflicts with existing catalogue data")
    await session.refresh(service_type)
    return service_type


async def assign_service_type_business_segment(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    service_type_id: UUID,
    assignment_data: BusinessSegmentAssignment,
) -> ServiceType | None:
    await _get_company(session=session, tenant=tenant, company_id=company_id)
    service_type = await get_service_type(
        session=session,
        tenant=tenant,
        company_id=company_id,
        service_type_id=service_type_id,
    )
    if service_type is None:
        return None
    if service_type.status is CatalogueStatus.INACTIVE:
        raise CatalogueStateConflictError("Inactive Service Type cannot be changed")
    if assignment_data.business_segment_id is not None:
        segment = await session.scalar(
            select(CostCenterBusinessSegment).where(
                CostCenterBusinessSegment.id
                == assignment_data.business_segment_id,
                CostCenterBusinessSegment.company_id == company_id,
            )
        )
        if segment is None:
            raise CatalogueInputError(
                "Business Segment does not belong to the Company"
            )
        if segment.status is not CostCenterStatus.ACTIVE:
            raise CatalogueStateConflictError("Business Segment is not active")
    service_type.business_segment_id = assignment_data.business_segment_id
    service_type.updated_at = datetime.now(UTC)
    await _commit(session, "Service Type assignment could not be saved")
    await session.refresh(service_type)
    return service_type


async def inactivate_service_type(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    service_type_id: UUID,
) -> ServiceType | None:
    await _get_company(session=session, tenant=tenant, company_id=company_id)
    service_type = await get_service_type(
        session=session,
        tenant=tenant,
        company_id=company_id,
        service_type_id=service_type_id,
    )
    if service_type is None:
        return None
    if service_type.status is CatalogueStatus.INACTIVE:
        return service_type
    service_type.status = CatalogueStatus.INACTIVE
    service_type.updated_at = datetime.now(UTC)
    await _commit(session, "Service Type could not be inactivated")
    await session.refresh(service_type)
    return service_type


async def list_product_categories(
    *, session: AsyncSession, tenant: Tenant, company_id: UUID
) -> Sequence[ProductCategory]:
    await _get_visible_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    result = await session.scalars(
        select(ProductCategory)
        .where(ProductCategory.company_id == company_id)
        .order_by(ProductCategory.name, ProductCategory.id)
    )
    return result.all()


async def get_product_category(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    category_id: UUID,
) -> ProductCategory | None:
    return await session.scalar(
        select(ProductCategory)
        .join(Company, ProductCategory.company_id == Company.id)
        .where(
            ProductCategory.id == category_id,
            ProductCategory.company_id == company_id,
            Company.tenant_id == tenant.id,
        )
    )


async def update_product_category(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    category_id: UUID,
    category_data: ProductCategoryUpdate,
) -> ProductCategory | None:
    await _get_company(session=session, tenant=tenant, company_id=company_id)
    category = await get_product_category(
        session=session,
        tenant=tenant,
        company_id=company_id,
        category_id=category_id,
    )
    if category is None:
        return None
    if category.status is CatalogueStatus.INACTIVE:
        raise CatalogueStateConflictError(
            "Inactive Product Category cannot be changed"
        )
    for field, value in category_data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    category.updated_at = datetime.now(UTC)
    await _commit(
        session,
        "Product Category conflicts with existing catalogue data",
    )
    await session.refresh(category)
    return category


async def inactivate_product_category(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    category_id: UUID,
) -> ProductCategory | None:
    await _get_company(session=session, tenant=tenant, company_id=company_id)
    category = await get_product_category(
        session=session,
        tenant=tenant,
        company_id=company_id,
        category_id=category_id,
    )
    if category is None:
        return None
    if category.status is CatalogueStatus.INACTIVE:
        return category
    active_product_id = await session.scalar(
        select(Product.id)
        .where(
            Product.product_category_id == category.id,
            Product.status == CatalogueStatus.ACTIVE,
        )
        .limit(1)
    )
    if active_product_id is not None:
        raise CatalogueStateConflictError(
            "Product Category has active Products"
        )
    category.status = CatalogueStatus.INACTIVE
    category.updated_at = datetime.now(UTC)
    await _commit(session, "Product Category could not be inactivated")
    await session.refresh(category)
    return category


async def list_products(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    product_category_id: UUID | None = None,
) -> Sequence[Product]:
    await _get_visible_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    statement = select(Product).where(Product.company_id == company_id)
    if product_category_id is not None:
        statement = statement.where(
            Product.product_category_id == product_category_id
        )
    result = await session.scalars(statement.order_by(Product.name, Product.id))
    return result.all()


async def get_product(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    product_id: UUID,
) -> Product | None:
    return await session.scalar(
        select(Product)
        .join(Company, Product.company_id == Company.id)
        .where(
            Product.id == product_id,
            Product.company_id == company_id,
            Company.tenant_id == tenant.id,
        )
    )


async def update_product(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    product_id: UUID,
    product_data: ProductUpdate,
) -> Product | None:
    await _get_company(session=session, tenant=tenant, company_id=company_id)
    product = await get_product(
        session=session,
        tenant=tenant,
        company_id=company_id,
        product_id=product_id,
    )
    if product is None:
        return None
    if product.status is CatalogueStatus.INACTIVE:
        raise CatalogueStateConflictError("Inactive Product cannot be changed")
    for field, value in product_data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    product.updated_at = datetime.now(UTC)
    await _commit(session, "Product conflicts with existing catalogue data")
    await session.refresh(product)
    return product


async def inactivate_product(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    product_id: UUID,
) -> Product | None:
    await _get_company(session=session, tenant=tenant, company_id=company_id)
    product = await get_product(
        session=session,
        tenant=tenant,
        company_id=company_id,
        product_id=product_id,
    )
    if product is None:
        return None
    if product.status is CatalogueStatus.INACTIVE:
        return product
    active_sku_id = await session.scalar(
        select(Sku.id)
        .where(
            Sku.product_id == product.id,
            Sku.status == CatalogueStatus.ACTIVE,
        )
        .limit(1)
    )
    if active_sku_id is not None:
        raise CatalogueStateConflictError("Product has active SKUs")
    product.status = CatalogueStatus.INACTIVE
    product.updated_at = datetime.now(UTC)
    await _commit(session, "Product could not be inactivated")
    await session.refresh(product)
    return product


async def list_skus(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    product_id: UUID | None = None,
) -> Sequence[Sku]:
    await _get_visible_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    statement = select(Sku).where(Sku.company_id == company_id)
    if product_id is not None:
        statement = statement.where(Sku.product_id == product_id)
    result = await session.scalars(statement.order_by(Sku.name, Sku.id))
    return result.all()


async def get_sku(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    sku_id: UUID,
) -> Sku | None:
    return await session.scalar(
        select(Sku)
        .join(Company, Sku.company_id == Company.id)
        .where(
            Sku.id == sku_id,
            Sku.company_id == company_id,
            Company.tenant_id == tenant.id,
        )
    )


async def update_sku(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    sku_id: UUID,
    sku_data: SkuUpdate,
) -> Sku | None:
    company = await _get_company(
        session=session,
        tenant=tenant,
        company_id=company_id,
    )
    sku = await get_sku(
        session=session,
        tenant=tenant,
        company_id=company_id,
        sku_id=sku_id,
    )
    if sku is None:
        return None
    if sku.status is CatalogueStatus.INACTIVE:
        raise CatalogueStateConflictError("Inactive SKU cannot be changed")

    changes = sku_data.model_dump(exclude_unset=True)
    tax_fields = {
        "company_hsn_sac_code_id",
        "base_tax_treatment_id",
        "selected_tax_rate_id",
    }
    if tax_fields.intersection(changes):
        await _validate_tax_configuration(
            session=session,
            company=company,
            hsn_sac_code_id=changes.get(
                "company_hsn_sac_code_id",
                sku.company_hsn_sac_code_id,
            ),
            expected_classification=HsnSacClassificationType.HSN,
            base_tax_treatment_id=changes.get(
                "base_tax_treatment_id",
                sku.base_tax_treatment_id,
            ),
            tax_rate_id=changes.get(
                "selected_tax_rate_id",
                sku.selected_tax_rate_id,
            ),
        )
    if "uom" in changes:
        uom_val = changes["uom"]
        if uom_val is None or not str(uom_val).strip():
            raise CatalogueInputError("UOM cannot be null or blank for SKU")
        try:
            norm_uom = await validate_uom_code(
                session=session, uom_code=uom_val
            )
        except UomInputError as exc:
            raise CatalogueInputError(str(exc)) from exc
        if norm_uom is None:
            raise CatalogueInputError("UOM cannot be null or blank for SKU")
        changes["uom"] = norm_uom
    for field, value in changes.items():
        setattr(sku, field, value)
    sku.updated_at = datetime.now(UTC)
    await _commit(session, "SKU conflicts with existing catalogue data")
    await session.refresh(sku)
    return sku


async def assign_sku_business_segment(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    sku_id: UUID,
    assignment_data: BusinessSegmentAssignment,
) -> Sku | None:
    await _get_company(session=session, tenant=tenant, company_id=company_id)
    sku = await get_sku(
        session=session,
        tenant=tenant,
        company_id=company_id,
        sku_id=sku_id,
    )
    if sku is None:
        return None
    if sku.status is CatalogueStatus.INACTIVE:
        raise CatalogueStateConflictError("Inactive SKU cannot be changed")
    if assignment_data.business_segment_id is not None:
        segment = await session.scalar(
            select(CostCenterBusinessSegment).where(
                CostCenterBusinessSegment.id
                == assignment_data.business_segment_id,
                CostCenterBusinessSegment.company_id == company_id,
            )
        )
        if segment is None:
            raise CatalogueInputError(
                "Business Segment does not belong to the Company"
            )
        if segment.status is not CostCenterStatus.ACTIVE:
            raise CatalogueStateConflictError("Business Segment is not active")
    sku.business_segment_id = assignment_data.business_segment_id
    sku.updated_at = datetime.now(UTC)
    await _commit(session, "SKU assignment could not be saved")
    await session.refresh(sku)
    return sku


async def inactivate_sku(
    *,
    session: AsyncSession,
    tenant: Tenant,
    company_id: UUID,
    sku_id: UUID,
) -> Sku | None:
    await _get_company(session=session, tenant=tenant, company_id=company_id)
    sku = await get_sku(
        session=session,
        tenant=tenant,
        company_id=company_id,
        sku_id=sku_id,
    )
    if sku is None:
        return None
    if sku.status is CatalogueStatus.INACTIVE:
        return sku
    sku.status = CatalogueStatus.INACTIVE
    sku.updated_at = datetime.now(UTC)
    await _commit(session, "SKU could not be inactivated")
    await session.refresh(sku)
    return sku
