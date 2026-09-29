from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.ar.delivery.model import CompanyInvoiceDeliverySettings
from skmc_erp.ar.delivery.schema import CompanyInvoiceDeliverySettingsPut
from skmc_erp.core.company.model import Company
from skmc_erp.core.email.model import EmailProviderConfig
from skmc_erp.core.tenant.model import Tenant


class DeliverySettingsInputError(Exception):
    pass


async def _company(session: AsyncSession, tenant: Tenant, company_id: UUID) -> Company:
    company = await session.get(Company, company_id)
    if company is None or company.tenant_id != tenant.id:
        raise DeliverySettingsInputError("Company does not exist")
    return company


async def get_delivery_settings(*, session: AsyncSession, tenant: Tenant, company_id: UUID) -> CompanyInvoiceDeliverySettings | None:
    await _company(session, tenant, company_id)
    return await session.get(CompanyInvoiceDeliverySettings, company_id)


async def put_delivery_settings(*, session: AsyncSession, tenant: Tenant, company_id: UUID, settings_data: CompanyInvoiceDeliverySettingsPut) -> CompanyInvoiceDeliverySettings:
    await _company(session, tenant, company_id)
    if settings_data.email_provider_config_id is not None:
        provider = await session.scalar(
            select(EmailProviderConfig).where(
                EmailProviderConfig.id == settings_data.email_provider_config_id,
                EmailProviderConfig.tenant_id == tenant.id,
                or_(EmailProviderConfig.company_id.is_(None), EmailProviderConfig.company_id == company_id),
            )
        )
        if provider is None:
            raise DeliverySettingsInputError("Email Provider Configuration does not exist")

    settings = await session.get(CompanyInvoiceDeliverySettings, company_id)
    if settings is None:
        settings = CompanyInvoiceDeliverySettings(company_id=company_id)
        session.add(settings)
    for field, value in settings_data.model_dump().items():
        setattr(settings, field, value)
    await session.commit()
    await session.refresh(settings)
    return settings
