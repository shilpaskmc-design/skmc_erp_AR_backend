# Customer Onboarding Requirements

## Status and Governing Baseline

This requirement is **PROPOSED** for review and does not authorize implementation. `CONFIRMED` means agreed in the current planning baseline; `OPEN`, `REVIEW`, and `DEFERRED` items must remain unresolved.

The detailed status register is [Customer Onboarding Architecture and Decision Baseline](../architecture/customer_onboarding_decision_baseline.md). The canonical persistence artifact is [Customer Onboarding and Customer Master Database Design](../CUSTOMER_ONBOARDING_ERD.md), status `CURRENT WORKING DESIGN / PROPOSED FOR FREEZE`. [Customer Onboarding Workflow Persistence Options](../CUSTOMER_ONBOARDING_WORKFLOW_OPTIONS.md) is retained only as a superseded historical alternatives record.

No API, migration, model, service, route, frontend, or test implementation is authorized.

## Purpose and Ownership

**Status: `CONFIRMED` — Current MVP decision**

Customer Onboarding creates and maintains the external legal/customer identity and AR relationship required by one seller Company.

- A Customer is Company-specific.
- Legal identity, statutory identifiers, GST registrations, Locations, Contacts, and Contact Details are common/Party-like in meaning but remain Customer-owned for MVP.
- Default Payment Term/credit period, Customer Code lifecycle, approval, and Contact purposes are Customer/AR-specific.
- No shared Party, Vendor, Contact, or generic Counterparty master is introduced.
- A future Party model may extract/link common identity without absorbing AR-specific behavior.

## Search and Duplicate Control

**Status: `CONFIRMED` — Current MVP working design**

Authorized users can search within the owning Company by Customer/legal/display name, normalized legal identifier including India PAN, normalized GSTIN, optional Customer Organisation, and allocated Customer Code.

For the India MVP, PAN is mandatory. PAN and other non-GST statutory identifiers are Customer child records classified by a reusable legal-identifier type; they are not direct `customers` columns. GSTIN remains in Customer GST registrations.

- Approved/current normalized identifier values and GSTINs are unique within the owning seller Company.
- Temporary duplicate Drafts may exist.
- Submit hard-validates against approved/live Customers and applicable pending submitted onboarding requests.
- Approval/publication validates again inside the publication operation.
- No `customer_identifier_claims` table is used for MVP.
- Concurrent-submit race handling is a later backend/database implementation invariant, not a new business table.

## Customer Organisation

**Status: `CONFIRMED` — Current MVP decision**

- Customer Organisation is an optional Company-specific external grouping of separately billable Customer legal entities.
- A Customer may be standalone.
- It is not the Tenant's seller-side `core.organisations` grouping and is not Party Master.
- MVP has no nesting, inherited configuration, shared credit exposure, or Organisation-level approval.
- Inactive Customer Organisations cannot receive new associations; history remains intact.

## Customer Information

Onboarding may include legal/display identity, generic non-GST identifiers, GST-registration status and registrations, stable Locations and their effective versions, Contacts and Contact Details, Contact roles and purposes, optional Customer Organisation, default Payment Term/credit period, conditional documents, and the system-generated Customer Code produced at publication.

### Customer Code

**Status: `CONFIRMED` — Current MVP working design**

Customer Code is a Company Configuration responsibility:

```text
Customer Code = Company-configured prefix + Company-scoped sequential number
```

- Company configures the prefix and numeric padding/digit length.
- Sequence starts at 1, is Company-scoped, and does not reset automatically.
- Code is allocated only when `NEW_CUSTOMER` is successfully approved/published.
- Code remains stable after allocation; amendments do not replace it.
- Exact counter locking and idempotency mechanics belong to backend design.
- Prefix validation, padding overflow, and whether setup blocks Company activation or Customer approval remain configuration/physical-design `REVIEW` details.

### Credit Limit

**Status: `DEFERRED` — Future consideration**

Credit Limit, group exposure, and exposure-based commercial blocking are not part of this MVP.

## GST Registrations

**Status: `CONFIRMED` — Current MVP decision**

- A Customer may be GST-registered or unregistered.
- A registered Customer needs applicable GST details before approval; an unregistered Customer may have none.
- One Customer may have multiple distinct registrations.
- GST registration and physical Location are different concepts; a Location version may reference an applicable same-Customer registration.
- Approved GSTIN is not casually overwritten. Inactivate the obsolete/incorrect registration and introduce the replacement through controlled change.
- Final financial documents preserve the GST identity actually used.

Non-India statutory requirements and the supporting-document matrix remain `REVIEW`.

## Supporting Documents

**Status: `CONFIRMED` storage boundary; `REVIEW` required-document matrix**

- Customer documents reference existing `stored_files`; no file bytes or second storage framework is introduced.
- A document may evidence a Customer identifier or GST registration.
- PAN/GST supporting evidence is required where applicable to onboarding.
- Immutable request snapshots preserve exact submitted file references.
- Exact mandatory document types by jurisdiction/entity/customer type remain `REVIEW`; no large configurable rule engine is introduced.
- The `document_type_id` reference target must be aligned to an approved reusable reference during physical freeze; this does not add a Customer table now.

