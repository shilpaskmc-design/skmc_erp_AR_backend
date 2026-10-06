# Customer Onboarding Architecture and Decision Baseline

## 1. Purpose, Authority, and Status

This document defines the current Customer Onboarding business/architecture baseline. The selected working persistence direction is documented in the canonical 14-table Customer database-design artifact; implementation remains prohibited until review/freeze.

**Document status:** `PROPOSED` for review.

The decision statuses inside this proposed baseline mean:

| Status | Meaning in this document |
|---|---|
| `CONFIRMED` | Agreed in the current Customer Onboarding planning discussion and proposed as the governing MVP direction. It is not implementation approval while this baseline remains `PROPOSED`. |
| `OPEN` | A product decision is still required. Do not infer it from a table, API, UI, or implementation convenience. |
| `REVIEW` | The need or direction is known, but inclusion or detailed behavior must be reviewed before implementation. |
| `DEFERRED` | Deliberately excluded from the current MVP design slice. |

This document does **not** approve an API contract, migration, model, or implementation. [Customer Onboarding and Customer Master Database Design](../CUSTOMER_ONBOARDING_ERD.md) is the `CURRENT WORKING DESIGN / PROPOSED FOR FREEZE`; the older workflow-options document is historical/superseded.

## 2. Decision Summary

| Area | Decision | Status | Horizon |
|---|---|---|---|
| Customer ownership | A Customer belongs to exactly one seller Company in the current MVP. | `CONFIRMED` | Current MVP decision |
| Common versus AR data | Legal identity, statutory identity, locations, contacts, and endpoints are common/Party-like in meaning but remain physically owned by the AR Customer aggregate for MVP. Commercial defaults and AR communication purposes are Customer/AR-specific. | `CONFIRMED` | Current MVP decision |
| Shared Party/Vendor master | Do not introduce a shared Party, Vendor, or Contact master solely for possible future AP reuse. | `CONFIRMED` | Current MVP decision |
| Future Party boundary | Keep common-in-meaning data separable so a later Party master can link or own it without moving AR-specific commercial behavior into Core. | `CONFIRMED` | Future architectural consideration |
| Customer Organisation | An optional Company-specific external-customer group may contain multiple Customer legal entities; a Customer may also be standalone. It is not the seller-side `core.organisations` concept. | `CONFIRMED` | Current MVP decision |
| Legal identifiers and GSTIN | Use generic Customer legal identifiers for PAN/CIN/LLPIN and other jurisdiction-specific identities; keep GSTIN in Customer GST registrations. Approved/current duplicate control is scoped to the owning seller Company. | `CONFIRMED` | Current MVP decision |
| Draft/pending duplicate control | Draft overlap is allowed; hard validation occurs on Submit and again on approval/publication. No `customer_identifier_claims` table is used for MVP. | `CONFIRMED` | Current MVP working design |
| Customer Locations | Store reusable physical locations. Bill-To and Ship-To are transaction selections, not permanent Customer Location roles. | `CONFIRMED` | Current MVP decision |
| Customer Location effective dating | Use stable `customer_locations` identity plus effective-dated `customer_location_versions`; address-bearing fields live only in versions. | `CONFIRMED` | Current MVP working design |
| Contacts and communications | Separate contact identity, Contact Details, contact roles, and contact purposes. Post-approval Contact change control remains `REVIEW`. | `CONFIRMED` / `REVIEW` | Structure / change policy |
| Credit period | Customer has at most one default Payment Term selection; it does not independently maintain a second editable credit-days field. Company default is the fallback. | `CONFIRMED` | Current MVP decision |
| Credit limit | Customer Credit Limit is outside the current MVP baseline. | `DEFERRED` | Future consideration |
| Receivable GL | Receivable GL remains Company-level; Customer does not own a Receivable GL mapping. | `CONFIRMED` | Current MVP decision |
| Approval semantics | Use one Customer onboarding/amendment business flow with Draft, Submit, Authority Review, Approve/Approve with Changes/Return/Reject and maker/checker separation. | `CONFIRMED` | Current MVP decision |
| Workflow persistence | Use `customer_requests` with authoritative JSONB Draft, immutable JSONB request snapshots, and append-only actions. | `CONFIRMED` | Current MVP working design |
| History | Preserve exact submitted request payloads, append-only actions, Location versions, audit evidence, and owning-transaction snapshots without typed Customer revision children. | `CONFIRMED` | Current strategy |
| Customer Code | System-generate Company prefix plus Company-scoped sequential number, starting at 1 without automatic reset, during successful `NEW_CUSTOMER` publication. | `CONFIRMED` | Current MVP working design |
| Inactive reactivation | Inactivation blocks new commercial use and preserves history; whether reactivation reuses the record/code or requires a re-onboarding path remains unresolved. | `OPEN` | Must be resolved before lifecycle freeze |

