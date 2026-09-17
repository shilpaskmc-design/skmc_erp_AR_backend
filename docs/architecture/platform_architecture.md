# Platform Architecture

## 1. Purpose and Authority

This document is the operational guardrail for the current technical and platform architecture. It summarizes the decisions in the [AR SaaS Categorized Architecture Decision Register](../../AR_SaaS_Categorized_Architecture_Decision_Register.pdf), which is the primary source for this document, and applies the documentation-governance rules in [docs/README.md](../README.md).

This document does not define Accounts Receivable business behavior. Company Configuration, Customer, Sales Order, Billing, Tax, Receipt, Reminder, and other feature rules remain in their owning requirements documents.

Status terms retain their governance meaning:

- **FINAL** decisions are mandatory architecture constraints.
- **DIRECTION** records a selected approach whose final implementation choice is still open.
- **CONFIGURE** means the architecture is selected but an operating value or concrete setup remains to be chosen.
- **DEFERRED** items are deliberately excluded from the current delivery.
- **FUTURE** items are later deployment profiles or capabilities without current implementation authority.
- **SCOPE / POST-MVP** items are outside the current MVP and must not enter it merely because an extension path exists.

A change to a **FINAL** architecture decision requires human approval and an Architecture Decision Record (ADR). Implementation convenience does not override this rule.

## 2. Current Architecture Style

The following architecture style is **FINAL**:

- The product is an AR-first SaaS platform.
- The application begins as a modular monolith, with strong logical module and domain boundaries inside one deployable backend.
- The initial domain structure is Shared Core plus the AR Domain.
- AR may consume Core capabilities. Core must not depend on AR behavior or entities.
- The first deployment is not a collection of microservices.
- Service extraction occurs only when scale, team ownership, security, or isolation creates a measured need.

The current topology can be read as:

```text
Internet
  -> GCP External Application Load Balancer
     + Cloud Armor Standard
     + GCP-managed TLS
       -> *.ourapp.com      -> Cloud Run AR application
       -> auth.ourapp.com   -> Keycloak on two GCP VMs / regional MIG

AR application
  -> Cloud SQL for PostgreSQL
     -> keycloak_db
     -> application_db
        -> core schema
        -> ar schema
  -> Transactional Outbox
     -> Dispatcher
     -> TaskQueue abstraction
     -> GCP Cloud Tasks
     -> Cloud Run Worker
        -> WeasyPrint
        -> Cloudflare R2
        -> Resend
```

This is a modular-monolith deployment with separate runtime components for authentication and asynchronous work. Those components do not turn the business modules into microservices.

## 3. Technology Stack

| Area | Current choice | Status |
|---|---|---|
| Frontend | React + TypeScript + Vite | FINAL |
| Backend | FastAPI + Python | FINAL |
| Validation | Pydantic | FINAL |
| ORM | SQLAlchemy 2.x | FINAL |
| Database | PostgreSQL on GCP Cloud SQL | FINAL |
| Migrations | Alembic | FINAL |
| Identity | Keycloak | FINAL |
| Runtime | GCP Cloud Run for the application and workers; Keycloak on GCP Compute Engine | FINAL |
| Async | Transactional Outbox + provider-neutral TaskQueue + GCP Cloud Tasks + Cloud Run Workers | FINAL |
| Object Storage | Cloudflare R2 behind an ObjectStorage abstraction | FINAL |
| PDF | WeasyPrint behind a PdfRenderer abstraction | FINAL |
| Email | Resend behind an EmailProvider abstraction | FINAL |
| Edge / WAF | GCP External Application Load Balancer + Cloud Armor Standard + GCP-managed TLS | FINAL |
| Secrets | GCP Secret Manager with runtime injection/config abstraction | FINAL |
| Observability | GCP-native logging/monitoring + Sentry + OpenTelemetry | FINAL |
| CI/CD | GitHub Actions + GCP Artifact Registry | FINAL |
| Containers | Docker | FINAL |

## 4. Multi-Tenancy and Access

The multi-tenant structure is **FINAL**:

