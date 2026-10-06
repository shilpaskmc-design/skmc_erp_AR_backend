# Customer Module

## Purpose and status

The Customer module supports Company-specific Customer onboarding, approved-Customer changes, approval, publication to the operational Customer Master, and retention of Customer request history.

It covers Customer legal and statutory information, GST registrations, reusable Locations, supporting documents, Contacts, Contact Details, Contact roles, Contact purposes, commercial defaults, and the Customer request journey.

Pending or unapproved request data must never overwrite the approved operational Customer Master. Approved Customer data is consumed by Sales Order, Billing/Invoicing, Accounts Receivable, and Receipts/Collections.

**Customer data-model status:** `CURRENT WORKING DESIGN / PROPOSED FOR FREEZE`.

The module documentation does not authorize migrations, ORM models, APIs, services, routes, frontend work, or tests. `CONFIRMED` decisions govern the current proposal; `OPEN`, `REVIEW`, and `DEFERRED` boundaries retain those statuses.

## Boundaries

- A Customer belongs to one seller Company.
- Common/Party-like identity remains physically Customer-owned for the current MVP.
- Customer/AR-specific approval, Customer Code, Payment Term selection, and communication purposes remain AR-owned.
- No shared Party, Vendor, Contact, or generic Counterparty master is introduced.
- Customer approval is aggregate-specific and does not create a generic workflow engine.

## Dependencies

- Company Configuration for Customer Code configuration and reusable Payment Terms.
- Shared Company, geography, entity-type, statutory-reference, stored-file, authorization, and audit capabilities.
- Shared approval/audit semantics in [Approval and Audit Requirements](../../requirements/approval_and_audit).
- Global ownership constraints in [Module Boundaries](../../architecture/module_boundaries.md).

## Downstream consumers

- Sales Order selects an approved active Customer and eligible Customer Locations.
- Billing uses approved Customer/statutory context and preserves transaction-time snapshots.
- Accounts Receivable uses the Company-level Receivable GL resolution boundary.
- Receipts and Collections use approved Customer identity without rewriting Customer history.

## Canonical documents and reading order

1. [Requirements](requirements.md) - what the module must support.
2. [Workflows](workflows.md) - request states, actions, actors, and publication journey.
3. [Data Model](data_model.md) - canonical 14-table persistence proposal and ERD.
4. [Business Rules](business_rules.md) - validation, ownership, invariants, readiness, and history rules.
5. [Open Decisions](open_decisions.md) - unresolved `OPEN` and `REVIEW` items only.

The editable ERD source is [data_model.mmd](data_model.mmd). Historical workflow alternatives remain in [Customer Onboarding Workflow Persistence Options](../../history/superseded/customer/customer_onboarding_workflow_options.md) and are not current authority.