## 3. Ownership and Future Party Boundary

### 3.1 Company-specific Customer

**Status: `CONFIRMED` — Current MVP decision**

- Each Customer is owned by one seller Company.
- The same external legal entity may therefore be represented by separate Customers for different seller Companies.
- Customer search, duplicate checks, approval, code assignment, commercial defaults, and operational use occur in the owning Company context.
- Tenant isolation and explicit Company authorization both apply. Tenant membership alone does not grant access to a Customer in another Company.

### 3.2 Common/Party-like and Customer/AR-specific domains

**Status: `CONFIRMED` — Current MVP decision**

The single MVP Customer workflow must classify controlled changes into two conceptual domains:

| Domain | Current examples |
|---|---|
| `COMMON/PARTY-LIKE` | Legal/display identity, PAN and other statutory identity, GST registrations, stable/effective-dated physical locations, contact identity, and Contact Details |
| `CUSTOMER/AR-SPECIFIC` | Customer-code lifecycle, default Payment Term/credit period, Contact-purpose assignments, and other Customer commercial/receivables behavior |

Both categories remain inside the AR Customer aggregate for MVP. The classification is an architectural boundary, not an instruction to introduce Party tables or two workflows now.

### 3.3 No premature shared master

**Status: `CONFIRMED` — Current MVP decision**

- Do not create a shared Party master merely because Customer and a future Vendor could describe the same legal entity.
- Do not create a shared Contact master merely for hypothetical AP reuse.
- Future Vendor onboarding must own its AP-specific roles, purposes, commercial terms, and approval rules. It must not reuse AR communication purposes by accident.
- Physical Customer ownership in MVP must not be interpreted as permanent domain ownership of legal-party concepts.

### 3.4 Future Party migration

**Status: `CONFIRMED` — Future architectural consideration**

If a Party master is approved later, it may consolidate or link equivalent Company-specific Customer and Vendor identities. The future change should be able to move common identity changes to Party approval while AR/commercial changes remain under Customer approval. Current design must therefore avoid embedding AR-specific terms or purposes into legal identity, Location, Contact, or Contact Detail concepts.

No placeholder `party_id`, Party table, dual-write flow, or Party approval process is approved for MVP.

## 4. Customer Organisation

**Status: `CONFIRMED` — Current MVP decision**

- Customer Organisation is an optional Company-specific external-customer grouping, such as a group containing several separately billable Customer legal entities.
- A Customer may be standalone and therefore have no Customer Organisation.
- It is distinct from `core.organisations`, which groups the Tenant's own seller Companies.
- No nested Customer Organisation hierarchy, configuration inheritance, shared balance, shared credit exposure, or Organisation-level approval is part of MVP.
- Customer Organisation has an active/inactive lifecycle. Inactive groups cannot be selected for new associations; existing Customer and transaction history remains intact.

## 5. Legal and Statutory Identity

### 5.1 Legal identifiers and GSTIN rules

**Status: `CONFIRMED` — Current MVP decision**

- PAN is mandatory for an India-MVP Customer through an applicable legal-identifier type/rule.
- PAN, CIN, LLPIN, UEN, EIN, ABN, CRN, and future jurisdiction-specific non-GST identifiers belong in generic Customer identifier rows, not permanent direct `customers` columns.
- The original/business identifier value and normalized comparison value belong in the same identifier row.
- Within one owning seller Company, an approved/current normalized identifier value of a given type may belong to only one Customer legal entity.
- A Customer may be GST-registered or unregistered.
- A GST-registered Customer must provide the applicable GST registration details; an unregistered Customer may have no GSTIN.
- One Customer may have multiple GSTINs, for example registrations in different states.
- Within one owning seller Company, a normalized GSTIN may belong to only one Customer.
- Duplicate validation covers onboarding and amendment, but the open-draft enforcement mechanism remains `REVIEW`.
- Option A hard-reserves draft PAN/GSTIN values through a narrow claim table. Option B permits warnings/temporary draft overlap and validates on submit and again on approval/publish while database uniqueness protects approved/current rows.
- GSTIN remains in the GST-registration model and is not moved to the generic identifier table.
- The existing Company identifier-type reference should be reviewed for generic/shared naming and reuse. No rename or migration is approved by this baseline.