## Locations, Bill-To, and Ship-To

### Stable identity and effective versions

**Status: `CONFIRMED` — Current MVP working design**

- `customer_locations` stores stable Location identity, owning Customer/Company, Location code, and lifecycle.
- `customer_location_versions` stores effective Location name, full address, geography, applicable GST registration, registered-address designation, and validity period.
- Address-bearing fields are not duplicated in the stable Location row.
- An approved address/effective change creates a new version rather than rewriting history.
- A pending Location edit does not alter the current approved version.
- Historical versions remain queryable; used Locations are inactivated rather than hard-deleted.
- Future scheduling/backdating is not introduced.
- Whether changing GST-to-Location mapping requires approval remains `REVIEW`.

### Transaction use

**Status: `CONFIRMED` — Current MVP decision**

- Bill-To and Ship-To are transaction selections, not permanent Location flags.
- Sales Order selects an eligible approved Customer Location for Bill-To and either an eligible Customer Location or, where allowed, a seller Company Location for Ship-To.
- A draft invoice may inherit and, with authority, change those selections before finalization.
- A new master address follows the Customer change path; invoice-only free-text master addresses are not the normal solution.
- Finalized documents snapshot the exact address used; later master changes never rewrite history.

## Contacts and Communication

### Contact identity and details

**Status: `CONFIRMED` — Current MVP structure**

- Customer-owned Contact identity supports `PERSON`, `DEPARTMENT`, and `GENERAL`.
- Contact may optionally associate with a Customer GST registration and/or Location.
- Reachability is stored separately as `customer_contact_details`.
- Initial detail types include `EMAIL`, `PHONE`, `MOBILE`, and `WHATSAPP`.
- Entered `detail_value` and backend `normalized_value` are distinct; format validation/normalization remains required.
- Endpoint verification/provider behavior is not part of this database freeze.

### Roles and purposes

**Status: `CONFIRMED` — Current MVP structure**

- Contact roles such as `PRIMARY`, `BILLING`, `FINANCE`, and `ESCALATION` describe organisational/business role.
- Contact purposes such as `BILLING`, `PAYMENT`, and `PAYMENT_REMINDER` explain why a particular Contact Detail may be used.
- Role and purpose are separate. `PRIMARY` never automatically means invoice recipient.
- TO/CC/BCC, fallback, priority, recipient resolution, verification, and per-document overrides remain `REVIEW` in Delivery/Reminder design.

### Change control and communication readiness

**Status: `REVIEW` change control; `CONFIRMED` readiness boundary**

- Whether post-approval Contact, Detail, role, and purpose changes require approval or direct authorized edit plus audit is not final.
- The Class A/B/C model and its `APPROVAL_REQUIRED` versus `DIRECT_EDIT_ALLOWED` classifications are not adopted; no policy tables are introduced.
- Contact/email is not a universal Customer approval prerequisite.
- An enabled/requested send, reminder, or escalation must resolve to an eligible active Contact Detail.
- Missing recipients block communication, not completed financial finalization.
- Delivery/reminder requests snapshot resolved recipient values.

## Payment Term and Default Credit Period

**Status: `CONFIRMED` — Current MVP decision**

Company Configuration owns reusable `IMMEDIATE` and `NET_DAYS` Payment Terms. Customer may select one active same-Company term as its Default Credit Period; otherwise the active Company default applies.

Do not maintain an independent Customer credit-days field. `credit_days` belongs to the reusable term. Sales Order/invoice may inherit the resolved term and an authorized user may select another active term before finalization with required reason/audit. Finalized documents snapshot the selected term, credit days, and derived due date. Due date derives from the applicable document date, not email-send time.

## Receivable GL

**Status: `CONFIRMED` — Current MVP decision**

Customer Onboarding does not map Receivable GL. The Company-level default in `company_accounting_settings` remains the eligible Customer-Sale source; finalized transactions preserve the resolved GL identity.

## Customer Request and Approval Workflow

### Persistence boundary

**Status: `CONFIRMED` — Current MVP working design**

- `customer_requests` stores the case, status, owner, target, and one authoritative editable `draft_data JSONB`.
- No `customer_request_drafts` table exists.
- Submit/Resubmit copies the exact Draft into an immutable `customer_request_snapshots` JSONB row.
- `customer_request_actions` stores append-only state/action evidence.
- PostgreSQL is authoritative; optional browser IndexedDB is recovery/cache only.
- JSON contains `stored_files` references, not binaries.

`NEW_CUSTOMER` has null `target_customer_id` and normally carries a complete onboarding payload. An existing-Customer request such as `ADD_GST`, `ADD_LOCATION`, or `UPDATE_CUSTOMER` targets the Customer and may carry only the relevant delta/context. `ADD_CONTACT` is used only if the unresolved Contact change policy later requires approval.

### Maker ownership

**Status: `CONFIRMED` — Current MVP decision**

