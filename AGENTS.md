# SKMC ERP SaaS — Agent Instructions

These instructions apply to the entire repository. They are an operational guide, not a replacement for the governing product, architecture, requirement, or database documents.

## 1. Start Here

Before implementing anything:

1. Read `docs/README.md`.
2. Classify the task as product/business rule, database design, backend implementation, frontend implementation, infrastructure/platform, or documentation.
3. Use the **Minimal Reading Strategy** in `docs/README.md`.
4. Read only the relevant requirement sections.
5. Search headings and entity names before reading large files.
6. Do not scan the entire `docs` directory by default.

More context is not automatically better. Read the minimum authoritative context required for the requested slice.

## 2. Documentation Authority

Use this precedence for the question being answered:

1. explicit approved/current product decision;
2. relevant current business or feature requirement;
3. finalized architecture constraints;
4. current database design for persistence detail;
5. existing implementation and tests as evidence of implemented behavior; and
6. historical or reference material.

Database design cannot silently create product behavior. Existing code does not automatically override an explicitly approved current requirement. File modification time alone does not establish authority.

If two current authoritative documents conflict, **STOP the affected design decision and report the conflict**. Do not guess or resolve it through implementation convenience.

## 3. Status Rules

Do not silently implement `TBD`, `REVIEW`, `PROPOSED`, `DEFERRED`, `FUTURE`, or `POST-MVP` material unless the current task explicitly approves or promotes it.

- `KEEP` and `ADD` in database documentation are database-design statuses, not universal product approval.
- `MVP` describes intended scope; it does not mean every detailed rule is frozen.
- Historical and superseded material provides traceability, not current authority.

## 4. Architecture Guardrails

Follow [docs/architecture/platform_architecture.md](docs/architecture/platform_architecture.md). The key non-negotiable rules are:

- Use a modular monolith first and organize code by feature/domain.
- AR may depend on Core/Shared. Core/Shared must not depend on AR-specific behavior.
- PostgreSQL is the financial source of truth.
- Final financial transactions preserve transaction-time truth.
- Binary artifacts belong in object storage, not PostgreSQL.
- Durable asynchronous work follows the approved transactional-outbox and task pattern.
- Background workers must be retry-safe and idempotent.
- Delivery failure must not undo finalized financial state.
- Authentication and ERP business authorization are separate concerns.
- Company or subdomain context does not grant permission.
- Provider-specific infrastructure APIs stay behind adapters.
- Do not introduce Redis, Kafka, Kubernetes, microservices, or equivalent distributed complexity without an approved, measured need.

Do not duplicate the full platform architecture here. Consult its named section when platform detail matters.

## 5. Module Boundaries

Follow [docs/architecture/moduleboundaries.md](docs/architecture/moduleboundaries.md).

- Core/Shared owns reusable Company/platform identities and shared accounting/statutory concepts.
- AR owns AR-specific commercial, Billing, receivable, Receipt/Knock-off, account-mapping, delivery, reminder, approval, and audit behavior.
- Future Accounting owns full posting, journal, ledger, reconciliation, closing, correction/reclassification, and Inter-Unit clearing behavior unless an approved decision promotes a slice.

Never move AR-specific logic into Core for convenience. Never duplicate shared Company, Location, Currency, GL Account, or statutory masters inside AR.

## 6. Task-Specific Reading

Use these as starting points, then follow only relevant cross-references.

### Company Configuration task

Read the relevant heading in `docs/requirements/COMPANY_CONFIGURATION.md`, the matching entities in `docs/requirements/database.md` only when persistence is involved, and `docs/architecture/moduleboundaries.md` when ownership is affected.

### Customer task

Read `docs/requirements/customer_onboarding.md`, matching Customer sections in `docs/requirements/database.md`, and `docs/requirements/approval_and_audit` only when approval or audit behavior is affected.

### Sales Order task

Read `docs/requirements/sales_order_commercial_setup.md` and only the related catalogue, Billing, approval, or database sections required by the requested change.

