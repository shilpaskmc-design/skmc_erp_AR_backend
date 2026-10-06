# Customer Onboarding Workflow Persistence Options — Superseded Alternatives

## Status and decision question

**Status:** `SUPERSEDED` as active design options; retained for historical traceability only.

The current working design is **Request + append-only Actions + immutable JSONB Request Snapshots**, documented in [Customer Onboarding and Customer Master Database Design](CUSTOMER_ONBOARDING_ERD.md). It was selected after these alternatives were compared. Do not implement or count any table set in this historical document.

The business journey is confirmed:

~~~text
DRAFT -> SUBMIT -> AUTHORITY REVIEW
                   -> APPROVE
                   -> APPROVE WITH CHANGES
                   -> RETURN
                   -> REJECT
~~~

Returned onboarding can be corrected and resubmitted. The unresolved question is:

> Do we need only the complete onboarding action journey, formally separate submission/decision records, or the ability to permanently reproduce the exact complete Customer data at every submission/resubmission?

Only one approach may become the physical MVP design. The tables below must not be counted together.

## Approach 1 — Request + Actions

~~~mermaid
flowchart LR
    R[customer_onboarding_requests<br/>current case + editable draft]
    C[request child collections<br/>identifiers / GST / locations / documents]
    A[customer_onboarding_actions<br/>append-only journey]
    R --> C
    R --> A
~~~

Candidate structures:

- `customer_onboarding_requests`
- `customer_onboarding_request_identifiers`
- `customer_onboarding_request_gst_registrations`
- `customer_onboarding_request_locations`
- `customer_onboarding_request_documents`
- `customer_onboarding_actions`

The request may carry proposed Customer header data: Tenant/Company scope, optional Customer Organisation, legal/display name, optional Entity Type, country, GST applicability, optional default Payment Term, status, and actors/timestamps.

Actions are append-only and may include `CREATED`, `SUBMITTED`, `RETURNED`, `RESUBMITTED`, `EDITED_BY_AUTHORITY`, `APPROVED_WITH_CHANGES`, `APPROVED`, and `REJECTED`, with actor/time, from/to status, and reason.

**Strength:** complete action journey with the least formal approval structure.

**Limitation:** does not independently preserve the complete Customer form exactly as it appeared at every submission.

## Approach 2 — Request + Submissions + Decisions

~~~mermaid
flowchart LR
    R[customer_onboarding_requests<br/>current case + editable draft]
    C[request child collections<br/>identifiers / GST / locations / documents]
    S[customer_approval_submissions<br/>each submit or resubmit]
    D[customer_approval_decisions<br/>authority response]
    R --> C
    R --> S
    S --> D
~~~

Candidate structures:

- `customer_onboarding_requests`
- the four request child collections
- `customer_approval_submissions`
- `customer_approval_decisions`

A submission records the request, submission number, submitter, time, and status. A decision records the submission, `APPROVE` / `APPROVE_WITH_CHANGES` / `RETURN` / `REJECT`, actor, time, and reason.

**Strength:** explicit maker/checker submission and decision evidence.

**Limitation:** a submission row alone does not preserve the complete submitted Customer form. A draft lock/hash/copy rule would be required, or exact-form reproduction must be accepted as unavailable.

## Approach 3 — Request + Actions + Revisions

~~~mermaid
flowchart LR
    R[customer_onboarding_requests<br/>current case + editable draft]
    A[customer_onboarding_actions<br/>append-only journey]
    V[customer_onboarding_revisions<br/>immutable submitted header]
    VC[revision child snapshots<br/>identifiers / GST / locations / documents]
    R --> A
    R --> V
    V --> VC
    A -. relevant revision .-> V
~~~

Candidate structures:

- `customer_onboarding_requests`
- `customer_onboarding_actions`
- `customer_onboarding_revisions`
- `customer_onboarding_revision_identifiers`
- `customer_onboarding_revision_gst_registrations`
- `customer_onboarding_revision_locations`
- `customer_onboarding_revision_documents`

Each submit/resubmit creates an immutable revision with a per-request revision number, optional predecessor, complete proposed header, content hash, actor, and time. Typed revision children preserve each submitted collection. Actions may reference the relevant revision.

**Strength:** complete workflow journey and exact submitted-content history.

**Limitation:** highest table, publish, immutability, and retention complexity.

## Shared rules whichever approach is selected

- Pending onboarding/amendment data must not overwrite the operational Customer master before approval.
- Maker/checker separation applies.
- `APPROVE WITH CHANGES` must record authority, reason, and the exact data approved.
- Material and non-material changes retain their documented classification.
- Workflow persistence is not audit persistence.
- Approval outcome and operational publish must be atomic.
- Customer, Sales Order, Billing, and other aggregates may use aggregate-specific tables while following consistent business semantics.
- Do not create a generic workflow engine solely for reuse.

## Not selected

These three approaches were not selected. The exact-history question was resolved for the current working design as preservation of the exact submitted **request payload**: complete for `NEW_CUSTOMER` where applicable, and delta-shaped for amendment requests. `customer_revisions`, typed revision children, `customer_approval_submissions`, and `customer_approval_decisions` are not part of the current 14-table design.