### 5.2 Statutory corrections and history

**Status: `CONFIRMED` — Current MVP decision**

- Approved GSTIN identity is not overwritten in place as a casual correction.
- An incorrect or obsolete approved GST registration is inactivated, and the replacement is introduced through an approved Customer amendment.
- Material legal/statutory changes use the Customer onboarding/amendment approval workflow.
- Finalized documents continue to use their transaction-time Customer and statutory snapshots.
- Exact supporting-document requirements and non-India statutory applicability remain `REVIEW`.

## 6. Customer Locations, Bill-To, and Ship-To

### 6.1 Location meaning

**Status: `CONFIRMED` — Current MVP decision**

- A Customer Location represents a reusable physical address/site such as a registered office, branch, office, warehouse, or other business location.
- `Billing Address` and `Shipping Address` are not permanent Location identities or boolean roles.
- Any applicable active, approved Customer Location may be selected as Bill-To or Customer Ship-To for a transaction, subject to later Billing/statutory validation.
- A Ship-To may also be a seller Company Location where the approved Billing rule allows `COMPANY_LOCATION`.
- Sales Order captures the selected Bill-To and Ship-To context. A draft invoice may inherit those selections and an authorized user may change them to another eligible approved Location before submission/finalization.
- Do not create invoice-only free-text master addresses as a substitute for onboarding. A required new Customer Location goes through the Customer amendment path first.
- Finalized financial documents snapshot the exact Bill-To/Ship-To values used. Later Location edits do not rewrite them.

### 6.2 Customer Location effective dating

**Status: `CONFIRMED` — Current MVP working design**

The current preferred simple behavior is:

- a pending Location edit does not alter the currently approved Location;
- after approval, the new address becomes current from the approval date;
- the prior address history closes immediately before the new period;
- future scheduling and arbitrary backdating are not MVP needs.

Customer Location follows the same narrow structural idea as Company Location: stable `customer_locations` identity plus effective-dated `customer_location_versions`. Physical address, Location name, applicable GST registration, and registered-address designation belong to the version, not the stable row. Historical versions remain queryable and finalized transactions still preserve their own snapshots. Future scheduling/backdating is not introduced. Whether a GST-to-Location mapping change requires approval remains `REVIEW`.

## 7. Contacts and Communication Resolution

### 7.1 Contact identity

**Status: `CONFIRMED` — Current MVP decision**

Customer-owned Contact identity uses `contact_type` (`PERSON`, `DEPARTMENT`, or `GENERAL`) plus `display_name`. It may optionally associate with a same-Customer GST registration and/or Location. Subtype-specific person/department fields are not added to the current table proposal; richer identity fields require a later approved requirement.

### 7.2 Contact Details

**Status: `CONFIRMED` — Current MVP decision**

- `customer_contact_details` are separate from Contact identity so one Contact may have multiple reachable values.
- Initial detail types include `EMAIL`, `PHONE`, `MOBILE`, and `WHATSAPP`.
- `detail_value` is the entered address/number. `normalized_value` is the backend canonical value used for validation and comparison.
- Email and phone formats must be validated. Email is trimmed/case-normalized where appropriate; phone numbers should be normalized to E.164 where the available country context permits it.
- Exact verification, uniqueness, and WhatsApp-provider behavior are not approved by this baseline.

### 7.3 Roles versus Contact purposes

**Status: `CONFIRMED` — Current MVP decision**

Contact roles and communication purposes are different concepts:

| Concept | Meaning | Examples |
|---|---|---|
| Contact role | The Contact's business relationship to the Customer | `PRIMARY`, `BILLING`, `FINANCE`, `ESCALATION` |
| Contact purpose | Why a particular Contact Detail may be used | `BILLING`, `PAYMENT`, `PAYMENT_REMINDER` |

- `PRIMARY` is not automatically an invoice recipient.
- Purpose assignment identifies the eligible Contact Detail(s).
- A shared mailbox, named person, department, or general Customer-owned address can serve a purpose.
- Future AP/Vendor onboarding defines its own purposes rather than reusing AR purposes.
- Recipient-resolution precedence, Customer delivery overrides, reminder merge/replace behavior, and per-document recipient overrides remain `REVIEW` under their owning delivery/reminder requirements.

