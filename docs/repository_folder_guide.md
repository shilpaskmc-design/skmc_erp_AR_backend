# SKMC ERP Repository Folder Guide

## 1. Purpose of This Document

This document answers one practical question: **“What lives where, and why?”** It maps the repository’s current meaningful folders to their technical responsibility, business purpose, important contents, ownership limits, and relationships with other modules.

It describes the repository as it exists now. It does not treat proposed features or untracked local artifacts as current repository structure.

---

## 2. Repository Big Picture

```text
skmc_erp_AR_backend/
├── alembic/          # PostgreSQL database schema migrations
├── docs/             # Product, requirements, architecture, and decisions
├── src/              # Backend application source
│   └── skmc_erp/
│       ├── core/     # Shared/Core ERP domains
│       └── ar/       # Accounts Receivable domains
├── tests/            # Automated unit, model, API, and migration tests
├── .env.example      # Safe example of required runtime environment variables
├── .gitignore        # Files and generated artifacts excluded from Git
├── AGENTS.md         # Repository working and governance rules
├── alembic.ini       # Alembic command and logging configuration
└── pyproject.toml    # Python project, dependencies, build, and pytest config
```

The repository is a **modular monolith**. `src/skmc_erp/core/` supplies reusable Company and platform capabilities. `src/skmc_erp/ar/` supplies AR-specific configuration and behavior and may depend on Core. Core must not depend on AR-specific behavior.

Generated environments and caches such as `.venv/`, `__pycache__/`, and `.pytest_cache/`, plus IDE metadata and unrelated local files, are intentionally outside this guide.

---

## 3. Repository Root

| Path | Responsibility and business purpose | Important contents / relationships | Must not own |
|---|---|---|---|
| `alembic/` | Versioned PostgreSQL schema evolution. It converts approved persistence changes into an ordered, reversible database history. | Uses application model metadata and `alembic.ini`; detailed in Section 6. | Product policy or business rules that have not first been approved in requirements. |
| `docs/` | Governing product context, feature requirements, architecture boundaries, decisions, implementation evidence, and change history. | `docs/README.md` explains authority and the minimal-reading strategy; detailed in Section 8. | Runtime application logic or executable database migrations. |
| `src/` | Installable Python source tree. | Contains the `skmc_erp` application package; detailed in Sections 4 and 5. | Tests, migration history, or duplicated requirements documentation. |
| `tests/` | Automated evidence for models, validation, services, APIs, and PostgreSQL migrations. | Mirrors Core and AR domains and has a separate integration suite; detailed in Section 7. | Production business logic used to make the application work. |
| `AGENTS.md` | Repository-wide working rules: documentation authority, architecture guardrails, change discipline, testing, and reporting expectations. | Read before making repository changes. | Feature-specific requirements. |
| `pyproject.toml` | Python 3.12 project metadata, runtime/dev dependencies, Hatch build settings, package discovery, and pytest configuration. | Builds `src/skmc_erp`; pytest searches `tests/` and uses automatic asyncio mode. | Environment secrets or deployment-specific values. |
| `alembic.ini` | Alembic CLI and migration logging configuration. | Points Alembic at `alembic/`; the runtime URL is supplied through application settings. | Credentials committed to source control. |
| `.env.example` | Safe template for `DATABASE_URL`, application identity, environment, and Company-import signing-key settings. | Copy to a local `.env` and replace placeholders. | Real credentials, production secrets, or test results. |
| `.gitignore` | Keeps local environments, secrets, caches, coverage data, and build outputs out of version control. | Applies across the repository. | Rules that hide source, migrations, requirements, or tests that should be reviewed. |

---

## 4. Application Package: `src/skmc_erp/`

```text
src/skmc_erp/
├── __init__.py
├── config.py
├── database.py
├── main.py
├── model_base.py
├── core/
│   ├── access/
│   ├── accounting/
│   ├── bank_account/
│   ├── company/
│   ├── company_gst_registration/
│   ├── company_identifier/
│   ├── company_import/
│   ├── company_location/
│   ├── cost_center/
│   ├── currency/
│   ├── email/
│   ├── entity_type/
│   ├── file_storage/
│   ├── financial_year/
│   ├── fx/
│   ├── geography/
│   ├── organisation/
│   ├── tax_reference/
│   ├── tenant/
│   └── uom/
└── ar/
    ├── accounting/
    ├── catalogue/
    ├── company_readiness/
    ├── compliance/
    ├── currency/
    ├── delivery/
    ├── document_presentation/
    ├── fx/
    ├── numbering/
    ├── payment_term/
    └── reminder/
```

