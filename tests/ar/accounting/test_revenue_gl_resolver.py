from datetime import date
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from skmc_erp.ar.accounting.schema import RevenueGlMappingCreate
from skmc_erp.ar.accounting.service import (
    AccountingMappingNotFoundError,
    RevenueGlMappingAmbiguityError,
    assign_revenue_gl_mapping,
    end_revenue_gl_mapping,
    inactivate_revenue_gl_mapping,
    resolve_revenue_gl_mapping,
)
from skmc_erp.ar.catalogue.model import CatalogueStatus
from skmc_erp.core.company.model import Company
from skmc_erp.core.tenant.model import Tenant
from tests.integration.test_ar_accounting_mappings_api import api_context, migrated_database  # noqa: F401


async def _seed_test_env(session: AsyncSession):
    tenant = Tenant(name=f"Tenant {uuid4()}", status="ACTIVE")
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    tenant_id = tenant.id
    session.expunge(tenant)

    company = Company(
        tenant_id=tenant_id,
        legal_name=f"Company {uuid4()}",
        status="DRAFT",
    )
    session.add(company)
    await session.commit()
    await session.refresh(company)
    company_id = company.id

    # GL Accounts
    gl1 = await _create_gl(session, company_id, "4101")
    gl2 = await _create_gl(session, company_id, "4102")
    gl3 = await _create_gl(session, company_id, "4103")
    gl4 = await _create_gl(session, company_id, "4104")

    # Service Types
    st1 = await _create_service_type(session, company_id, "IT Consulting")
    st2 = await _create_service_type(session, company_id, "Legal Advisory")

    # SKUs
    sku1 = await _create_sku(session, company_id, "SKU-SERVER")
    sku2 = await _create_sku(session, company_id, "SKU-LAPTOP")

    # Locations
    loc_noida = await _create_location(session, company_id, "Noida")
    loc_mumbai = await _create_location(session, company_id, "Mumbai")

    return {
        "tenant": tenant,
        "company_id": company_id,
        "gl1": gl1,
        "gl2": gl2,
        "gl3": gl3,
        "gl4": gl4,
        "st1": st1,
        "st2": st2,
        "sku1": sku1,
        "sku2": sku2,
        "loc_noida": loc_noida,
        "loc_mumbai": loc_mumbai,
    }


async def _create_gl(session: AsyncSession, company_id, code):
    from skmc_erp.core.accounting.model import GlAccount
    gl = GlAccount(company_id=company_id, account_code=f"GL-{code}-{uuid4()}"[:20], account_name=f"GL {code}", valid_from=date(2025, 1, 1), status="ACTIVE")
    session.add(gl)
    await session.commit()
    await session.refresh(gl)
    return gl.id


async def _create_service_type(session: AsyncSession, company_id, name):
    from skmc_erp.ar.catalogue.model import ServiceCategory, ServiceType
    from skmc_erp.core.geography.model import Country
    from skmc_erp.core.tax_reference.model import (
        CompanyHsnSacCode,
        TaxRate,
        TaxTreatment,
        TaxType,
    )

    await session.merge(Country(code="IN", name="India", status="ACTIVE"))
    cat = ServiceCategory(company_id=company_id, name=f"Cat {uuid4()}", status=CatalogueStatus.ACTIVE)
    session.add(cat)
    sac = CompanyHsnSacCode(
        company_id=company_id,
        classification_type="SAC",
        code=str(uuid4().int)[:6],
        description="IT consulting services",
        status="ACTIVE",
    )
    session.add(sac)
    tax_type = TaxType(
        code=f"GST-{uuid4()}"[:30],
        name="Goods and Services Tax",
        country_code="IN",
        status="ACTIVE",
    )
    session.add(tax_type)
    await session.flush()
    tr = TaxRate(
        tax_type_id=tax_type.id,
        country_code="IN",
        rate_percent=18.0,
        status="ACTIVE",
    )
    session.add(tr)
    tt = TaxTreatment(
        country_code="IN",
        code=f"TT-{uuid4()}"[:20],
        name="Taxable",
        tax_type_id=tax_type.id,
        status="ACTIVE",
    )
    session.add(tt)
    await session.flush()
    service_category_id = cat.id
    hsn_sac_code_id = sac.id
    tax_rate_id = tr.id
    tax_treatment_id = tt.id
    await session.commit()

    st = ServiceType(
        company_id=company_id,
        service_category_id=service_category_id,
        name=name,
        company_hsn_sac_code_id=hsn_sac_code_id,
        selected_tax_rate_id=tax_rate_id,
        tax_treatment_id=tax_treatment_id,
        status=CatalogueStatus.ACTIVE,
    )
    session.add(st)
    await session.commit()
    await session.refresh(st)
    return st.id


