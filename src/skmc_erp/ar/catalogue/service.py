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
    ProductCategoryCreate,
    ProductCreate,
    ServiceCategoryCreate,
    ServiceTypeCreate,
    SkuCreate,
)
from skmc_erp.core.company.model import (
    Company,
    CompanyBusinessNature,
    CompanyStatus,
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


class CatalogueNotFoundError(Exception):
    """The Company is not visible within the resolved Tenant."""


class CatalogueInputError(Exception):
    """A supplied catalogue value or relationship is invalid."""


class CatalogueStateConflictError(Exception):
    """The requested catalogue change conflicts with current business state."""


async def _get_company(
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
    tax_rate_id: UUID,
    tax_treatment_id: UUID,
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

    treatment_row = (
        await session.execute(
            select(TaxTreatment, TaxType)
            .join(TaxType, TaxType.id == TaxTreatment.tax_type_id)
            .where(TaxTreatment.id == tax_treatment_id)
        )
    ).one_or_none()
    if treatment_row is None:
        raise CatalogueInputError("Tax Treatment does not exist")
    treatment, treatment_tax_type = treatment_row
    if (
        treatment.status is not TaxReferenceStatus.ACTIVE
        or treatment_tax_type.status is not TaxReferenceStatus.ACTIVE
    ):
        raise CatalogueStateConflictError("Tax Treatment is not active")
    if treatment_tax_type.code != "GST":
        raise CatalogueInputError("Tax Treatment must belong to GST")
    if treatment_tax_type.country_code != treatment.country_code:
        raise CatalogueInputError(
            "Tax Treatment does not match its GST jurisdiction"
        )
    if (
        treatment.tax_type_id != tax_rate.tax_type_id
        or treatment.country_code != tax_rate.country_code
    ):
        raise CatalogueInputError(
            "Tax Rate and Tax Treatment must belong to the same GST jurisdiction"
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
        tax_rate_id=service_data.selected_tax_rate_id,
        tax_treatment_id=service_data.tax_treatment_id,
    )
    service_type = ServiceType(
        company_id=company.id,
        service_category_id=category.id,
        name=service_data.name,
        code=service_data.code,
        description=service_data.description,
        uom=service_data.uom,
        company_hsn_sac_code_id=service_data.company_hsn_sac_code_id,
        selected_tax_rate_id=service_data.selected_tax_rate_id,
        tax_treatment_id=service_data.tax_treatment_id,
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
        tax_rate_id=sku_data.selected_tax_rate_id,
        tax_treatment_id=sku_data.tax_treatment_id,
    )
    sku = Sku(
        company_id=company.id,
        product_id=product.id,
        sku_code=sku_data.sku_code,
        name=sku_data.name,
        description=sku_data.description,
        uom=sku_data.uom,
        company_hsn_sac_code_id=sku_data.company_hsn_sac_code_id,
        selected_tax_rate_id=sku_data.selected_tax_rate_id,
        tax_treatment_id=sku_data.tax_treatment_id,
        tcs_check_required=sku_data.tcs_check_required,
        status=CatalogueStatus.ACTIVE,
    )
    session.add(sku)
    await _commit(session, "SKU conflicts with existing catalogue data")
    await session.refresh(sku)
    return sku
