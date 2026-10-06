# Documentation Governance

## Documentation Purpose

This directory contains product, architecture, feature-requirement, database-design, implementation-status, change-history, decision-record, and reference material for SKMC ERP SaaS and the current AR-focused work.

These documents operate at different levels of authority and maturity. The presence of a statement in the repository does not automatically make it a frozen implementation requirement. Before implementing a change, identify the relevant document layer, read the status attached to the specific statement, and confirm that no later approved decision supersedes it.

## Documentation Layers

| Layer | Purpose |
|---|---|
| Product Baseline | Defines product vision, scope, boundaries, concepts, and high-level principles. It does not supply every transaction or persistence rule. |
| Architecture | Defines module ownership, dependency direction, platform constraints, history strategy, and implementation boundaries. Architecture proposals must be distinguished from finalized architecture decisions. |
| Feature / Business Requirements | Defines business behavior for a specific feature or flow. These documents may contain confirmed MVP behavior alongside open, deferred, or future items. |
| Database Design | Translates approved requirements into relational design candidates, constraints, and statuses. It must not create business policy that the requirements have not approved. |
| Implementation Status | Records what was evidenced in the repository on a stated inspection date. It is historical evidence, not desired product behavior. |
| Change History | Records the meaning and disposition of material product and design changes. It complements, but does not replace, Git history. |
| Decision Records | Preserve the rationale and trade-offs for major finalized architecture or domain/design decisions. |
| Reference Documents | Supply context, diagrams, exports, spreadsheets, or supporting analysis. They are not implementation authority unless an approved document explicitly gives them that role. |

## Document Map

