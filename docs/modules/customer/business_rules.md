# Customer Business Rules

## Status and authority

**Document status:** `PROPOSED` Customer decision baseline.

`CONFIRMED` rules below govern the current proposal but do not authorize implementation. Unresolved matters are isolated in [Open Decisions](open_decisions.md). Physical table detail belongs only in [Data Model](data_model.md).

## Ownership and domain boundary

**Status: `CONFIRMED`**

- A Customer belongs to exactly one seller Company.
- The same external legal entity may be represented as separate Customers for different seller Companies.
- Customer search, duplicate checking, approval, code allocation, commercial defaults, and operational use occur in the owning Company context.
- Tenant isolation and explicit Company authorization both apply; Tenant membership alone does not grant Customer access in every Company.
- Legal identity, statutory identity, Locations, Contacts, and Contact Details are common/Party-like in meaning but remain physically Customer-owned for MVP.
- Customer Code, default Payment Term, approval, Contact purposes, and commercial/receivable behavior are Customer/AR-specific.
- Do not introduce a shared Party, Vendor, Contact, or generic Counterparty master for hypothetical future reuse.

Where a Customer change requires approval, it uses the Customer-specific request workflow. No separate Party approval workflow is introduced in MVP. A future approved Party model may extract or link common identity while AR-specific behavior remains under Customer ownership; no placeholder Party key or dual write is introduced now.

## Approved operational state versus pending requests

**Status: `CONFIRMED`**

- Operational Customer data contains only approved/current state.
- Pending onboarding or amendment data remains in the Customer request boundary.
- Pending data must never overwrite live Customer data before approval/publication succeeds.
- Downstream modules may consume only an eligible approved operational Customer.
- Approval outcome, action evidence, Customer publication, and new-Customer code allocation must be atomic.

## Customer Organisation

**Status: `CONFIRMED`**

- Customer Organisation is an optional Company-specific external grouping of separately billable Customer legal entities.
- A Customer may remain standalone.
- It is distinct from the seller-side Organisation that groups the Tenant's own Companies.
- MVP has no nested hierarchy, inherited configuration, shared balance, shared credit exposure, or Organisation-level approval.
- An inactive Customer Organisation cannot accept a new association, but existing history remains intact.

## Legal identifiers and GSTIN

**Status: `CONFIRMED`**

- For India-MVP Customers, PAN must be captured where applicable to the Customer's entity/legal type.
- PAN, CIN, LLPIN, UEN, EIN, ABN, CRN, and future non-GST identifiers use generic Customer identifier records.
- Do not add permanent `customers.pan`, `customers.cin`, or `customers.llpin` columns.
- Each identifier record retains the entered value and a normalized comparison value.
- GSTIN remains separate in Customer GST registrations.
- One Customer may have multiple GST registrations.
- Within one seller Company, one approved/current normalized identifier value of a type or normalized GSTIN may belong to only one Customer legal entity.
- An approved GSTIN is not casually overwritten. Inactivate an obsolete or incorrect registration and introduce its replacement through controlled change.

## Duplicate validation

**Status: `CONFIRMED`**

- Temporary duplicate Drafts may exist.
- Submit performs hard duplicate validation against approved/live Customers and applicable pending submitted requests.
- Approval/publication performs the hard validation again inside the publication operation.
- No `customer_identifier_claims` table is part of MVP.
- Concurrent-submit and publication race handling is a backend/database implementation invariant, not a new business table.

## Customer Locations

**Status: `CONFIRMED`**

- `customer_locations` represents stable Customer Location identity, code, ownership, and lifecycle.
- `customer_location_versions` represents effective-dated Location name, physical address, geography, applicable same-Customer GST context, registered-address designation, and validity.
- Physical address fields belong in Location versions rather than being duplicated in the stable Location row.
- A pending Location change does not alter the current approved Location.
- On approval, the approved Location version becomes the applicable current version according to the confirmed effective-dating rules, and the earlier current version is closed accordingly.
- Historical Location versions remain queryable; historically used Locations are inactivated rather than hard-deleted.
- Bill-To and Ship-To are transaction selections, not permanent Customer Location roles or boolean flags.

## Contacts, details, roles, and purposes

**Status: `CONFIRMED` structure; change control remains `REVIEW`**

- Contact identity supports `PERSON`, `DEPARTMENT`, and `GENERAL`, with a required display label.
- A Contact may optionally reference a same-Customer GST registration and/or Location.
- Contact Details are separate from Contact identity so one Contact may have multiple reachable values.
- Initial detail types include `EMAIL`, `PHONE`, `MOBILE`, and `WHATSAPP`.
- Entered and normalized Contact Detail values remain distinct; backend format validation and normalization are required.
- Contact roles describe the Contact's business relationship to the Customer.
- Contact purposes describe why a specific Contact Detail may be used.
- Roles and purposes are separate. `PRIMARY` never automatically means invoice recipient.
- A named person, department, general contact, or shared mailbox may serve a purpose.
- Future AP/Vendor purposes must not silently reuse AR communication purposes.

## Communication readiness and history

**Status: `CONFIRMED` boundary**