async def _create_sku(session: AsyncSession, company_id, code):
    from skmc_erp.ar.catalogue.model import Product, ProductCategory, Sku
    from skmc_erp.core.geography.model import Country
    from skmc_erp.core.tax_reference.model import (
        CompanyHsnSacCode,
        TaxRate,
        TaxTreatment,
        TaxType,
    )

    await session.merge(Country(code="IN", name="India", status="ACTIVE"))
    cat = ProductCategory(company_id=company_id, name=f"ProdCat {uuid4()}", status=CatalogueStatus.ACTIVE)
    session.add(cat)
    await session.flush()
    p = Product(company_id=company_id, product_category_id=cat.id, name=f"Prod {uuid4()}", status=CatalogueStatus.ACTIVE)
    session.add(p)
    sac = CompanyHsnSacCode(
        company_id=company_id,
        classification_type="HSN",
        code=str(uuid4().int)[:8],
        description="Portable computers",
        status="ACTIVE",
    )
    session.add(sac)
    tax_type = TaxType(
        code=f"GST-{uuid4()}"[:30],
        name="Goods and Services Tax",
        country_code="IN",
        status="ACTIVE",
    )
    session.add(tax_type)
    await session.flush()
    tr = TaxRate(
        tax_type_id=tax_type.id,
        country_code="IN",
        rate_percent=18.0,
        status="ACTIVE",
    )
    session.add(tr)
    tt = TaxTreatment(
        country_code="IN",
        code=f"TT-{uuid4()}"[:20],
        name="Taxable",
        tax_type_id=tax_type.id,
        status="ACTIVE",
    )
    session.add(tt)
    await session.flush()
    product_id = p.id
    hsn_sac_code_id = sac.id
    tax_rate_id = tr.id
    tax_treatment_id = tt.id
    await session.commit()

    sku = Sku(
        company_id=company_id,
        product_id=product_id,
        sku_code=f"SKU-{uuid4()}"[:20],
        name=f"SKU {code}",
        uom="NOS",
        company_hsn_sac_code_id=hsn_sac_code_id,
        selected_tax_rate_id=tax_rate_id,
        tax_treatment_id=tax_treatment_id,
        status=CatalogueStatus.ACTIVE,
    )
    session.add(sku)
    await session.commit()
    await session.refresh(sku)
    return sku.id


async def _create_location(session: AsyncSession, company_id, name):
    from skmc_erp.core.company_location.model import CompanyLocation
    from skmc_erp.core.geography.model import Country

    await session.merge(Country(code="IN", name="India", status="ACTIVE"))
    loc = CompanyLocation(
        company_id=company_id,
        location_name=name,
        address_line_1="Addr 1",
        city="City",
        country_code="IN",
        is_branch=True,
        status="ACTIVE",
    )
    session.add(loc)
    await session.commit()
    await session.refresh(loc)
    return loc.id


@pytest.mark.asyncio
async def test_resolver_fixed_precedence_tiers(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI]
):
    _, engine, _ = api_context
    async with AsyncSession(engine) as session:
        e = await _seed_test_env(session)
        tenant, company_id = e["tenant"], e["company_id"]
        st1, gl1, gl2, gl3, gl4 = e["st1"], e["gl1"], e["gl2"], e["gl3"], e["gl4"]
        loc_noida = e["loc_noida"]

        # Tier 1: Consulting + B2B + Noida -> GL1
        await assign_revenue_gl_mapping(
            session, tenant, company_id,
            RevenueGlMappingCreate(service_type_id=st1, supply_type_code="B2B", company_location_id=loc_noida, gl_account_id=gl1, valid_from=date(2026, 1, 1))
        )
        # Tier 2: Consulting + B2B + NULL -> GL2
        await assign_revenue_gl_mapping(
            session, tenant, company_id,
            RevenueGlMappingCreate(service_type_id=st1, supply_type_code="B2B", company_location_id=None, gl_account_id=gl2, valid_from=date(2026, 1, 1))
        )
        # Tier 3: Consulting + NULL + Noida -> GL3
        await assign_revenue_gl_mapping(
            session, tenant, company_id,
            RevenueGlMappingCreate(service_type_id=st1, supply_type_code=None, company_location_id=loc_noida, gl_account_id=gl3, valid_from=date(2026, 1, 1))
        )
        # Tier 4: Consulting + NULL + NULL -> GL4
        await assign_revenue_gl_mapping(
            session, tenant, company_id,
            RevenueGlMappingCreate(service_type_id=st1, supply_type_code=None, company_location_id=None, gl_account_id=gl4, valid_from=date(2026, 1, 1))
        )

        # 39. Item + Supply + Location wins (Tier 1)
        res1 = await resolve_revenue_gl_mapping(session, tenant, company_id, service_type_id=st1, sku_id=None, supply_type_code="B2B", company_location_id=loc_noida, effective_on=date(2026, 6, 1))
        assert res1.gl_account_id == gl1

        # 40. Item + Supply wins over Item + Location (Tier 2 beats Tier 3 when location is Mumbai)
        res2 = await resolve_revenue_gl_mapping(session, tenant, company_id, service_type_id=st1, sku_id=None, supply_type_code="B2B", company_location_id=e["loc_mumbai"], effective_on=date(2026, 6, 1))
        assert res2.gl_account_id == gl2

        # 41. Item + Location wins when Supply is B2C (no Tier 1 or Tier 2 match) -> Tier 3
        res3 = await resolve_revenue_gl_mapping(session, tenant, company_id, service_type_id=st1, sku_id=None, supply_type_code="B2C", company_location_id=loc_noida, effective_on=date(2026, 6, 1))
        assert res3.gl_account_id == gl3

        # 42. Item only is final fallback (B2C + Mumbai) -> Tier 4
        res4 = await resolve_revenue_gl_mapping(session, tenant, company_id, service_type_id=st1, sku_id=None, supply_type_code="B2C", company_location_id=e["loc_mumbai"], effective_on=date(2026, 6, 1))
        assert res4.gl_account_id == gl4