### 7.4 Communication history and readiness

**Status: `CONFIRMED` — Current MVP decision**

- Customer approval is not universally blocked merely because no email/contact is present.
- When automatic invoice delivery, a manual send, reminder, or escalation is requested, the required purpose must resolve to an active, valid Contact Detail or that communication action is blocked with a clear error.
- A missing recipient does not undo or roll back an already finalized financial document.
- A delivery/reminder request snapshots its resolved recipient values. Later Contact or Contact Detail changes do not change queued, sent, failed, or historical evidence.

## 8. Payment Term and Default Credit Period

### 8.1 One reusable concept

**Status: `CONFIRMED` — Current MVP decision**

- Company Configuration owns reusable Payment Term options such as Immediate, 7 days, 15 days, and 30 days.
- For the current simple terms, `credit_days` is the business value used to derive a due date. `IMMEDIATE` means zero days; `NET_DAYS` means a positive number of days.
- The term name is a business-facing label. The term type is a controlled technical classification and need not be exposed as a second business choice when it can be derived from the selected option.
- Customer may select at most one Company-owned Payment Term as its `Default Credit Period`.
- Do not store an independently editable Customer `default_credit_days` alongside the selected Payment Term. That would create two sources of truth.

### 8.2 Inheritance and transaction override

**Status: `CONFIRMED` — Current MVP decision**

Resolution order is:

1. Customer default Payment Term, when active and valid for the owning Company.
2. Otherwise the owning Company's active default Payment Term.

The selected term may be carried into the Sales Order and then the invoice. Before invoice finalization, an authorized user may select another active Company Payment Term for that specific transaction—for example, Immediate instead of the Customer's usual 7 days. An override that differs from the inherited/agreed value requires reason and audit evidence according to the owning Sales Order/Billing rule.

Finalized documents snapshot the selected term identity/label as needed, credit days, calculation basis, and due date. The due date is derived from the applicable invoice/document date, not from the email-send timestamp. Later master changes do not recalculate finalized documents.

### 8.3 Credit Limit

**Status: `DEFERRED` — Future consideration**

Credit Limit, shared group exposure, credit holds, and order/invoice blocking based on exposure are outside this Customer Onboarding MVP baseline.

## 9. Receivable GL

**Status: `CONFIRMED` — Current MVP decision**

- Customer Onboarding does not select or map a Receivable GL account.
- The current one-default rule remains `company_accounting_settings.default_receivable_gl_account_id`.
- Eligible finalized Customer-Sale documents preserve the resolved Company Receivable GL identity.
- Customer/category/export-specific account determination may be designed later only if a real approved requirement appears.

## 10. Approval, Workflow Persistence, and Change Materiality

### 10.1 One Customer business workflow

**Status: `CONFIRMED` — Current MVP decision**

- New onboarding and later material amendments use one Customer business workflow: Draft -> Submit -> Finance/Authorized Review -> Approve, Approve with Changes, Return, or Reject.
- A returned Customer is corrected and resubmitted.
- The approver cannot be the original maker/submitter for that submission.
- Approval is aggregate-specific evidence. Customer, Sales Order, and Billing may share small approval primitives later, but they do not share one business workflow or a generic workflow builder.
- The current Customer workflow covers both `COMMON/PARTY-LIKE` and `CUSTOMER/AR-SPECIFIC` changes. Separate Party and Customer approval workflows are not introduced until a shared Party model is explicitly approved.

**Workflow persistence status: `CONFIRMED` for the current working design.** Use one `customer_requests` row containing authoritative editable `draft_data JSONB`, immutable `customer_request_snapshots` created at Submit/Resubmit and Authority approval-with-changes, and append-only `customer_request_actions`. The exact historical requirement is the submitted **request payload**: complete for `NEW_CUSTOMER` where applicable and delta-shaped for an amendment. Typed relational Customer revision children and separate submission/decision tables are superseded.

The request status set is `DRAFT`, `SUBMITTED`, `RETURNED`, `APPROVED`, `REJECTED`, and `CANCELLED`. `RESUBMIT` and `APPROVE_WITH_CHANGES` are actions, not statuses. `UNDER_REVIEW` and `WITHDRAWN` are not used. Maker may cancel only a `DRAFT`; returned requests are corrected and resubmitted by the same Maker. Approved, rejected, and cancelled requests are terminal.

