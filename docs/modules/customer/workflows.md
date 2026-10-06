# Customer Request Workflows

## Status and purpose

**Document status:** `PROPOSED FOR FREEZE`; no implementation authority until reviewed.

This document defines the Customer-specific onboarding and amendment journey. It does not create a generic approval workflow shared by Customer, Sales Order, and Billing.

## Participants

### Maker

- The request creator acts as the Maker.
- Only that Maker normally edits the request while it is `DRAFT` or `RETURNED`.
- Another ordinary Maker does not take over or edit that request.
- Submit locks ordinary Maker editing until the request is returned.
- The Maker cannot approve their own submission.

### Authority

The authorized reviewer acts on a `SUBMITTED` request and may:

- `APPROVE`;
- `APPROVE_WITH_CHANGES` where elevated permission and audit requirements are satisfied;
- `RETURN`; or
- `REJECT`.

## States and actions

Request states are:

- `DRAFT`
- `SUBMITTED`
- `RETURNED`
- `APPROVED`
- `REJECTED`
- `CANCELLED`

Workflow actions are:

- `SUBMIT`
- `RETURN`
- `RESUBMIT`
- `APPROVE`
- `APPROVE_WITH_CHANGES`
- `REJECT`
- `CANCEL`

`RESUBMIT` and `APPROVE_WITH_CHANGES` are actions, not statuses. `UNDER_REVIEW` and `WITHDRAWN` are not part of the current workflow.

## Transition matrix

| Current state | Action | Next state | Required evidence |
|---|---|---|---|
| New | Create | `DRAFT` | Request ownership and editable Draft |
| `DRAFT` | `SUBMIT` | `SUBMITTED` | Immutable Maker-submission snapshot and action |
| `DRAFT` | `CANCEL` | `CANCELLED` | Maker action |
| `SUBMITTED` | `RETURN` | `RETURNED` | Return action with remarks |
| `RETURNED` | `RESUBMIT` | `SUBMITTED` | New immutable Maker-submission snapshot and action |
| `SUBMITTED` | `APPROVE` | `APPROVED` | Approval action referencing the exact submitted snapshot; atomic publication |
| `SUBMITTED` | `APPROVE_WITH_CHANGES` | `APPROVED` | Derived Authority-approved snapshot, reason, action, and atomic publication |
| `SUBMITTED` | `REJECT` | `REJECTED` | Rejection action and applicable remarks |

## Draft and cancellation

- Creation produces one current editable Draft.
- Draft changes do not create operational Customer data.
- Autosave does not create workflow actions.
- The Maker may cancel only while the request is `DRAFT`.
- The Maker cannot cancel after the first Submit, including while the request is `RETURNED`.
- `CANCELLED` is terminal.

## Submit

Submit must:

- validate required request content and Customer readiness applicable at submission;
- hard-check normalized legal identifiers and GSTINs against applicable live and pending submitted Customers/requests;
- capture the exact current Draft as an immutable `MAKER_SUBMISSION` snapshot;
- record the `SUBMIT` action and actor; and
- move the request to `SUBMITTED`.

Temporary duplicate Drafts may exist, but a conflicting request must not pass Submit merely because it was created first.

## Return and Resubmit

- Authority may return a `SUBMITTED` request with remarks.
- Return moves the request to `RETURNED` and never edits or replaces its prior submission snapshot.
- The same Maker corrects the returned request.
- Resubmit creates a new immutable `MAKER_SUBMISSION` snapshot and returns the request to `SUBMITTED`.
- Every Return action retains its own remarks.

## Approve

- Authority approves the exact submitted snapshot.
- Approval revalidates authorization, request status, current target, Company scope, readiness, normalized identifiers, GSTINs, and Customer Code allocation where applicable.
- Approval evidence and operational publication must be atomic.
- Pending data must not overwrite live Customer data before the approval/publication operation succeeds.
- `APPROVED` is terminal.

## Approve with Changes

An authorized Authority may edit business-entered values and approve in one audited action where permitted and audit requirements are satisfied.

- The original Maker snapshot remains immutable.
- The exact edited result is stored as a derived `AUTHORITY_APPROVED` snapshot.
- The action records actor, time, source snapshot, reason/remarks, and outcome.
- Authority cannot change system-controlled fields, bypass maker/checker separation, or transform the request into an unrelated legal Customer.

## Reject

- Authority may reject a `SUBMITTED` request.
- `REJECTED` is terminal.
- A rejected request is not reopened or copy-resumed.
- Later onboarding starts with a new request.

## New Customer journey

For `NEW_CUSTOMER`:

- the target Customer is absent before approval;
- the submitted payload is normally a complete onboarding payload;
- successful approval publishes the approved operational Customer aggregate; and
- Customer Code is allocated only as part of successful publication.

## Existing Customer change journey

For an existing-Customer change:

- the request identifies the approved target Customer;
- the request may carry only the relevant delta and context;
- pending data never mutates the approved Customer before publication; and
- only one request for that target may be `DRAFT`, `SUBMITTED`, or `RETURNED` in the current MVP.

Whether a Contact-only change must use this workflow remains under `REVIEW` in [Open Decisions](open_decisions.md).

## History produced by the journey

- The editable Draft represents only the current proposal.
- Request snapshots preserve exact Maker-submitted or Authority-approved payloads.
- Actions preserve state transitions, actors, times, and remarks/reasons.
- Return never overwrites a snapshot.
- Approval snapshots do not replace effective-dated Customer master history or general audit evidence. Downstream transaction-history requirements are governed by the relevant downstream module.