### Billing task

Read `docs/requirements/billing_and_invoicing.md`; read `docs/requirements/tax_satutory_rules.md` when tax is affected, `docs/requirements/approval_and_audit` when approval or finalization is affected, and only the corresponding entities in `docs/requirements/database.md` when persistence is involved.

### Receipt / Knock-off task

Read `docs/requirements/reciepts_and_knockoff.md`, the applicable TDS/statutory section in `docs/requirements/tax_satutory_rules.md`, and only the matching Receipt/Allocation entities in `docs/requirements/database.md`.

### Accounting/CoA configuration task

Read **Accounting Setup / Chart of Accounts** in `docs/requirements/COMPANY_CONFIGURATION.md`, the current CoA and mapping entities in `docs/requirements/database.md`, and `docs/architecture/moduleboundaries.md`. Do not automatically read unrelated AR flows.

### Infrastructure task

Read `docs/architecture/platform_architecture.md`. Read feature requirements only when the infrastructure change affects a business contract.

## 7. Database Design Rules

Before changing persistence:

1. establish the governing business requirement;
2. read only the relevant current database entities;
3. preserve Tenant and Company ownership boundaries;
4. use relational constraints for real invariants where practical;
5. do not rely on frontend validation alone for financial or business integrity;
6. normally inactivate or date-end historically used financial masters rather than deleting them; and
7. never reconstruct finalized financial history from mutable current masters.

Do not implement an unresolved proposed table merely because it appears in `docs/requirements/database.md`.

## 8. Change Discipline

For a business-rule change:

```text
Requirement -> database consequence, if any -> implementation -> tests
```

For a database-only correction that does not alter business behavior:

```text
Relevant requirement validation -> database documentation -> implementation
```

For an architecture change:

```text
Identify conflict -> human approval -> ADR when required -> architecture documentation -> implementation
```

For a major domain/design replacement, follow the DDR guidance in `docs/decisions/README.md` when applicable.

## 9. CHANGELOG Rules

`docs/CHANGELOG.md` records meaningful product and design evolution.

Add a new `CHG` entry when a task:

- approves or changes a business rule;
- replaces a significant design;
- resolves an important `TBD` or `REVIEW` decision;
- changes a documented architecture or domain boundary; or
- corrects material canonical documentation.

Do not add a design changelog entry for ordinary formatting, typo correction, routine code refactoring, test-only maintenance, or implementation that simply follows an already-recorded design unless repository practice explicitly requires one.

Never rewrite an old changelog entry to make history look cleaner. Add a new entry when the documented history changes.

## 10. Evolving AR Scope

The AR product and domain design is still evolving. `docs/AR_MVP_ARCHITECTURE.md` contains confirmed, proposed, and open material; the whole document is not a frozen implementation specification.

Implement only the approved slice required by the current task. Do not resolve unrelated open decisions while implementing another feature.

## 11. Avoid Overengineering

Unless explicitly approved, do not introduce:

- generic rule engines;
- workflow builders;
- universal settings bags;
- generic accounting-dimension engines;
- premature service extraction;
- duplicate masters; or
- abstraction layers created only for hypothetical future requirements.

Preserve known extension points without implementing future systems prematurely.

## 12. Implementation Workflow

For implementation tasks:

1. identify the requested behavior;
2. identify the authoritative requirement;
3. identify the architecture and module boundary;
4. inspect only the relevant current implementation;
5. identify the necessary persistence, API, and UI impact;
6. implement the smallest coherent slice;
7. add or update meaningful tests for the behavior;
8. run the relevant existing validation and tests; and
9. report unresolved dependencies or documentation conflicts.

Do not broaden task scope without approval.

## 13. End-of-Task Report

For material changes, report:

- files changed;
- behavior implemented;
- requirement or document followed;
- database and migration impact;
- tests run and results;
- documentation and changelog changes;
- unresolved issues; and
- anything intentionally not implemented.