| Document | Purpose | Authority / Status | Use for implementation? | Important limitation |
|---|---|---|---|---|
| `PRODUCT_OVERVIEW.md` | Product vision, scope, Core/AR boundary, concepts, principles, MVP boundaries, and open areas | High-level product baseline | Yes, for product scope and principles | It explicitly is not a detailed requirement, database-design, or implementation specification |
| `AR_MVP_ARCHITECTURE.md` | AR architecture boundaries, Company Configuration flow, readiness, domain direction, history, staged work, and decision register | Review proposal; not an approved MVP freeze or implementation specification. Individual statements are marked Confirmed, Proposed, or TBD | Only for the requested slice and only according to the statement's status | Its table counts and proposed implementation sequence are not automatic approval to implement tables |
| `architecture/module_boundaries.md` | Core/Shared and AR ownership, dependency direction, feature structure, and future extraction direction | Current architectural direction; no separate freeze status is declared in the file | Yes, for module boundaries when consistent with finalized architecture decisions | It is conceptual and does not define detailed feature behavior or physical deployment by itself |
| `modules/company_configuration/README.md` | Company Configuration module purpose, boundaries, dependencies, downstream consumers, canonical documents, and reading order | Canonical Company Configuration documentation entry point; individual documents retain their stated statuses | Follow only the confirmed slice after review/freeze | It does not imply implementation completion or resolve listed OPEN/REVIEW matters |
| `modules/company_configuration/requirements.md` | Current Company Configuration business and system requirements | PROPOSED for review | No implementation until reviewed/frozen | Physical persistence belongs in the Company Configuration data model; unresolved policy belongs in open decisions |
| `modules/company_configuration/workflows.md` | Company configuration sequence, setup journey, and activation gates | PROPOSED FOR FREEZE; no implementation authority until reviewed | No implementation until reviewed/frozen | It does not create a generic workflow engine |
| `modules/company_configuration/data_model.md` | Canonical 54-table Company Configuration persistence design, domain inventory, and Mermaid ERD | CURRENT WORKING DESIGN / PROPOSED FOR FREEZE; no implementation approval | No; review/freeze is required before migrations/models/APIs | Certain tax maintenance, FX policy, and team IAM rules remain REVIEW/OPEN |
| `modules/company_configuration/business_rules.md` | Reconciled Company Configuration ownership, location, GST, fiscal, catalogue, cost center, and default rules | PROPOSED decision baseline with explicit statuses | No implementation until reviewed/frozen; afterward only for its confirmed slice | Physical details remain in the data model and unresolved matters remain in open decisions |
| `modules/company_configuration/open_decisions.md` | Genuine unresolved Company Configuration business/design decisions | OPEN/REVIEW register | No | It must not be resolved through implementation convenience |
| `modules/customer/README.md` | Customer module purpose, boundaries, dependencies, downstream consumers, canonical documents, and reading order | Canonical Customer documentation entry point; individual documents retain their stated statuses | Follow only the confirmed slice after review/freeze | It does not imply implementation completion or resolve listed OPEN/REVIEW matters |
| `modules/customer/requirements.md` | Current Customer business and system requirements | PROPOSED for review | No implementation until reviewed/frozen | Physical persistence belongs in the Customer data model; unresolved policy belongs in Customer open decisions |
| `modules/customer/workflows.md` | Customer-specific request states, actions, actors, transitions, and publication journey | PROPOSED FOR FREEZE; no implementation authority until reviewed | No implementation until reviewed/frozen | It does not create a generic cross-module workflow engine |
| `modules/customer/data_model.md` | Canonical 14-table operational Customer + Request/Snapshot/Action design, state machine, JSONB rationale, duplicate handling, and open boundaries | CURRENT WORKING DESIGN / PROPOSED FOR FREEZE; no implementation approval | No; review/freeze is required before migrations/models/APIs | Customer change-control, post-approval Contact changes, GST-to-Location mapping, and non-India statutory applicability remain REVIEW; reactivation remains OPEN |
| `modules/customer/business_rules.md` | Reconciled Customer ownership, Party boundary, legal/location/contact/commercial/approval/history rules | PROPOSED Customer decision baseline with explicit statuses | No implementation until reviewed/frozen; afterward only for its confirmed slice | Physical details remain in the data model and unresolved matters remain in open decisions |
| `modules/customer/open_decisions.md` | Genuine unresolved Customer business/design decisions | OPEN/REVIEW register | No | It must not be resolved through implementation convenience |
| `history/superseded/customer/customer_onboarding_workflow_options.md` | Historical comparison of three earlier workflow persistence alternatives | SUPERSEDED as active design; retained for traceability | No | Current working design is Request + immutable JSONB Request Snapshots + append-only Actions |
| `requirements/COMPANY_CONFIGURATION.md` | Compatibility redirect to the consolidated Company Configuration documentation | REDIRECT ONLY; not independent authority | No | Use `modules/company_configuration/README.md` and its reading order |
| `requirements/customer_onboarding.md` | Compatibility redirect to the consolidated Customer module documentation | REDIRECT ONLY; not independent authority | No | Use `modules/customer/README.md` and its reading order |
| `requirements/sales_order_commercial_setup.md` | Commercial agreement or internal-supply setup that can lead to Billing | Feature requirements with current MVP and future distinctions | Yes, for the approved Sales Order slice | Detailed downstream accounting, scheduling, and future workflow behavior is not fully settled |
| `requirements/billing_and_invoicing.md` | Creation and finalization behavior for outgoing AR documents | Feature requirements with confirmed rules and explicitly deferred extensions | Yes, for the approved Billing slice | It does not approve full Accounting posting, advanced numbering resolution, or historical reclassification |
| `requirements/tax_satutory_rules.md` | Currently confirmed AR tax and statutory behavior | Confirmed current AR behavior | Yes, for the applicable approved Tax/Statutory slice | It explicitly is not a generic configurable tax-rule engine; advanced TDS/TCS behavior remains outside current MVP unless approved |
| `requirements/approval_and_audit` | Current AR approval, edit locks, historical-period exception, version history, and audit events | Current MVP behavior plus explicitly future workflow extensibility | Yes, for the approved Approval/Audit slice | It does not authorize a generic workflow builder or full period-closing engine |
| `requirements/reciepts_and_knockoff.md` | Currently confirmed Receipt, allocation, cash, TDS, PI-transfer, and history concepts | Explicitly not fully frozen; records confirmed concepts only | Only for its confirmed concepts and a separately approved implementation slice | It explicitly is not the final detailed payment design |
| `requirements/database.md` | Detailed working table inventory, columns, relationships, constraints, rationales, statuses, and database change log | Working design/review draft; not a migration specification | Yes, after the governing business behavior is approved and only according to each item's status | `KEEP` and `ADD` are database-design statuses. `ADD`, `REVIEW`, and `DEFER` do not create universal product or implementation approval |
| `history/repository_implementation_status_2026-09-10.md` | Dated factual inspection of implementation present in the checkout | Historical implementation-status snapshot dated 2026-09-10 | Yes, only as evidence of repository state on that date | It does not define desired behavior and its file-inventory statements become stale as the repository changes |
| `../AR_SaaS_Categorized_Architecture_Decision_Register.pdf` | Categorized platform architecture decisions and future/configuration distinctions | “Current Production Architecture Baseline”; individual entries use statuses including FINAL, SCOPE, CONFIGURE, DIRECTION, DEFERRED, FUTURE, and POST-MVP | Use FINAL entries as architecture constraints; handle every other entry according to its stated status | It is a platform architecture register, not a detailed AR business-requirement or database specification |
| `CHANGELOG.md` | Human-readable meaning of material product and design changes | Governance change history | Yes, to identify later approved changes and superseded directions | It does not replace the underlying requirement, architecture document, decision record, or Git history |
| `decisions/README.md` | Rules for creating future ADRs and DDRs | Decision-record governance | Yes, when deciding whether a standalone record is required | It is not itself an architecture or domain decision |
| `SKMC_ERP_AR_database_plan_updated.xlsx` | Existing database-planning reference artifact | Reference document; not classified as current authority in this governance pass | No, unless an approved requirement or design explicitly adopts its content | Do not infer authority from filename, format, or modification time |

