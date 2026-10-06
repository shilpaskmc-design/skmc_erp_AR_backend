# Company Configuration Open Decisions

## Status and use

This file contains only genuinely unresolved Company Configuration `OPEN` and `REVIEW` decisions. These items must not be inferred from UI, API, schema, or implementation convenience.

Routine physical database implementation work (e.g. exact SQL data types, index syntax, FK constraints, migration mechanics, ORM mappings) does not belong in this register as a business open decision.

## 1. Controlled Tax Reference Maintenance & Foreign Jurisdiction Generalization

**Status: `REVIEW` / `DEFERRED`**

- Platform reference-data maintenance authority for tax families, statutory codes, and default rates.
- Generalizing `company_hsn_sac_codes` to foreign item-tax classification schemes remains `DEFERRED` until foreign-seller requirements are approved.

## 2. FX Policy Values & Conversion Selection Rules

**Status: `OPEN`**

- Exact corporate/spot rate publication frequency, spot quote source, tolerance threshold, and FX policy values for multi-currency receipt knock-off.

## 3. Team IAM Membership Enforcement

**Status: `REVIEW`**

- Mechanics of enforcing IAM user subject identity against `team_memberships` for transaction authorization and reporting filters.

## 4. Document Numbering Condition Semantics

**Status: `OPEN`**

- Exact first-release condition-type vocabulary, operator vocabulary, multi-condition combination (AND/OR), priority semantics, and conflict resolution rules for `document_sequence_conditions`.

## 5. Document Output Template Selection & Stamp Visibility

**Status: `OPEN`**

- Detailed current-template selection rules when multiple templates match, and whether Stamp visibility is an independent `show_stamp` choice or strictly governed by the selected server-side template.

## 6. Stored-File Retention & Metadata Policy

**Status: `OPEN`**

- Stored-file retention policy, orphan-cleanup rules, legal-hold policy, and canonical hash algorithm for `stored_files`.

## 7. Customer Code Prefix & Overflow Validation

**Status: `REVIEW`**

- Allowed prefix validation rules, padding overflow behavior (e.g., sequence exceeding configured digit length), and whether Customer Code setup blocks Company activation or only `NEW_CUSTOMER` approval.

## 8. Service Catalogue Platform Suggestions vs Company Adoption Boundary

**Status: `BOUNDARY TBD`**

- Exact boundary between platform suggested Service Categories/Types, Company adoption, and Company-custom service ownership.

## 9. Incomplete Draft Cost Center Settings

**Status: `OPEN`**

- Whether an incomplete draft Cost Center configuration saved without a selected basis is permitted in draft state before activation.

## 10. Company Profile & GST Registration Versioning

**Status: `REVIEW`**

- Whether `company_profile_versions` and `company_gst_registration_versions` tables are required as full version tables beyond the current projection and legal name versions.

## Explicitly not open here

- Tenant vs Organisation vs Company ownership structure is `CONFIRMED`.
- Single Registered Office requirement is `CONFIRMED`.
- Financial Year pattern and non-overlapping period rules are `CONFIRMED`.
- Base GST Nature (`TAXABLE`, `NIL_RATED`, `EXEMPT`, `NON_GST`) is `CONFIRMED`.
- Customer Code generation direction (prefix + sequence starting at 1) is `CONFIRMED`.
- LUT requirement for `EXPWOP` / `SEZWOP` only is `CONFIRMED`.
- Three cost-center bases (Business Segment, Team, Location) are `CONFIRMED`.
