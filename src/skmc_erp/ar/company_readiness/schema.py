from uuid import UUID

from pydantic import BaseModel

from skmc_erp.core.company.model import CompanyStatus


class ReadinessCheck(BaseModel):
    code: str
    message: str


class CompanyReadinessResponse(BaseModel):
    company_id: UUID
    status: CompanyStatus
    ready_for_activation: bool
    blocking_checks: list[ReadinessCheck]
    passed_checks: list[ReadinessCheck]
    non_blocking_warnings: list[ReadinessCheck]