### 4.1 Package-level files

| File | Responsibility | Relationship / ownership limit |
|---|---|---|
| `__init__.py` | Marks `skmc_erp` as a Python package. | It is not a service locator or a place for domain behavior. |
| `config.py` | Defines environment-backed application settings and the cached settings accessor. | Reads values such as `DATABASE_URL`; must not contain committed secrets or feature rules. |
| `database.py` | Creates the async SQLAlchemy engine/session factory and request-scoped session dependency. | Provides database plumbing to all modules; services remain responsible for business transactions and commits. |
| `main.py` | Creates the FastAPI application, registers current Core and AR routers, exposes `/health`, and disposes the engine during shutdown. | Composition root only; domain rules belong in feature services and schemas. |
| `model_base.py` | Defines the shared SQLAlchemy declarative `Base`. | All ORM models share its metadata, which Alembic imports through `alembic/env.py`. |

### 4.2 Feature-module file convention

Most feature folders use the following files. A missing layer is intentional when the current module only supplies persistence or reference data.

| File | Normal role |
|---|---|
| `__init__.py` | Python package marker and, in many modules, a short ownership description. |
| `model.py` | SQLAlchemy ORM entities, enums, database constraints, and relationships for the module. |
| `schema.py` | Pydantic request/response contracts and input validation. |
| `service.py` | Business operations, cross-entity validation, state changes, and transaction orchestration. |
| `router.py` | FastAPI endpoints, dependency wiring, HTTP status codes, and translation of service errors. |

Routers call services; services use models; schemas define the API boundary. `main.py` registers routers. Alembic imports model modules so `Base.metadata` represents the whole implemented schema.

---

## 5. Domain Modules

### 5.1 Core/Shared: `src/skmc_erp/core/`

Core owns reusable Tenant, Company, legal/statutory identity, shared accounting, and platform-level reference capabilities. AR can consume these modules. Core must not import AR-specific behavior merely for convenience.