### 10.2 Material changes

**Status: `CONFIRMED` — Current MVP decision**

Material Customer changes require a new controlled approval cycle and immutable request snapshots. Current material categories are:

- legal/display identity where it affects the approved Customer identity;
- PAN and other applicable jurisdiction-specific legal identifiers;
- GST registration additions, replacements, inactivations, or material corrections;
- physical Location additions and address/jurisdiction changes;
- Customer default Payment Term/credit period; and
- any future field explicitly classified as approval-controlled.

System-controlled identity/workflow values, including Customer Code once allocated, are not ordinary reviewer-editable fields.

### 10.3 Non-material operational changes

**Status: `REVIEW` — Business-policy decision**

The physical Contact, Contact Detail, role, and purpose tables are part of the working design. Whether post-approval Contact changes require an approval request or allow direct authorized edit plus audit is not final. The wider Class A/B/C change-control model and its `APPROVAL_REQUIRED` versus `DIRECT_EDIT_ALLOWED` classification also remain `REVIEW`; no configuration tables are introduced yet.

### 10.4 Finance review and override

**Status: `CONFIRMED` — Current MVP decision**

- Standard Finance review returns a submitted onboarding/amendment when a material correction is required.
- An elevated, explicit permission may allow Finance to edit and approve in one audited action.
- The chosen design preserves the original Maker snapshot and creates an `AUTHORITY_APPROVED` snapshot derived from it when Authority changes business-entered data. The action, exact approved values, reason, and maker/checker evidence remain traceable.
- This override cannot bypass maker/checker separation, change system-controlled identity fields, or transform the submission into a different legal Customer.

The exact permission name and storage contract belong to the later authorization/database design.

## 11. Workflow Journey, Revision, Version, Snapshot, and Audit

**Status: `CONFIRMED` — Current MVP decision**

| Concept | Meaning | Customer example |
|---|---|---|
| Workflow journey | Request/action/submission/decision state, actor, time, and reason | Submitted, returned, corrected, resubmitted, approved |
| Request snapshot | Immutable exact request payload at Submit/Resubmit or Authority approval-with-changes | Maker submission 2 or Authority-approved snapshot derived from it |
| Effective-dated version | A value valid during a defined time range | Customer Location address/version history |
| Transaction snapshot | Values frozen on a transaction or delivery intent | Customer legal name, GSTIN, Bill-To/Ship-To, credit days, due date, recipient email on a finalized document/request |
| Audit history | Who did what, when, why, and the before/after evidence | Customer returned, endpoint changed, Finance override used |

Current history strategy is:

1. current Customer master state for current operations;
2. append-only audit evidence for changes/actions;
3. immutable JSONB request snapshots plus append-only request actions;
4. typed transaction and delivery snapshots for finalized historical truth; and
5. selective effective dating only where separately justified.

No `current_revision_no` / `latest_revision_no` belongs in the operational Customer core. `snapshot_no` sequences immutable request payloads only; it is not a legal-name version, Location effective-version number, transaction snapshot number, or audit-event sequence.

Customer legal-name changes do not require a separate general-purpose effective-dated name-version table in MVP. Request snapshots, audit history, and finalized transaction snapshots preserve the approved evidence.

## 12. Approval and Operational Readiness

### 12.1 Customer approval readiness

**Status: `CONFIRMED` — Current MVP decision**

A Customer cannot be approved for operational use unless the submitted onboarding/amendment state provides:

- owning Company and required authorization context;
- non-blank legal identity and country;
- India-MVP PAN through the applicable legal-identifier type/rule and other currently applicable statutory identity;
- GST registration details when the Customer is GST-registered;
- at least one usable approved physical Location;
- a resolvable default credit period through Customer selection or Company default; and
- any supporting evidence made mandatory for that Customer type/jurisdiction after the supporting-document matrix is reviewed.

Customer Organisation is optional. Communication readiness is deliberately evaluated separately.

### 12.2 Communication readiness

**Status: `CONFIRMED` — Current MVP decision**