```text
Tenant
  -> optional Organisation
     -> Company
```

- Tenant is the primary security and data-isolation boundary.
- Company is the legal and business entity.
- Organisation is an optional grouping within a Tenant.
- A hostname or subdomain identifies Company context. It never grants Company access.
- User access to a Company must be explicitly authorized.

The architecture requires explicit Company authorization but does not prescribe a particular Company-membership table here. The persistence mechanism remains a separate domain/database decision and must preserve the finalized authorization rule.

## 5. Database Architecture

The following decisions are **FINAL**:

- PostgreSQL is the database engine and financial source of truth.
- GCP Cloud SQL for PostgreSQL is the initial managed database service.
- The initial topology uses one Cloud SQL PostgreSQL instance.
- Keycloak uses `keycloak_db`; application financial and platform data use `application_db`.
- Keycloak and the application use separate database credentials. Keycloak must not have access to application financial data.
- The application initially uses logical `core` and `ar` schemas.
- While these domains share one database, normal PostgreSQL foreign keys, joins, constraints, transactions, and locking are allowed and expected where they protect integrity.
- Approved financial documents preserve structured, immutable transaction-time snapshots in PostgreSQL.

The schemas express logical ownership. They are not separate services or databases today. Physical service/database extraction is a later option when scale, ownership, or isolation justifies it; code must preserve boundaries so extraction remains practical.

## 6. Application Dependency Rules

These dependency rules are **FINAL**:

```text
AR -> Core       allowed
Core -> AR       forbidden
```

Core entities and services must not import or depend on AR-specific invoice, receivable, reminder, receipt, or workflow behavior. AR consumes stable Core contracts.

Provider-specific infrastructure APIs remain behind interfaces or adapters. Business and domain code must not directly depend on:

- GCP Cloud Tasks APIs; use the TaskQueue abstraction;
- Cloudflare R2 APIs; use the ObjectStorage abstraction;
- Resend APIs; use the EmailProvider abstraction;
- GCP Secret Manager APIs; use runtime injection or the configuration abstraction;
- renderer-specific APIs where the PdfRenderer contract applies; or
- provider-specific tracing APIs where OpenTelemetry provides the portable instrumentation boundary.

Equivalent future providers must be introduced by adapters rather than by rewriting Core or AR business logic.

## 7. Async Processing

Financial state and durable asynchronous intent commit atomically through the **FINAL** Transactional Outbox pattern:

```text
Financial transaction + durable async intent
  -> one PostgreSQL transaction
  -> Outbox
  -> Dispatcher
  -> provider-neutral TaskQueue
  -> GCP Cloud Tasks
  -> Cloud Run Worker
```

Operational rules:

- Workers must be idempotent and retry-safe.
- Retries must not duplicate financial effects, PDF generation, emails, or other durable work.
- Queue payloads carry IDs and references, not large binaries or the authoritative financial state.
- Queue submission failure must not lose work already committed with the financial transaction.
- Kafka is outside the current MVP. It may be considered only after a genuine event-streaming requirement exists.

## 8. Documents and Delivery

The following decisions are **FINAL**:

- Binary files belong in object storage, not PostgreSQL.
- Cloudflare R2 is the current object-storage provider.
- Storage access goes through a provider-neutral ObjectStorage interface.
- PostgreSQL retains the object key, content hash, and relevant metadata linking the artifact to structured financial truth.
- A finalized financial PDF is an immutable artifact with a retained hash.
- WeasyPrint renders PDFs through a PdfRenderer abstraction.
- Resend sends transactional email through an EmailProvider abstraction.
- Delivery states must carry operational meaning; the architecture does not reduce delivery to a single boolean.
- Delivery failure never rolls back or invalidates an approved financial document.

Feature-specific recipients, templates, reminders, and delivery policies belong in their owning requirements, not in this platform guardrail.

## 9. Authentication and Authorization Boundary

Keycloak is the **FINAL** authentication platform. It owns login, credentials, password policy, MFA, sessions, and OIDC authentication.