| Folder | What it owns and why | Important current files | What it must not own / key relationships |
|---|---|---|---|
| `access/` | Company-to-user membership persistence used to establish Company access scope. | `model.py` (`CompanyUserMembership`). | Authentication-provider login, AR permissions, or the assumption that Company context alone grants business authorization. Relates users to `company/`. |
| `accounting/` | Shared Company accounting identities and configuration: GL accounts, account hierarchies/groups, dated group relationships/mappings, and accounting settings. | `model.py`, `schema.py`, `service.py`, `router.py`; exposes GL-account and accounting-structure APIs. | AR-specific revenue/tax mapping lives in `ar/accounting/`; journal posting, ledgers, closing, and reconciliation remain outside the current AR implementation. |
| `bank_account/` | Company bank-account master data and lifecycle validation. | Standard model/schema/service/router stack. | Receipts, knock-off/allocation, or payment execution. Those are transaction concerns, while AR may reference these bank accounts. |
| `company/` | Canonical Company identity, business nature, lifecycle status, and legal-name history. | Standard stack; `model.py` contains `Company` and `CompanyLegalNameVersion`. | Tenant identity, AR readiness policy, catalogue data, or module-specific configuration. It is referenced by almost every Company-scoped module. |
| `company_gst_registration/` | GST-registration types and Company GST registrations. | Standard stack; persistence in `model.py`, Company-scoped API in `router.py`. | LUTs, invoice tax calculation, or a generic tax engine. `ar/compliance/` owns LUT configuration and AR uses registrations as inputs. |
| `company_identifier/` | Jurisdiction-specific identifier types, Company identifier values, and Entity-Type-to-Identifier requirement rules. | `model.py` currently provides `CompanyIdentifierType`, `CompanyIdentifier`, and `EntityTypeIdentifierRule`. | GST-registration records or AR activation orchestration. `ar/company_readiness/` reads these models when evaluating identity readiness. |
| `company_import/` | Company Configuration Excel import preview/apply workflow and its validation boundary. | `router.py`, `schema.py`, `service.py`; `workbook.py` safely parses the workbook; `token.py` signs and validates preview tokens. | A generic import engine, ownership of imported domain entities, or bypassing their invariants. It orchestrates the relevant Company, fiscal-year, location, and GST modules. |
| `company_location/` | Company locations, registered-office flags, stable location codes, and version history for location truth. | Standard stack; `model.py` includes `CompanyLocation` and `CompanyLocationVersion`. | Cost-centre dimensions, GST registrations, or AR delivery behavior. Those modules reference locations through explicit relationships. |
| `cost_center/` | Company cost-centre configuration, business segments, cost-centre teams, team assignments, location cost centres, and Company settings. | Standard stack. | AR revenue mapping or accounting postings. AR catalogue and mapping modules may reference its business segments. |
| `currency/` | Shared currency reference data and Company reporting-currency associations. | `model.py` (`Currency`, `CompanyReportingCurrency`). | AR-enabled Billing/Receipt currencies (`ar/currency/`) or exchange rates (`core/fx/`). |
| `email/` | Shared email-provider configuration metadata and reusable email-address validation. | `model.py`, `validator.py`. | Invoice-delivery preferences, reminder policy, provider-specific send orchestration, or durable delivery jobs. |
| `entity_type/` | Jurisdiction-scoped legal Entity Type reference data. | `model.py` (`EntityType`). | Company-specific identifier values. It is referenced by `company/` and `company_identifier/`. |
| `file_storage/` | Provider-neutral metadata for Company-owned stored files, including object key, hash, type, size, and original filename. | `model.py` (`StoredFile`). | Binary file contents or provider-specific storage APIs. AR document branding references stored-file metadata; binaries belong in object storage. |
| `financial_year/` | Company fiscal settings and Financial Year definitions/lifecycle. | Standard stack; `model.py` contains `CompanyFiscalSettings` and `FinancialYear`. | Ledger close, posting, or historical-period exception workflows. Other configuration modules can reference Financial Years. |
| `fx/` | Shared, dated exchange-rate facts and rate types. | Standard stack around `ExchangeRate`. | AR policy about which rate to use; that belongs in `ar/fx/`. |
| `geography/` | Shared Country and Country Subdivision reference masters. | `model.py`. | Company addresses or tax behavior. `company/`, `company_location/`, and identifier/GST modules reference these masters. |
| `organisation/` | Optional Tenant-scoped grouping identity above Companies. | `model.py` (`Organisation`). | Tenant ownership, Company configuration, or AR transactions. It groups rather than replaces those identities. |
| `tax_reference/` | Shared tax reference masters and Company HSN/SAC configuration: tax types/rates/treatments, statutory codes/rates, and HSN/SAC-to-rate mappings. | Standard stack; current router exposes Company HSN/SAC APIs. | Invoice tax-outcome resolution, AR tax-to-GL mapping, or a generic rules engine. `ar/catalogue/` and `ar/accounting/` consume these references. |
| `tenant/` | Top-level SaaS Tenant identity and temporary request Tenant-context dependency. | `model.py`, `dependencies.py`. | Company-level permission or business authorization. Tenant ownership is the outer isolation boundary. |
| `uom/` | Shared Unit of Measure reference master and reusable code validation/service behavior. | `model.py`, `schema.py`, `service.py`. | Product/SKU ownership; catalogue records reference UOM codes. |

### 5.2 Accounts Receivable: `src/skmc_erp/ar/`

AR owns AR-specific commercial, Billing-support, receivable-configuration, delivery, reminder, compliance, and accounting-mapping behavior. It may depend on Core/Shared identities and facts.