- Customer approval is not universally blocked because no email or Contact is present.
- An enabled/requested delivery, reminder, or escalation must resolve an eligible active Contact Detail or that communication action is blocked with a clear error.
- Missing communication readiness does not undo or roll back an already finalized financial document.

## Payment Term and default credit period

**Status: `CONFIRMED`**

- Company Configuration owns reusable Payment Terms, including current `IMMEDIATE` and `NET_DAYS` concepts.
- A Customer may select at most one active same-Company Payment Term as its default credit period.
- When absent, the active Company default Payment Term applies.
- Do not store an independently editable Customer `default_credit_days` beside the selected Payment Term.
- Sales Order and Billing may inherit the resolved term and permit an authorized transaction-specific change with reason/audit under their own rules.
- Due date derives from the applicable document date, not email-send time.

## Receivable GL

**Status: `CONFIRMED`**

- Customer Onboarding does not select or map a Receivable GL.
- The current source remains the Company-level default Receivable GL.

## Customer Code

**Status: `CONFIRMED` working direction**

- Customer Code is system-generated; it is not ordinary Maker-entered data.
- Customer Code configuration belongs to Company Configuration.
- The format uses a Company-configured prefix and Company-configured numeric padding.
- The sequence starts at 1, is scoped to the Company, and does not reset automatically.
- Code is allocated only during successful `NEW_CUSTOMER` approval/publication.
- The allocated code remains stable through later amendments.
- Counter locking and idempotency are later backend/database mechanics.

Prefix validation, padding overflow behavior, and the Company activation-versus-Customer approval configuration gate remain Company Configuration review dependencies; they do not reopen the selected Customer Code direction.

## Approval and maker/checker rules

**Status: `CONFIRMED`**

- New onboarding and material amendments use one Customer-specific workflow.
- The approver cannot be the Maker/submitter for the applicable submission.
- Standard Authority review returns a request when a material correction is required.
- An authorized Authority may approve with permitted business-entered changes where the required edit/approval permission and audit requirements are satisfied; the original Maker snapshot, exact Authority-approved result, reason, action, and maker/checker evidence must be preserved.
- Authority cannot edit system-controlled fields or transform a request into an unrelated legal Customer.
- Customer, Sales Order, and Billing do not share one generic business workflow.

Material legal and statutory changes require approval. Approval treatment for other Customer changes, including Location, Contact and GST-to-Location changes, follows the confirmed change-control policy.

## Request and history rules

**Status: `CONFIRMED` working direction**

- One Customer request contains the current authoritative editable `draft_data` JSONB payload.
- No separate Customer-request Draft table is required.
- Submit and Resubmit create immutable request snapshots.
- The original Maker submission is never overwritten.
- Authority edit-and-approve creates a separately preserved Authority-approved snapshot derived from the Maker snapshot.
- Actions are append-only workflow evidence containing state/action, actor, time, and remarks/reason.
- Return remarks belong to the Return action; Return never changes an immutable snapshot.
- No field-level review-findings table is currently required.
- New-Customer payloads are normally complete; existing-Customer amendment payloads may contain only the requested delta and context.
- `target_customer_id` is absent for `NEW_CUSTOMER` and identifies the approved Customer for an amendment.
- Current MVP permits only one open approval request per existing Customer.
- Do not add `current_revision_no` or `latest_revision_no` to the operational Customer root.

## History semantics

**Status: `CONFIRMED`**

- Request Draft means the current editable proposal.
- Request snapshot means the exact immutable payload submitted or approved at a workflow point.
- Request action means state/action, actor, time, and remarks/reason evidence.
- Effective-dated version means master data valid during a defined period, currently used for Customer Location history.
- Audit history records who changed what, when, and why.

The Customer-owned history strategy is approved operational master + request snapshots/actions + audit + Customer Location versions. Request JSONB does not replace typed operational data. Customer legal name does not require a separate general-purpose name-version table in MVP.

Downstream modules are responsible for preserving the historical transaction data required by their own finalized-document rules. Customer-master changes must not rewrite finalized downstream evidence.

## Approval readiness

**Status: `CONFIRMED`**

Approval/publication requires the owning Company and authorization context, non-blank legal identity and country, applicable statutory identity including PAN where required for the Customer's entity/legal type, GST details when registered, at least one usable Location, a resolvable Payment Term, and required supporting evidence where applicable. Customer Organisation is optional and communication readiness is evaluated separately.

## Inactivation

**Status: `CONFIRMED` inactivation; reactivation remains `OPEN`**

- An inactive Customer cannot be selected for new Sales Orders, invoices, or other new commercial use.
- Existing transactions, receivables, receipts, allocations, communications, audit, and statutory history remain available through their permitted downstream processes.
- A duplicate Customer must not be created merely to bypass unresolved reactivation policy or Company-scoped identifier uniqueness.

## Deferred and future boundaries

- Customer Credit Limit, group exposure, credit holds, and exposure-based order/invoice blocking are `DEFERRED` outside MVP.
- Shared Party/Vendor/Contact masters and separate Party/Customer approval workflows are future considerations only.
- The design preserves a migration boundary for a future Party model without adding Party structures now.
