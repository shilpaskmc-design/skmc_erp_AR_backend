from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from skmc_erp.ar.catalogue.router import router as catalogue_router
from skmc_erp.ar.currency.router import router as ar_currency_router
from skmc_erp.ar.delivery.router import router as delivery_router
from skmc_erp.ar.document_presentation.router import (
    branding_router as document_branding_router,
)
from skmc_erp.ar.document_presentation.router import (
    router as document_presentation_router,
)
from skmc_erp.ar.fx.router import router as ar_fx_router
from skmc_erp.ar.numbering.router import router as document_numbering_router
from skmc_erp.ar.accounting.router import router as ar_accounting_router
from skmc_erp.ar.compliance.router import router as ar_compliance_router
from skmc_erp.ar.payment_term.router import router as payment_term_router
from skmc_erp.ar.reminder.router import router as reminder_router
from skmc_erp.core.accounting.router import router as gl_account_router
from skmc_erp.core.accounting.router import structure_router as accounting_structure_router
from skmc_erp.core.bank_account.router import router as bank_account_router
from skmc_erp.core.company.router import router as company_router
from skmc_erp.core.company_import.router import router as company_import_router
from skmc_erp.core.cost_center.router import router as cost_center_router
from skmc_erp.core.company_location.router import router as company_location_router
from skmc_erp.core.company_gst_registration.router import (
    router as company_gst_registration_router,
)
from skmc_erp.core.financial_year.router import router as financial_year_router
from skmc_erp.core.fx.router import router as exchange_rate_router
from skmc_erp.core.tax_reference.router import router as tax_reference_router
from skmc_erp.database import engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(
    title="SKMC ERP API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(company_router)
app.include_router(company_import_router)
app.include_router(cost_center_router)
app.include_router(company_location_router)
app.include_router(company_gst_registration_router)
app.include_router(financial_year_router)
app.include_router(catalogue_router)
app.include_router(gl_account_router)
app.include_router(accounting_structure_router)
app.include_router(bank_account_router)
app.include_router(payment_term_router)
app.include_router(ar_currency_router)
app.include_router(ar_accounting_router)
app.include_router(ar_compliance_router)
app.include_router(document_presentation_router)
app.include_router(document_branding_router)
app.include_router(delivery_router)
app.include_router(exchange_rate_router)
app.include_router(ar_fx_router)
app.include_router(document_numbering_router)
app.include_router(reminder_router)
app.include_router(tax_reference_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