| Folder | What it owns and why | Important current files | What it must not own / key relationships |
|---|---|---|---|
| `accounting/` | AR tax-GL and revenue-GL mappings, their effective-dated lifecycle, and revenue-account resolution. | Standard stack; `model.py` contains `RevenueGlMapping` and `TaxGlAccountMapping`. | The GL-account master/CoA (`core/accounting/`) or future journal/ledger posting. It maps AR commercial/tax concepts to Core GL accounts. |
| `catalogue/` | Company-owned services and goods catalogue: service categories/types, product categories/products, and SKUs, including business-segment and tax-reference configuration. | Standard stack; five principal catalogue models. | Shared UOM, tax, Company, or cost-centre masters; it references the relevant Core modules. It also does not own transaction-level Billing tax outcomes. |
| `company_readiness/` | Derived AR Company readiness evaluation and guarded activation orchestration across implemented configuration. | `schema.py`, `service.py`, `router.py`; deliberately has no model because readiness is computed rather than stored. | The underlying Company/Core masters or a generic workflow engine. It reads Core and AR configuration and can create approved defaults while activating a Company. |
| `compliance/` | AR Letter of Undertaking (LUT) configuration tied to Company GST registration and Financial Year. | Standard stack around `CompanyLut`. | GST-registration ownership, general tax masters, or invoice tax calculation. Those live in Core or future Billing behavior. |
| `currency/` | Currencies enabled for AR Billing/Receipts at a Company, with AR-specific settings. | Standard stack around `CompanyARCurrency`. | Global currency reference data (`core/currency/`) or rate facts/policies (`core/fx/`, `ar/fx/`). |
| `delivery/` | Company invoice-delivery preferences. | Standard stack around `CompanyInvoiceDeliverySettings`. | Shared email-provider credentials, actual message sending, or retry/outbox workers. It represents AR delivery configuration only. |
| `document_presentation/` | Billing document template selection and versioned Company branding. | Standard stack plus `registry.py` for supported Billing-template keys. | File binaries (`core/file_storage/`) or invoice-generation transactions. It references stored-file metadata for assets. |
| `fx/` | AR policy for selecting an exchange-rate type by purpose. | Standard stack around `FXPolicy`. | Exchange-rate facts, which live in `core/fx/`. |
| `numbering/` | AR document sequences and optional sequence conditions for supported document types. | Standard stack; `DocumentSequence` and `DocumentSequenceCondition`. | A universal numbering/rules engine or ownership of the documents being numbered. Billing/credit/debit documents consume this configuration. |
| `payment_term/` | Company Payment Term definitions used by AR commercial and Billing flows. | Standard stack around `PaymentTerm`. | Customer agreements, invoices, receivables, or collection transactions. Those use Payment Terms but own their own state. |
| `reminder/` | AR reminder policy and schedule-rule configuration. | Standard stack; `ReminderPolicy` and `ReminderScheduleRule`. | Reminder execution, email delivery infrastructure, or receivable balances. It configures future AR reminder behavior. |

### 5.3 Dependency direction

```text
FastAPI composition (main.py)
        │
        ├── Core routers ──> Core services ──> Core models
        │
        └── AR routers ────> AR services ────> AR models
                                  │
                                  └──────────> Core services/models

Allowed:   AR -> Core/Shared
Forbidden: Core/Shared -> AR-specific behavior
```

Cross-module database references should point to the owning identity rather than duplicate it. For example, AR mappings reference Core GL accounts, AR currencies reference Core currency codes, and document branding references Core stored-file metadata.

---

## 6. Database Migrations: `alembic/`

```text
alembic/
├── README             # Alembic environment note
├── env.py             # Async PostgreSQL migration environment and model imports
├── script.py.mako     # Template used when generating a revision
└── versions/          # Ordered migration revision files
```

- `env.py` loads runtime database settings, imports implemented Core and AR model modules, exposes `Base.metadata`, supports offline/online migration modes, and preserves enough space for descriptive Alembic revision identifiers.
- `versions/` is the authoritative executable schema history. Revision files own upgrade/downgrade mechanics and database constraints; they do not independently approve product behavior.
- Migration tests use a disposable PostgreSQL database. Processes that migrate the same test database must run serially.

The current linear history ends at Alembic head `0034_company_identifier_foundation`. The current revision files are:

