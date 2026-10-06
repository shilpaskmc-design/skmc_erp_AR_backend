# Customer Open Decisions

## Status and use

This file contains only unresolved Customer `OPEN` and `REVIEW` matters. These items must not be inferred from UI, API, schema, or implementation convenience.

The Customer persistence proposal remains `CURRENT WORKING DESIGN / PROPOSED FOR FREEZE`. Resolving a question here may require a later requirement, data-model, and changelog update.

## Customer change-control classification

**Status: `REVIEW`**

1. Will the Class A/B/C Customer-change control model be adopted?
2. If Class B is adopted, which fields or operations are:
   - `APPROVAL_REQUIRED`; or
   - `DIRECT_EDIT_ALLOWED` with authorization and audit?

No change-policy/configuration table is approved.

## Post-approval Contact changes

**Status: `REVIEW`**

Decide whether changes to Contact identity, Contact Details, roles, and purposes require a Customer approval request or may be performed as a direct authorized edit with audit evidence.

`ADD_CONTACT` is a Customer request type only if the approved policy requires Contact changes to follow approval.

## GST-to-Location mapping changes

**Status: `REVIEW`**

Decide whether adding or changing the applicable GST-registration context on a Customer Location version always requires Customer approval or can use another authorized/audited maintenance path.

## Customer reactivation

**Status: `OPEN`**

Decide whether an inactive Customer:

- returns to service through controlled amendment/re-onboarding on the same stable Customer and Customer Code; or
- remains terminal while a separately controlled replacement identity is created.

The decision must preserve Company-scoped PAN/GSTIN uniqueness and historical continuity. A duplicate Customer cannot be created merely to bypass the unresolved rule.

## Non-India statutory applicability

**Status: `REVIEW`**

Identify which legal/statutory identifiers and supporting evidence apply by supported jurisdiction and entity/legal type.

This decision does not require a large configurable worldwide rules engine. Confirmed India PAN/GST supporting-document requirements are not reopened.

## Explicitly not open here

- `UNDER_REVIEW` and `WITHDRAWN` are not current states.
- Withdraw-after-submit is not part of the workflow.
- `customer_identifier_claims` is not part of MVP.
- Credit Limit is `DEFERRED`, not an unresolved MVP design question.
- No request `payload_schema_version` is proposed at this stage.
- No field-level Return/review-findings table is required.
- Complex parallel amendments are outside MVP.
- The 14-table count and Request + JSONB Snapshots + Actions direction are not reopened by this file.