- Customer approval does not imply that every communication purpose is ready.
- Readiness for `INVOICE_DELIVERY`, `PAYMENT_REMINDER`, or `COLLECTION_ESCALATION` is checked when that capability is enabled or executed.
- Each enabled/requested purpose must resolve to at least one eligible active endpoint according to the eventual delivery/reminder precedence rules.

## 13. Lifecycle and Open Decisions

### 13.1 Inactivation

**Status: `CONFIRMED` — Current MVP decision**

An inactive Customer is unavailable for new Sales Orders, new invoices, and other new commercial selection. Existing finalized documents, receivables, receipts, allocations, delivery evidence, audit, and statutory history remain accessible and may continue through their permitted settlement/correction processes.

### 13.2 Reactivation or re-onboarding

**Status: `OPEN` — Current MVP decision required**

The product still needs to decide whether an inactive Customer can:

- return to use through an amendment/re-onboarding approval on the same stable Customer/code; or
- remain terminal while a separately controlled replacement identity is created.

The decision must account for Company-scoped PAN/GSTIN duplicate control and historical continuity. No implementation may create a duplicate Customer merely to bypass the unresolved lifecycle rule.

### 13.3 Customer Code

**Status: `CONFIRMED` — Current MVP working design**

Customer Code is system-generated as Company-configured prefix plus a Company-scoped sequential number. The Company selects numeric padding; the sequence starts at 1, never resets automatically, and is allocated only inside successful `NEW_CUSTOMER` approval/publication. Existing amendments preserve the allocated code. Exact counter/locking/idempotency mechanics belong to later backend design. Prefix validation, padding overflow, and whether setup blocks Company activation or only Customer approval remain configuration/physical-design `REVIEW` details.

## 14. Remaining Review and Deferred Items

| Item | Status | Boundary |
|---|---|---|
| Inactive Customer reactivation/re-onboarding | `OPEN` | Must preserve duplicate control and history. |
| Customer Code prefix validation/padding overflow/readiness gate | `REVIEW` | Core generation direction is selected; detailed configuration contract remains. |
| Post-approval Contact change control | `REVIEW` | Approval request versus direct authorized edit plus audit. |
| GST-to-Location mapping change control | `REVIEW` | Whether the version change requires approval. |
| Class A/B/C change-control model | `REVIEW` | Do not add configuration tables yet. |
| Shared legal-identifier type naming/alignment | `REVIEW` | Consider generic reference naming without authorizing a migration. |
| Customer delivery/reminder override precedence and merge/replace behavior | `REVIEW` | Owned by Delivery/Reminder specifications, not inferred from contact roles. |
| Supporting-document matrix | `REVIEW` | Exact documents depend on customer type/jurisdiction and approval policy. |
| Non-India statutory rules | `REVIEW` | India-first PAN/GST behavior must not be generalized without jurisdiction rules. |
| Endpoint verification and provider-specific WhatsApp behavior | `REVIEW` | Format validation is current; verification/provider integration is separate. |
| Credit Limit and group exposure | `DEFERRED` | Not part of MVP. |
| Shared Party/Vendor/Contact master | `DEFERRED` | Future architecture only after explicit approval. |
| Separate Party and Customer approval workflows | `DEFERRED` | Depends on a future shared Party model. |
| Exact physical types, indexes, constraints, APIs, and migrations | `REVIEW` / `DEFERRED` | Review/freeze the 14-table working design before implementation. |

## 15. Design Gate for the Next Phase

The canonical [Customer Onboarding and Customer Master Database Design](../CUSTOMER_ONBOARDING_ERD.md) is the **CURRENT WORKING DESIGN / PROPOSED FOR FREEZE**. [Customer Onboarding Workflow Persistence Options](../CUSTOMER_ONBOARDING_WORKFLOW_OPTIONS.md) is retained as a superseded historical alternatives record. Neither authorizes implementation.

That design must:

- translate only `CONFIRMED` decisions into operational candidate persistence;
- keep `OPEN`, `REVIEW`, and `DEFERRED` items visibly unresolved;
- avoid creating a shared Party/Contact master;
- preserve the common/Party-like versus Customer/AR-specific boundary;
- retain stable Customer Location identity plus effective-dated versions aligned with the existing Company Location concept; and
- keep generic legal-identifier types aligned with the existing Company concept without silently renaming implemented references;
- retain the selected Request + JSONB Snapshots + Actions design without reintroducing superseded workflow alternatives; and
- avoid treating existing `ADD` candidates in `requirements/database.md` as already approved tables.
