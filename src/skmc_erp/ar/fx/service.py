from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.ar.fx.model import FXPolicy, FXPolicyPurpose
from skmc_erp.ar.fx.schema import FXPolicyPut
from skmc_erp.core.company.model import Company
from skmc_erp.core.tenant.model import Tenant


class FXPolicyInputError(Exception):
    pass


async def _company(session: AsyncSession, tenant: Tenant, company_id: UUID) -> Company:
    company = await session.get(Company, company_id)
    if company is None or company.tenant_id != tenant.id:
        raise FXPolicyInputError("Company does not exist")
    return company


async def list_fx_policies(*, session: AsyncSession, tenant: Tenant, company_id: UUID) -> Sequence[FXPolicy]:
    await _company(session, tenant, company_id)
    result = await session.scalars(select(FXPolicy).where(FXPolicy.company_id == company_id).order_by(FXPolicy.purpose))
    return result.all()


async def get_fx_policy(*, session: AsyncSession, tenant: Tenant, company_id: UUID, purpose: FXPolicyPurpose) -> FXPolicy | None:
    await _company(session, tenant, company_id)
    return await session.scalar(select(FXPolicy).where(FXPolicy.company_id == company_id, FXPolicy.purpose == purpose))


async def put_fx_policy(*, session: AsyncSession, tenant: Tenant, company_id: UUID, purpose: FXPolicyPurpose, policy_data: FXPolicyPut) -> FXPolicy:
    policy = await get_fx_policy(session=session, tenant=tenant, company_id=company_id, purpose=purpose)
    if policy is None:
        policy = FXPolicy(company_id=company_id, purpose=purpose)
        session.add(policy)
    for field, value in policy_data.model_dump().items():
        setattr(policy, field, value)
    await session.commit()
    await session.refresh(policy)
    return policy
