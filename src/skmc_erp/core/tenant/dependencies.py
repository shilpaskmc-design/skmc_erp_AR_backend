from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.config import Settings, get_settings
from skmc_erp.core.tenant.model import Tenant, TenantStatus
from skmc_erp.database import get_db_session


async def get_temporary_tenant_context(
    tenant_id: Annotated[UUID, Header(alias="X-Tenant-ID")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Tenant:
    """Resolve bootstrap-only Tenant context until authentication exists."""
    if settings.environment.strip().casefold() == "production":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Temporary tenant context is unavailable in production",
        )

    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    if tenant.status is not TenantStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tenant is not active",
        )

    return tenant
