# Customer Module Requirements

## Status and scope

**Document status:** `PROPOSED` for review. This document defines what the Customer module must support; it does not define physical tables, APIs, or implementation mechanics.

The current MVP supports new Customer onboarding and controlled changes to an existing approved Customer within one seller Company.

## Customer search before onboarding

Authorized users must be able to search within the owning Company before creating a Customer request. Search must support applicable Customer/legal/display name, normalized legal identifiers such as India PAN, normalized GSTIN, Customer Organisation, and allocated Customer Code.

Search and duplicate checks must respect Tenant isolation and explicit Company authorization.

## New Customer onboarding

The module must allow an authorized Maker to:

- create and save a new Customer request as Draft;
- capture the Customer's legal/display identity and country context;
- capture applicable legal identifiers;
- state whether the Customer is GST-registered;
- capture one or more GST registrations where applicable;
- capture reusable Customer Locations;
- associate applicable GST context with a Location;
- attach required supporting documents through the shared stored-file capability;
- capture Contacts, Contact Details, Contact roles, and Contact purposes;
- optionally associate the Customer with a Customer Organisation;
- select an optional Company-owned default Payment Term; and
- submit the request for Authority review.

The Customer must not become operational merely because a Draft or submitted request exists.

## Legal and statutory information

- For India-MVP Customers, PAN must be captured where applicable to the Customer's entity/legal type.
- PAN, CIN, LLPIN, and other non-GST identifiers must use the generic Customer legal-identifier concept.
- GSTIN must remain part of Customer GST registrations rather than the generic identifier collection.
- A Customer may be GST-registered or unregistered.
- A GST-registered Customer may have multiple distinct GST registrations.
- Applicable PAN/GST supporting evidence must be available for review.
- Approved statutory identity changes must follow controlled Customer change processing and preserve historical transaction truth.

The legal/statutory identifiers and supporting evidence applicable outside India remain under `REVIEW`.

## Customer Organisation

- A Customer may be standalone or belong to one optional Company-specific Customer Organisation.
- Customer Organisation groups separately billable Customer legal entities.
- It must not be confused with the Tenant's seller-side Organisation structure.
- MVP does not require nested Customer Organisations, inherited configuration, shared balances, shared credit exposure, or Organisation-level approval.

## Customer Locations

- A Customer must support reusable physical Locations such as registered office, branch, office, or warehouse.
- A usable Location must exist before Customer approval.
- Approved Location changes must preserve earlier address history.
- Bill-To and Ship-To are transaction selections from eligible Locations, not permanent Customer Location roles.
- A new master address required by a transaction must follow the Customer change process rather than becoming invoice-only free text.
- Finalized downstream documents must retain the exact address they used.

## Contacts and communication information

- A Customer may have person, department, or general/shared Contacts.
- A Contact may have multiple Contact Details.
- Initial Contact Detail types include email, phone, mobile, and WhatsApp.
- Contact identity, Contact Details, Contact roles, and Contact purposes must remain distinct.
- A `PRIMARY` role must not automatically make a Contact Detail an invoice recipient.
- Customer approval must not be universally blocked only because no Contact or email is present.
- A requested delivery, reminder, or escalation must resolve an eligible active Contact Detail before that communication action proceeds.

Post-approval Contact change control remains under `REVIEW`.

## Commercial defaults

- A Customer may select at most one active Payment Term owned by the same Company as its default credit period.
- When no Customer default is selected, the active Company default Payment Term applies.
- Customer must not maintain an independent second editable credit-days value.
- Customer Onboarding must not select or map a Customer Receivable GL account.
- Customer Credit Limit and group exposure are `DEFERRED` outside this MVP.

## Draft, review, and decision outcomes

The module must support:

- Save Draft;
- Submit for Approval;
- Authority review;
- Return with remarks;
- correction and Resubmit;
- Approve;
- Approve with Changes under elevated authority and audit requirements;
- Reject; and
- Draft cancellation.

The exact state/action contract is defined in [Workflows](workflows.md).

## Existing approved Customer changes

- The same Customer request capability must support controlled changes to an existing approved Customer.
- Material legal and statutory changes require approval. Approval treatment for other Customer changes, including applicable Location changes, follows the confirmed change-control policy.
- An existing-Customer request must identify its target Customer.
- An amendment may contain only the relevant requested delta and context.
- Pending amendment data must not overwrite approved operational data.
- Current MVP permits only one open approval request for an existing Customer.

Post-approval Contact and GST-to-Location mapping change policy remains under `REVIEW`.

## Approval and publication

A Customer may become available for operational use only after successful approval/publication. Publication must ensure that the approved state has:

- owning Company and authorization context;
- non-blank legal identity and country;
- applicable legal/statutory identifiers;
- GST details when registered;
- at least one usable Location;
- a resolvable default credit period; and
- required supporting evidence where applicable.

Successful new-Customer publication must allocate the system-generated Customer Code. Approval/publication must preserve maker/checker separation and must not publish data that fails duplicate or readiness validation.

## Customer lifecycle

- An authorized Authority may inactivate an approved Customer.
- An inactive Customer must not be selectable for new commercial activity.
- Existing documents, receivables, receipts, allocations, communications, audit, and statutory history must remain available through permitted downstream processes.
- Reactivation versus controlled re-onboarding remains `OPEN`.

## Historical integrity

The module must preserve:

- the approved operational Customer state used for current operations;
- exact submitted and Authority-approved request payloads;
- the request action journey and remarks;
- effective Customer Location history;
- audit evidence; and
- downstream transaction and communication snapshots.

Later Customer-master changes must never rewrite finalized transaction or communication evidence.

## Out of current MVP

- Customer Credit Limit, group exposure, and exposure-based blocking.
- A shared Party, Vendor, Contact, or Counterparty master.
- Separate Party and Customer approval workflows.
- Parallel amendment workflows for one existing Customer.
- A generic workflow builder, change-policy engine, or universal versioning engine.