```text
0001_create_core_tenants.py
0002_create_core_entity_types.py
0003_create_core_company_identity.py
0004_create_core_geographic_masters.py
0005_create_core_company_locations.py
0006_create_core_financial_years.py
0007_create_core_company_gst_registrations.py
0008_create_core_tax_reference.py
0009_create_ar_catalogue.py
0010_create_core_cost_center_configuration.py
0011_create_ar_payment_terms.py
0012_create_core_gl_accounts.py
0013_create_core_company_bank_accounts.py
0014_create_company_currency_configuration.py
0015_create_exchange_rates_fx_policies.py
0016_create_account_hierarchies_account_groups.py
0017_create_account_group_relationships.py
0018_create_gl_account_group_mappings.py
0019_create_tax_statutory_codes_rates.py
0020_create_accounting_configuration.py
0021_create_company_luts.py
0022_create_file_document_presentation.py
0023_create_email_delivery_configuration.py
0024_create_reminder_configuration.py
0025_create_company_access_foundation.py
0026_create_company_location_versions.py
0027_align_company_document_presentation.py
0028_revenue_gl_mapping_enhancement.py
0029_create_document_numbering_configuration.py
0030_create_company_legal_name_history.py
0031_uom_and_bank_account_hardening.py
0032_company_location_codes.py
0033_catalogue_base_gst_nature.py
0034_create_company_identifier_foundation.py
```

New persistence belongs in the owning feature module’s `model.py` and in a new Alembic revision after the governing requirement is approved. Do not edit old applied revisions merely to make the current model look cleaner.

---

## 7. Automated Tests: `tests/`

```text
tests/
├── __init__.py
├── ar/                     # Focused tests mirroring AR modules
│   ├── accounting/
│   ├── catalogue/
│   ├── currency/
│   ├── document_presentation/
│   ├── fx/
│   ├── numbering/
│   └── payment_term/
├── company_configuration/ # Cross-module Company Configuration tests
├── core/                   # Focused tests mirroring Core modules
│   ├── accounting/
│   ├── bank_account/
│   ├── company/
│   ├── company_gst_registration/
│   ├── company_identifier/
│   ├── company_import/
│   ├── company_location/
│   ├── cost_center/
│   ├── currency/
│   ├── entity_type/
│   ├── financial_year/
│   ├── fx/
│   ├── geography/
│   ├── organisation/
│   ├── tax_reference/
│   ├── tenant/
│   └── uom/
└── integration/            # Live PostgreSQL migration and API tests
```

| Folder | Responsibility | Relationship / ownership limit |
|---|---|---|
| `tests/core/` | Fast, focused evidence for Core models, schemas, validation, and services. Its subfolders mirror current Core domains that have focused tests. | Tests production behavior; shared fixtures/helpers must not become hidden production implementations. |
| `tests/ar/` | Fast, focused evidence for AR models, schemas, validation, and resolver behavior. | Mirrors AR ownership and may use Core objects as dependencies. |
| `tests/company_configuration/` | Cross-module schema/model checks for grouped Company Configuration batches and foundations. | Supplements, rather than replaces, domain-specific and PostgreSQL integration tests. |
| `tests/integration/` | End-to-end evidence for Alembic upgrade/downgrade behavior, PostgreSQL constraints, and FastAPI endpoints against the real database engine. | Requires `TEST_DATABASE_URL` for DB-backed cases. The target must be the disposable database expected by each test, and migration processes must not run concurrently against one database. |
| `tests/integration/company_configuration_migration_support.py` | Shared helper for safe Company Configuration migration cases, including empty-database checks, revision transitions, cleanup, and URL validation. | Test-only support; not imported by application code. |

`pyproject.toml` makes `tests/` the pytest root and enables async tests. A skipped DB-backed test normally means `TEST_DATABASE_URL` was not provided; it is not evidence that the PostgreSQL behavior passed.

---

## 8. Documentation: `docs/`