## Source-of-Truth Rules

1. Business behavior comes from the relevant approved requirement or explicit product decision.
2. Architecture constraints come from architecture documentation and finalized architecture decisions.
3. Database design implements business requirements and must not invent unresolved business behavior.
4. A proposed or `ADD` database table does not automatically mean the product behavior is approved.
5. `TBD`, `REVIEW`, `PROPOSED`, `DEFERRED`, and `FUTURE` items must not be silently implemented.
6. Historical and implementation-status documents do not override current approved requirements.
7. A newer file modification time does not automatically mean newer business authority.
8. Explicitly approved later decisions may supersede earlier decisions. The supersession should be recorded in `CHANGELOG.md` and, when material, a decision record.
9. Conflicting current documents must be reported rather than reconciled by assumption.
10. AR requirements are still evolving. Implement only the requested, approved slice and its necessary dependencies.

When two current sources appear to conflict, stop the affected implementation decision, identify the exact statements and statuses, and obtain or record an explicit resolution. Do not choose a rule based on document length, file date, or apparent schema convenience.

## Decision Status Vocabulary

| Status | Meaning |
|---|---|
| FINAL | A finalized decision that governs its stated area. Changing it requires an explicit later decision and usually an ADR or DDR when the impact is substantial. |
| CONFIRMED | Explicitly approved current behavior or direction. It governs the stated scope but does not imply that every implementation detail is frozen. |
| MVP | Included in the intended minimum product scope. It does not guarantee that every detailed rule or dependent decision is resolved. |
| PROPOSED | A recommendation or candidate awaiting approval. Do not implement it as settled behavior. |
| KEEP | A database-design disposition retaining a table or concept in the current plan. It is not universal business approval or proof of implementation. |
| ADD | A database-design proposal to add a table or concept for review. It is not automatic product or implementation approval. |
| REVIEW | The stated need, shape, or inclusion remains subject to review. Do not implement it silently. |
| TBD | A decision is still required. Do not guess the answer. |
| CONFIGURE | The governing architecture or capability is selected, while concrete deployment/configuration values remain to be chosen. |
| DIRECTION | The intended architectural trajectory is selected, but some final choice or implementation detail remains open. |
| SCOPE | A scope disposition in the architecture register, such as excluded from MVP or scheduled after AR; it is not a detailed implementation approval. |
| DEFERRED | Deliberately excluded from the current implementation slice pending a later decision or phase. |
| POST-MVP | Intended only after the MVP; it must not enter MVP merely because an extension path exists. |
| FUTURE | A possible or expected later capability without current implementation authority. |
| SUPERSEDED | Replaced by an explicitly approved later decision. Retain only for history and traceability. |
| REJECTED | Considered and deliberately not adopted. Do not reintroduce it without a new decision. |
| IMPLEMENTED | Present in code/schema and supported by current evidence. Documentation alone cannot establish this status. |
| HISTORICAL | A dated record of prior state or reasoning. It supplies context but is not current design authority. |

## Minimal Reading Strategy

Coding agents must not read the entire documentation directory for every task. Start with the task row below, inspect the named headings, then follow only the cross-references needed for the requested slice. Search headings and entity names before reading document bodies. Do not use line numbers as permanent references.

