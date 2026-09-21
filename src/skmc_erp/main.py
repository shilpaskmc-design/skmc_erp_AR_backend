from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from skmc_erp.ar.catalogue.router import router as catalogue_router
from skmc_erp.core.company.router import router as company_router
from skmc_erp.core.cost_center.router import router as cost_center_router
from skmc_erp.core.company_location.router import router as company_location_router
from skmc_erp.core.company_gst_registration.router import (
    router as company_gst_registration_router,
)
from skmc_erp.core.financial_year.router import router as financial_year_router
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
app.include_router(cost_center_router)
app.include_router(company_location_router)
app.include_router(company_gst_registration_router)
app.include_router(financial_year_router)
app.include_router(catalogue_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
