from tests.integration.company_configuration_migration_support import execute, rejected, run_migration_case, scalar, seed_company


async def _exercise(url: str) -> None:
    tenant, company = await seed_company(url)
    provider = await scalar(url, "INSERT INTO core.email_provider_configs (tenant_id, company_id, provider_type, sender_identity, secret_reference, status) VALUES (:tenant, :company, 'SMTP', 'billing@example.com', 'secret/ref', 'ACTIVE') RETURNING id", {"tenant": tenant, "company": company})
    await execute(url, "INSERT INTO ar.company_invoice_delivery_settings (company_id, automatic_sending_enabled, email_provider_config_id, sender_email) VALUES (:company, true, :provider, 'billing@example.com')", {"company": company, "provider": provider})
    await rejected(url, "INSERT INTO core.email_provider_configs (tenant_id, provider_type, sender_identity, secret_reference, status) VALUES (:tenant, 'SMTP', 'x@example.com', 'x', 'DRAFT')", {"tenant": tenant})
    await rejected(url, "DELETE FROM core.email_provider_configs WHERE id = :id", {"id": provider})


def test_email_delivery_configuration_migration_contract() -> None:
    run_migration_case("0023_email_delivery_configuration", "0022_file_document_presentation", ("core.email_provider_configs", "ar.company_invoice_delivery_settings"), _exercise)