| Task | Minimum reading |
|---|---|
| Company Configuration | Start with `modules/company_configuration/README.md`, then read `modules/company_configuration/requirements.md`, `modules/company_configuration/workflows.md`, `modules/company_configuration/business_rules.md`, and `modules/company_configuration/open_decisions.md` as relevant; read `modules/company_configuration/data_model.md` and `modules/company_configuration/data_model.mmd` for persistence details; `PRODUCT_OVERVIEW.md` for principles; `requirements/database.md` for shared contracts |
| Accounting Setup / Chart of Accounts | `PRODUCT_OVERVIEW.md` — Core/AR boundary, principles, and MVP/open areas; `requirements/COMPANY_CONFIGURATION.md` — “Accounting Setup / Chart of Accounts”; `AR_MVP_ARCHITECTURE.md` — sources/precedence, ownership, domain model, database alignment, history, MVP/future scope, and open decisions; `requirements/database.md` — Design Rules, Status Legend, Accounting Setup tables, accounting cross-table rules, current dated accounting change-log entries, and table summary; Billing/Tax sections only for resolved GL use |
| Customer Onboarding | Start with `modules/customer/README.md`, then read `modules/customer/requirements.md`, `modules/customer/workflows.md`, `modules/customer/business_rules.md`, and `modules/customer/open_decisions.md` as relevant; read `modules/customer/data_model.md` and `modules/customer/data_model.mmd` only for persistence work; consult `architecture/module_boundaries.md` for the Customer/Party boundary and `requirements/approval_and_audit` for shared approval/audit semantics; use `requirements/database.md` only for shared contracts and the Customer comparison/status summary; `history/superseded/customer/customer_onboarding_workflow_options.md` is historical only |
| Sales Order | `PRODUCT_OVERVIEW.md` — Sales Order / Commercial Setup; `requirements/sales_order_commercial_setup.md`; relevant transaction/open-decision sections in `AR_MVP_ARCHITECTURE.md`; Sales Order candidates in `requirements/database.md` only for database work |
| Billing / Invoicing | `PRODUCT_OVERVIEW.md` — Billing and Financial Documents; `requirements/billing_and_invoicing.md`; `requirements/tax_satutory_rules.md` for applicable tax behavior; `requirements/approval_and_audit` for approval and locks; relevant Billing/open-decision sections in `AR_MVP_ARCHITECTURE.md`; Billing candidates in `requirements/database.md` only for database work |
| Tax / Statutory | `PRODUCT_OVERVIEW.md` — Tax and product principles; `requirements/tax_satutory_rules.md`; applicable catalogue/Billing sections; Tax reference and mapping entities in `requirements/database.md` only when persistence is involved; unresolved tax decisions in `AR_MVP_ARCHITECTURE.md` |
| Approval / Audit | `requirements/approval_and_audit`; relevant approval/readiness/history sections in `AR_MVP_ARCHITECTURE.md`; the affected feature requirement; approval/audit candidates in `requirements/database.md` only for database work |
| Receipt / Knock-off | `requirements/reciepts_and_knockoff.md` — including its Status; applicable TDS material in `requirements/tax_satutory_rules.md`; Receipt/open-decision sections in `AR_MVP_ARCHITECTURE.md`; Receipt candidates in `requirements/database.md` only for database work |
| Infrastructure / Deployment | `AR_SaaS_Categorized_Architecture_Decision_Register.pdf` — applicable FINAL and status-tagged entries; `architecture/module_boundaries.md`; `AR_MVP_ARCHITECTURE.md` — Executive Summary and Future Service Extraction Analysis; `history/repository_implementation_status_2026-09-10.md` only as a dated evidence snapshot |
| Database-only design work | The approved requirement governing the behavior; `requirements/database.md` — header/status, Design Rules, Status Legend, relevant entity sections, cross-table rules, open decisions, dated change entries, and table summary; relevant architecture constraints. Do not treat `ADD` as approval or resolve business TBDs in the schema |

## Change Discipline

- **Business-rule change:** update the relevant feature requirement first and record the meaningful change in `CHANGELOG.md`.
- **Database consequence:** update `requirements/database.md` only after the governing business decision is approved. Preserve the table/status distinction and record superseded database concepts.
- **Architecture change:** update the applicable architecture documentation and create an ADR or DDR when a finalized architecture rule, major boundary, or consequential approved design changes.
- **Implementation:** change code, tests, migrations, APIs, or frontend behavior only after documentation authority for the requested slice is clear.

Avoid maintaining the same detailed rule independently in several documents. Put the rule in its owning requirement or decision record and use concise cross-references elsewhere. When a material decision changes, record what changed and what it supersedes rather than silently rewriting history.
