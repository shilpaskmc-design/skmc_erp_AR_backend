from tests.integration.company_configuration_migration_support import execute, rejected, run_migration_case, seed_company


async def _exercise(url: str) -> None:
    _, company = await seed_company(url)
    sql = "INSERT INTO core.company_user_memberships (company_id, user_subject_id, status) VALUES (:company, 'oidc|user-1', :status)"
    await execute(url, sql, {"company": company, "status": "ACTIVE"})
    await rejected(url, sql, {"company": company, "status": "ACTIVE"})
    await rejected(url, sql, {"company": company, "status": "DRAFT"})
    await rejected(url, "DELETE FROM core.companies WHERE id = :id", {"id": company})


def test_company_access_foundation_migration_contract() -> None:
    run_migration_case("0025_company_access_foundation", "0024_reminder_configuration", ("core.company_user_memberships",), _exercise)