The request creator is its Maker. Only that Maker normally edits it while editable; other ordinary Makers do not. Submit locks Maker editing. After Return, the same Maker corrects and resubmits the same request. Approver cannot be the Maker/submitter.

### Status model

| Current state | Action | Next state |
|---|---|---|
| New | Create | `DRAFT` |
| `DRAFT` | `SUBMIT` | `SUBMITTED` |
| `DRAFT` | `CANCEL` | `CANCELLED` |
| `SUBMITTED` | `RETURN` | `RETURNED` |
| `RETURNED` | `RESUBMIT` | `SUBMITTED` |
| `SUBMITTED` | `APPROVE` | `APPROVED` |
| `SUBMITTED` | `APPROVE_WITH_CHANGES` | `APPROVED` |
| `SUBMITTED` | `REJECT` | `REJECTED` |

`RESUBMIT` and `APPROVE_WITH_CHANGES` are actions, not statuses. `UNDER_REVIEW` and `WITHDRAWN` are not used. Maker may cancel only a Draft, not a Returned request. Return requires remarks. Approved, rejected, and cancelled requests are terminal. A rejected request is not reopened/copy-resumed; future onboarding begins a new request.

### Snapshots and Authority editing

- Submit/Resubmit creates a `MAKER_SUBMISSION` snapshot.
- Return never changes an existing snapshot; each Return action retains its remarks.
- If Authority edits business-entered data, original Maker data remains unchanged and an `AUTHORITY_APPROVED` snapshot may point to its source Maker snapshot.
- Authority cannot edit system-controlled fields or transform one legal Customer into an unrelated Customer.
- `APPROVE_WITH_CHANGES` preserves exact approved data, action, actor, and remarks/reason evidence.
- No field-level review-findings table or autosave action is required.

### One open request for an existing Customer

**Status: `CONFIRMED` — MVP simplification**

For non-null `target_customer_id`, only one request may be in `DRAFT`, `SUBMITTED`, or `RETURNED`. Parallel amendment requests are outside MVP.

## History Semantics

**Status: `CONFIRMED` — Current MVP decision**

- **Request Draft:** current editable proposed payload.
- **Request snapshot:** exact immutable payload submitted/approved; complete for new onboarding where applicable and delta-shaped for amendments.
- **Request action:** state, actor, time, and remarks/reason.
- **Effective-dated version:** Location information valid over a time range.
- **Transaction snapshot:** Customer/address/statutory/term/recipient values frozen by a finalized transaction or communication request.
- **Audit history:** who changed what, when, and why.

MVP uses current operational master + request snapshots/actions + audit + Customer Location versions + transaction snapshots. Customer name does not require a separate name-version table. Request JSONB is not a substitute for typed operational or finalized financial data.

## Customer Approval Readiness

**Status: `CONFIRMED` — Current MVP decision**

Approval requires owning Company/authorization context, non-blank legal identity and country, India-MVP PAN and applicable statutory identity, GST details when registered, at least one usable Location/version, a resolvable credit period, and applicable supporting evidence. Customer Organisation is optional. Communication readiness remains separate.

Approval/publication atomically revalidates readiness, authority, current target, Company scope, PAN/GSTIN duplicates, and Customer Code allocation for `NEW_CUSTOMER`. Idempotency for Submit, approval, publication, and code allocation is a later API/backend integrity requirement; exact mechanics are not designed here.

## Inactivation and Reactivation

**Status: `CONFIRMED` Authority-level inactivation; `OPEN` reactivation**

Inactive Customer cannot be selected for new commercial use. Existing transactions, receivables, receipts, allocations, communications, audit, and statutory history remain available through permitted settlement/correction flows.

Whether reactivation uses the same Customer/code or a controlled replacement/re-onboarding path remains `OPEN`. A second Customer must not be created merely to bypass Company-scoped identity uniqueness.

## Remaining REVIEW / OPEN / DEFERRED Items

| Item | Status |
|---|---|
| Class A/B/C change-control model and field classification | `REVIEW` |
| Post-approval Contact change control | `REVIEW` |
| GST-to-Location mapping change control | `REVIEW` |
| Recipient precedence, TO/CC/BCC, fallback, priority, overrides | `REVIEW` |
| Contact Detail verification/provider behavior | `REVIEW` |
| Shared identifier-type and geography FK alignment | `REVIEW` |
| `document_type_id` shared-reference target | `REVIEW` |
| Supporting-document matrix and non-India statutory rules | `REVIEW` |
| Customer Code prefix validation/padding overflow/readiness gate | `REVIEW` |
| Reactivation/re-onboarding | `OPEN` |
| Credit Limit/group exposure | `DEFERRED` |
| Shared Party/Vendor/Contact master | `DEFERRED` |

## Future Boundary

**Status: `CONFIRMED` — Future architectural consideration**

A future shared Party model may link equivalent Customer and Vendor identities and move common identity approval to Party. AR-specific terms, Contact purposes, Customer approval, and commercial behavior remain AR-owned. This does not approve Party tables, Party workflows, shared Contacts, or Vendor architecture in MVP.
