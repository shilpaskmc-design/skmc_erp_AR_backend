from tests.integration.company_configuration_migration_support import execute, rejected, run_migration_case, scalar, seed_company


async def _exercise(url: str) -> None:
    _, company = await seed_company(url)
    policy = await scalar(url, "INSERT INTO ar.reminder_policies (company_id, enabled, send_time) VALUES (:company, true, '09:00') RETURNING id", {"company": company})
    sql = "INSERT INTO ar.reminder_schedule_rules (reminder_policy_id, offset_days, status) VALUES (:policy, :offset, :status)"
    await execute(url, sql, {"policy": policy, "offset": -7, "status": "ACTIVE"})
    await rejected(url, sql, {"policy": policy, "offset": -7, "status": "ACTIVE"})
    await rejected(url, sql, {"policy": policy, "offset": 0, "status": "DRAFT"})
    await rejected(url, "DELETE FROM ar.reminder_policies WHERE id = :id", {"id": policy})


def test_reminder_configuration_migration_contract() -> None:
    run_migration_case("0024_reminder_configuration", "0023_email_delivery_configuration", ("ar.reminder_policies", "ar.reminder_schedule_rules"), _exercise)