The application and database enforce financial and business authorization, including Company access and permissions for protected business actions. Authentication answers who the user is; financial authorization answers what that user may do in the selected Company and business context.

ERP business permissions must not be moved into Keycloak merely because Keycloak authenticates users. Tenant or hostname context also must not be treated as authorization.

## 10. Networking and Edge

The current edge architecture is **FINAL**:

```text
*.ourapp.com
  -> GCP External Application Load Balancer
  -> Cloud Armor Standard
  -> GCP-managed TLS

Routes:
*.ourapp.com     -> Cloud Run application
auth.ourapp.com  -> Keycloak
```

The wildcard hostname provides Company-routing context. The application must still verify the authenticated user's explicit authorization for that Company.

The exact DNS provider and records are **CONFIGURE**. The wildcard pattern and routing architecture are already decided; choosing records/provider does not reopen those decisions.

## 11. Deployment and Operations

The following decisions are **FINAL**:

- Docker is the container packaging standard.
- The application and asynchronous worker run on GCP Cloud Run.
- Keycloak runs in Docker on two GCP Compute Engine instances, managed through a regional Managed Instance Group architecture.
- GitHub Actions provides CI/CD.
- GCP Artifact Registry stores versioned production images.
- The deployment flow is `PR -> CI -> image -> staging -> tests -> controlled production`.
- Alembic migrations run once as a controlled deployment job, not independently during every Cloud Run instance startup.
- GitHub authenticates to GCP through OIDC / Workload Identity Federation rather than long-lived service-account JSON keys.
- The environment set is Local, Staging, and Production for the current MVP.

Provider-modular Terraform/OpenTofu is the **DIRECTION** for infrastructure as code. The exact choice between Terraform and OpenTofu is **CONFIGURE**. Cloud SQL size, VM size, and other capacity values are not finalized here.

## 12. Observability and Secrets

The observability and secret-management architecture is **FINAL**:

- GCP Cloud Logging collects Cloud Run, VM, and infrastructure logs.
- GCP Cloud Monitoring provides managed metrics and alerts.
- Sentry provides frontend, backend, and worker error grouping and release correlation.
- OpenTelemetry supplies portable instrumentation and exports to the current GCP observability environment.
- GCP Secret Manager holds production credentials and secrets.
- Applications consume secrets through runtime injection or a configuration abstraction rather than direct domain-code calls to Secret Manager.
- Local secrets use a Git-ignored `.env` or equivalent local mechanism and must never be committed.
- Logs must not contain tokens, passwords, secrets, bank data, sensitive financial payloads, or full invoice payloads.

## 13. Backup and Availability

Data recovery and availability recovery are separate concerns.

The following Day 1 recovery requirements are **FINAL**:

- Cloud SQL automated backups;
- PostgreSQL point-in-time recovery (PITR);
- Cloudflare R2 versioning/retention for financial artifacts; and
- a documented and tested restore procedure.

These controls protect recoverability after bad migrations, deletion, updates, or artifact loss. They do not provide automatic database failover.

| Capability | Status | Current position |
|---|---|---|
| Data recovery through backups, PITR, R2 protection, and restore testing | FINAL | Required from Day 1 |
| Automatic downtime recovery | Not fully covered | No ready Cloud SQL standby is part of the current baseline |
| Regional Cloud SQL HA | DEFERRED | Next major availability improvement, subject to approval |
| Cross-region disaster recovery | DEFERRED | Outside the current MVP |
| Multi-cloud disaster recovery | DEFERRED | Requires a real enterprise or regulatory need |
| Active-active architecture | DEFERRED | Excluded at the current scale and complexity |

Exact retention periods and formal RPO/RTO values are **CONFIGURE**. They must be selected without implying that deferred HA or DR already exists.

## 14. Cloud Portability

The portability strategy is **FINAL**:

- Only GCP is implemented for the current production profile.
- Application architecture remains portable.
- Provider-specific APIs stay behind infrastructure adapters and are forbidden in Core/AR business logic.
- The deployment should prefer the selected cloud's native managed edge while it remains single-cloud.

