# DDR-0001 — Cost Center Team Reporting Buckets

- **Status:** APPROVED
- **Date:** 2026-09-19
- **Area:** Company Configuration / Cost Center Reporting
- **Supersedes:** The Team-model portion of CHG-2026-09-17-016 where the actual Company Team itself was the reporting/cost-center bucket.

## Context

The previous design combined operational Team identity, user membership, and Team-based reporting in `cost_center_teams`. The approved product behavior needs one reporting bucket to group several actual Company Teams without merging those Teams or their membership histories.

## Decision

- `cost_center_teams` is a Company-owned cost-center reporting bucket. It is not the actual operational Team master.
- `teams` stores actual Company-owned operational Teams.
- One Company has many Cost Center Team buckets and many actual Teams.
- One Cost Center Team may group many actual Teams.
- One actual Team may belong to zero or one Cost Center Team through nullable `teams.cost_center_team_id`.
- The bucket and assigned Team must belong to the same Company.
- `team_memberships` links users/IAM subjects to actual Teams through `team_id` and preserves effective-dated membership history.
- Users do not belong directly to Cost Center Team reporting buckets.
- No Team-to-Cost-Center-Team M:N mapping table is introduced.
- Actual Teams may remain unassigned. Mandatory complete reporting coverage is not approved.

Conceptually:

```text
Company
├── Cost Center Team: Regulatory Operations
│   ├── Actual Team: BIS Team
│   │   └── Team Memberships → users/IAM subjects
│   ├── Actual Team: AEO Team
│   │   └── Team Memberships → users/IAM subjects
│   └── Actual Team: FEMA Team
│       └── Team Memberships → users/IAM subjects
└── Actual Team: Unassigned Team
```

## Consequences

- Reporting-bucket identity, operational Team identity, and user membership become separate concepts.
- Downstream `team_id` references identify actual `teams`, not `cost_center_teams`.
- Moving an actual Team between reporting buckets changes its nullable bucket assignment without replacing the Team or its membership history.
- Business Segment and Location Cost Center relationships do not change.
- Generic `cost_centers`, `cost_center_types`, polymorphic mappings, and generic dimension/value engines remain excluded.

## Rejected Current-Scope Alternatives

- Keeping the actual Team as the reporting bucket cannot group multiple operational Teams under one reporting identity.
- An M:N Team-to-bucket mapping table contradicts the approved zero-or-one bucket per actual Team cardinality.
- Attaching users directly to reporting buckets loses the separate operational Team identity and membership history.

## Open Items

- Exact physical IAM subject column, datatype, and reference mechanism.
- Exact database enforcement for one active actual-Team membership per user within applicable Company scope.
- Whether a future Company activation/readiness policy requires complete Team-bucket coverage.

No source code, model, migration, API, or test implementation is authorized by this decision record.
