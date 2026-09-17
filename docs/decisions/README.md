# Decision Record Governance

This directory is reserved for standalone records that preserve the context, rationale, alternatives, trade-offs, and consequences of major finalized architecture or domain/design decisions.

## When a Standalone Decision Record Is Required

Create a standalone decision record when a decision:

- changes a finalized architecture rule;
- establishes a major cross-module ownership or dependency boundary;
- replaces a significant previously approved design;
- has substantial long-term technical or domain consequences; or
- needs rationale and trade-offs preserved beyond a short `CHANGELOG.md` entry.

Use an Architecture Decision Record when the primary consequence concerns platform structure, deployment, integration, security, infrastructure, or module dependency. Use a Domain/Design Decision Record when the primary consequence concerns a major business-domain model, cross-feature invariant, or durable data-design direction.

## When a Standalone Record Is Not Required

Do not create a separate ADR or DDR for:

- ordinary field additions;
- simple wording corrections;
- routine table-column changes;
- implementation-only refactoring that does not change architecture or product behavior; or
- a small, local change whose rationale is fully captured by its owning requirement and a short changelog entry.

## Decision Records and the General Change Log

`docs/CHANGELOG.md` records that a meaningful change occurred, its status, what it supersedes, affected documents, and implementation impact.

A standalone ADR or DDR explains why a consequential decision was selected, which alternatives were considered, the resulting constraints, and the long-term consequences. When a standalone record exists, the changelog entry should link to it rather than duplicate its full rationale.

Changing a finalized decision requires a new record. Do not rewrite the earlier record to make it appear that the old decision never existed. Mark the earlier record superseded and link both directions.

## Filename Convention

- `ADR-XXXX-short-title.md` for architecture decisions
- `DDR-XXXX-short-title.md` for major domain/design decisions

Use a zero-padded sequence such as `ADR-0001` or `DDR-0001`. Keep the title short, stable, lowercase, and hyphen-separated.

No ADR or DDR is created as part of the initial documentation-governance setup.