@pytest.mark.asyncio
async def test_resolver_item_cross_fallback_prohibited(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI]
):
    _, engine, _ = api_context
    async with AsyncSession(engine) as session:
        e = await _seed_test_env(session)
        tenant, company_id = e["tenant"], e["company_id"]
        st1, sku1, gl1 = e["st1"], e["sku1"], e["gl1"]

        await assign_revenue_gl_mapping(
            session, tenant, company_id,
            RevenueGlMappingCreate(service_type_id=st1, gl_account_id=gl1, valid_from=date(2026, 1, 1))
        )

        # 43. Service Type rule never matches SKU request
        with pytest.raises(AccountingMappingNotFoundError):
            await resolve_revenue_gl_mapping(session, tenant, company_id, service_type_id=None, sku_id=sku1, supply_type_code=None, company_location_id=None, effective_on=date(2026, 6, 1))

        # 44. SKU rule never matches Service Type request
        sku_gl = e["gl2"]
        await assign_revenue_gl_mapping(
            session, tenant, company_id,
            RevenueGlMappingCreate(sku_id=sku1, gl_account_id=sku_gl, valid_from=date(2026, 1, 1))
        )
        with pytest.raises(AccountingMappingNotFoundError):
            await resolve_revenue_gl_mapping(session, tenant, company_id, service_type_id=e["st2"], sku_id=None, supply_type_code=None, company_location_id=None, effective_on=date(2026, 6, 1))


@pytest.mark.asyncio
async def test_resolver_effective_dates_and_status(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI]
):
    _, engine, _ = api_context
    async with AsyncSession(engine) as session:
        e = await _seed_test_env(session)
        tenant, company_id = e["tenant"], e["company_id"]
        st1, gl1 = e["st1"], e["gl1"]

        # Mapping valid from 2026-03-01 to 2026-06-30
        m = await assign_revenue_gl_mapping(
            session, tenant, company_id,
            RevenueGlMappingCreate(service_type_id=st1, gl_account_id=gl1, valid_from=date(2026, 3, 1), valid_to=date(2026, 6, 30))
        )

        # 47. Future mapping before valid_from -> ignored
        with pytest.raises(AccountingMappingNotFoundError):
            await resolve_revenue_gl_mapping(session, tenant, company_id, service_type_id=st1, sku_id=None, supply_type_code=None, company_location_id=None, effective_on=date(2026, 2, 28))

        # 45. Effective date inside range -> matches
        res = await resolve_revenue_gl_mapping(session, tenant, company_id, service_type_id=st1, sku_id=None, supply_type_code=None, company_location_id=None, effective_on=date(2026, 4, 15))
        assert res.id == m.id

        # 46. Expired mapping after valid_to -> ignored
        with pytest.raises(AccountingMappingNotFoundError):
            await resolve_revenue_gl_mapping(session, tenant, company_id, service_type_id=st1, sku_id=None, supply_type_code=None, company_location_id=None, effective_on=date(2026, 7, 1))

        # 48. Inactive mapping -> ignored
        await inactivate_revenue_gl_mapping(session, tenant, company_id, m.id)
        with pytest.raises(AccountingMappingNotFoundError):
            await resolve_revenue_gl_mapping(session, tenant, company_id, service_type_id=st1, sku_id=None, supply_type_code=None, company_location_id=None, effective_on=date(2026, 4, 15))


@pytest.mark.asyncio
async def test_resolver_missing_runtime_criteria(
    api_context: tuple[AsyncClient, AsyncEngine, FastAPI]
):
    _, engine, _ = api_context
    async with AsyncSession(engine) as session:
        e = await _seed_test_env(session)
        tenant, company_id = e["tenant"], e["company_id"]
        st1, gl1 = e["st1"], e["gl1"]

        # Rule requires Supply B2B
        await assign_revenue_gl_mapping(
            session, tenant, company_id,
            RevenueGlMappingCreate(service_type_id=st1, supply_type_code="B2B", gl_account_id=gl1, valid_from=date(2026, 1, 1))
        )

        # 53. Runtime missing Supply Type cannot match a Supply-specific rule
        with pytest.raises(AccountingMappingNotFoundError):
            await resolve_revenue_gl_mapping(session, tenant, company_id, service_type_id=st1, sku_id=None, supply_type_code=None, company_location_id=None, effective_on=date(2026, 6, 1))

        # 49. Specific Supply rule does not match different Supply B2C
        with pytest.raises(AccountingMappingNotFoundError):
            await resolve_revenue_gl_mapping(session, tenant, company_id, service_type_id=st1, sku_id=None, supply_type_code="B2C", company_location_id=None, effective_on=date(2026, 6, 1))
