# Company Configuration Module

## Purpose and status

The Company Configuration module supports establishing reusable seller-side Company masters, legal identity, physical locations, GST registrations and LUTs, financial periods, business nature (Services, Goods, Both), catalogues (Services, Goods), HSN/SAC classifications, management-reporting cost centers (Business Segments, Teams, Locations), Payment Terms, Customer Code configuration, AR currencies and bank accounts, document numbering series, document presentation/branding, and email/reminder defaults required before operational AR activities.

**Company Configuration status:** `CURRENT WORKING DESIGN / PROPOSED FOR FREEZE`.

This documentation consolidation does not authorize migrations, SQL scripts, ORM models, APIs, services, routes, frontend work, or tests. `CONFIRMED` decisions govern the current proposal; `OPEN`, `REVIEW`, and `DEFERRED` boundaries retain those statuses.

## Boundaries

- **Tenant** is the SaaS isolation boundary.
- **Organisation** is an optional non-legal grouping of Companies within a Tenant; it supplies no configuration inheritance in MVP.
- **Company** is the legal, billing, tax, and accounting boundary.
- **Core / Shared vs AR-Specific boundary**: shared legal, location, statutory, tax, currency, and accounting identities belong to Core/Shared; AR-specific usage, document numbering, delivery, branding, and reminder policies belong to AR.
- **Customer Code configuration** is owned by Company Configuration; the Customer module only consumes that configuration during `NEW_CUSTOMER` publication.
- No shared Party, Vendor, Contact, or generic Counterparty master is introduced.

## Dependencies

- Shared platform capabilities: Countries, Country Subdivisions, Entity Types, Legal Identifier Types, GST Registration Types, Tax Types, Tax Treatments, Currencies, Stored Files (`stored_files`), and Audit infrastructure.
- Shared module boundaries in [Module Boundaries](../../architecture/module_boundaries.md).
- Shared database design contracts in [database.md](../../requirements/database.md).

## Downstream consumers

- **Customer Onboarding**: consumes Company identity, jurisdiction-scoped legal identifier rules, Payment Terms, and Customer Code configuration.
- **Sales Order & Commercial Setup**: consumes Company, Locations, Catalogues, Currencies, Payment Terms, and Cost Centers.
- **Billing & Invoicing**: consumes Company identity, GSTINs, Locations, Catalogues, HSN/SAC codes and eligible rates, Bank Accounts, AR Document Numbering series, Presentation/Branding, and Delivery settings.
- **Receivables & Receipts**: consumes Base Currency, Bank Accounts, and GL mappings.

## Canonical documents and reading order

1. [Requirements](requirements.md) — functional capabilities and business requirements.
2. [Workflows](workflows.md) — configuration sequence, wizard journey, and activation gates.
3. [Data Model](data_model.md) — canonical 54-table persistence proposal and ERD.
4. [Business Rules](business_rules.md) — domain invariants, ownership, lifecycle, and system rules.
5. [Open Decisions](open_decisions.md) — genuinely unresolved `OPEN` and `REVIEW` items only.

The editable ERD source is [data_model.mmd](data_model.mmd).