AWS and Azure mappings are **FUTURE** deployment profiles. They describe capability-equivalent options, not infrastructure to build now. Multi-cloud deployment must not be implemented before a commercial, regulatory, isolation, or resilience requirement justifies it.

## 15. Frozen Architecture Principles

The following principles are **FINAL** and frozen:

1. Financial correctness comes before distributed-system complexity.
2. Use a modular monolith first; introduce microservices only when justified.
3. PostgreSQL is the financial source of truth.
4. Store binary artifacts in object storage rather than the relational database.
5. Approved financial documents preserve immutable transaction-time truth.
6. Financial commit and durable asynchronous work intent must be transactionally reliable.
7. Background delivery failure must never undo financial finalization.
8. Workers must be idempotent and retry-safe.
9. Authentication and financial authorization are separate concerns.
10. A hostname identifies Company context; it never grants permission.
11. Provider-specific APIs remain behind adapters.
12. Use one production cloud now while keeping the application architecture portable.
13. Do not introduce Redis, Kafka, Kubernetes, or microservices without measured need.
14. Backups protect data; high availability protects service availability. They solve different problems.
15. Preserve the agreed MVP scope rather than expanding the architecture speculatively.

## 16. Not Yet Finalized / Implementation Configuration

The architecture register marks the following items **CONFIGURE** or leaves the exact choice within an approved **DIRECTION**. They must not be represented as finalized values:

| Item | Existing constraint | Still to configure |
|---|---|---|
| Cloud SQL sizing | PostgreSQL on Cloud SQL is FINAL | vCPU, RAM, storage, and load-based tuning |
| Backup retention | Automated backups and PITR are FINAL | Exact retention periods |
| RPO/RTO | Current HA deferral and recovery posture are known | Formal MVP recovery objectives |
| Keycloak sizing | Two-VM regional MIG architecture is FINAL | VM sizes and capacity assumptions |
| Keycloak clustering | HA topology is selected | Discovery, cache, and network details |
| Keycloak admin access | GCP edge architecture is selected | Admin hostname and access restrictions |
| DNS | Wildcard architecture is FINAL | Provider and exact records |
| Load balancer | GCP External Application Load Balancer is FINAL | Backend, health-check, and forwarding configuration |
| Cloud Armor | Cloud Armor Standard is FINAL | Exact WAF, rate-limit, and security rules |
| Infrastructure as code | Provider-modular IaC is DIRECTION | Terraform versus OpenTofu |
| Staging | Staging is FINAL | Exact runtime and database sizing |
| Production budget | Architecture is selected | Final monthly cost after capacity sizing |

Resolving these items configures the approved architecture. It does not, by itself, reopen the underlying FINAL decision.

## 17. Explicit Non-Goals for Current MVP

The current MVP does not include:

- Kubernetes;
- Kafka or an event-streaming platform;
- Redis without a measured requirement;
- premature decomposition into microservices;
- active-active deployment;
- cross-region or multi-cloud disaster recovery;
- simultaneous AWS, Azure, and GCP production deployment; or
- distributed infrastructure introduced only for hypothetical future scale.

Kubernetes, Kafka, and distributed architecture are **SCOPE / POST-MVP** unless later justified. Regional HA, cross-region DR, multi-cloud DR, and active-active retain their **DEFERRED** statuses. AWS/Azure profiles remain **FUTURE**. These labels preserve extension options without authorizing current implementation.

## 18. Architecture Change Rule

A coding agent may not silently replace, bypass, or dilute a **FINAL** architecture decision.

If implementation appears to require such a change:

1. identify the exact conflict and the FINAL decision it affects;
2. stop the architectural part of the change;
3. document the proposed replacement, rationale, alternatives, and consequences;
4. create or update an ADR after human approval; and
5. update the architecture documentation before implementing the approved change.

An unresolved **CONFIGURE** item may be decided through the applicable implementation/configuration process without treating the underlying architecture as reopened. **DIRECTION**, **DEFERRED**, **FUTURE**, and **SCOPE / POST-MVP** items must retain their stated status until an explicit approved decision changes it.