```text
docs/
├── modules/accounting/data_model.md
├── modules/accounting/data_model.mmd
├── README.md
├── PRODUCT_OVERVIEW.md
├── AR_MVP_ARCHITECTURE.md
├── history/repository_implementation_status_2026-09-10.md
├── repository_folder_guide.md
├── CHANGELOG.md
├── architecture/
│   ├── module_boundaries.md
│   └── platform_architecture.md
├── decisions/
│   ├── README.md
│   └── DDR-0001-cost-center-team-buckets.md
└── requirements/
    ├── COMPANY_CONFIGURATION.md
    ├── approval_and_audit
    ├── billing_and_invoicing.md
    ├── customer_onboarding.md
    ├── database.md
    ├── reciepts_and_knockoff.md
    ├── sales_order_commercial_setup.md
    └── tax_satutory_rules.md
```

| Path | Responsibility and authority | Must not be used as |
|---|---|---|
| `modules/accounting/data_model.md` / `modules/accounting/data_model.mmd` | Rendered Mermaid documentation and editable Crow's Foot source for the current Accounting Configuration design. | A replacement for `requirements/database.md`, or approval for future Accounting/Account Determination tables. |
| `README.md` | Documentation governance, source-of-truth precedence, status vocabulary, document map, and task-specific minimal-reading routes. | A detailed feature requirement. |
| `PRODUCT_OVERVIEW.md` | High-level product vision, scope, concepts, principles, and Core/AR boundary. | Physical schema or endpoint specification. |
| `AR_MVP_ARCHITECTURE.md` | Mixed-status AR architecture and domain direction. Each statement’s Confirmed/Proposed/TBD status matters. | Blanket approval to implement every described item. |
| `architecture/` | Current platform guardrails and module/dependency ownership. `module_boundaries.md` is the direct authority for Core-versus-AR placement; `platform_architecture.md` governs the modular monolith and platform constraints. | Detailed business behavior. |
| `requirements/` | Feature/business requirements plus the working database-design document. Read the relevant feature first; use `database.md` for persistence detail only after behavior is approved. | Proof that a feature is implemented, or permission to implement items marked TBD/REVIEW/PROPOSED/DEFERRED/FUTURE. |
| `decisions/` | Durable ADR/DDR governance and finalized consequential decision records. | A replacement for the owning requirement or routine change notes. |
| `CHANGELOG.md` | Human-readable history of meaningful approved product/design evolution and supersession. | Git history or a full requirement specification. |
| `history/repository_implementation_status_2026-09-10.md` | Dated evidence of what an earlier repository inspection found. | A live repository map or current desired behavior. |
| `repository_folder_guide.md` | This current “where does what live?” map. | Product authority, a migration inventory substitute, or proof that a feature passes tests. |

The authority order is: explicit approved decision, current feature requirement, finalized architecture constraints, current database design for persistence detail, implementation/tests as evidence, and then historical/reference material. A newer filename or modification date does not override that order.

---

## 9. How the Main Folders Work Together

```text
Approved product / feature decision
                │
                v
docs/requirements + docs/architecture
                │
                v
src/skmc_erp/core or src/skmc_erp/ar
     │                         │
     ├── model change ────────> alembic/versions
     │
     └── schema/service/router
                │
                v
tests/core or tests/ar + tests/integration
```

Use the owning feature folder for a coherent vertical slice. Add a migration only when persistence changes. Add focused tests beside the matching test domain and PostgreSQL/API coverage in `tests/integration/` when database behavior or route wiring matters. Update governing documentation when business, architecture, or material design decisions change.

Quick placement examples:

- A shared Company legal identity belongs in `core/`; an AR Billing preference belongs in `ar/`.
- A reusable exchange-rate fact belongs in `core/fx/`; AR’s rule for selecting it belongs in `ar/fx/`.
- A GL account belongs in `core/accounting/`; an AR revenue-to-GL mapping belongs in `ar/accounting/`.
- Stored-file metadata belongs in `core/file_storage/`; Billing document branding belongs in `ar/document_presentation/`.
- Schema evolution belongs in `alembic/versions/`; executable behavior belongs in `src/`; verification belongs in `tests/`; governing intent belongs in `docs/`.

---

## 10. Keeping This Guide Current

Update this guide when a meaningful tracked folder is added, removed, renamed, or given a different ownership boundary. Update the migration head/index when a new revision is added. Do not add virtual environments, caches, IDE files, generated outputs, or unrelated local artifacts merely because they appear in a working tree.
