# Decisions Index

Registry of architecture decisions made during planning.

| ID | Decision | Status | Date |
|----|----------|--------|------|
| D001 | Shared application container and standard-library HTTP adapter | accepted | 2026-09-09 |
| D002 | Candidate document optimistic concurrency and recoverable history | accepted | 2026-09-09 |
| D003 | Locally bundled Monaco Editor | accepted | 2026-09-09 |
| D004 | Loopback capability and narrow JSON API | accepted | 2026-09-09 |
| D005 | Server-authoritative browser state machine and layered verification | accepted | 2026-09-09 |

## Status Values

- `proposed` — Under consideration
- `accepted` — Approved and final
- `superseded` — Replaced by a later decision

## Decision Template

Create `D###_title.md` files for each significant decision:

```markdown
# D001: [Decision Title]

**Status:** proposed | accepted | superseded
**Date:** YYYY-MM-DD

## Context

[Why is this decision needed?]

## Options

### Option A: [Name]
- **Pros:** [Benefits]
- **Cons:** [Drawbacks]

### Option B: [Name]
- **Pros:** [Benefits]
- **Cons:** [Drawbacks]

## Decision

[Which option was chosen and why]

## Consequences

[What changes or follow-up work results from this decision]
```

Accepted decisions may be revisited only if implementation evidence disproves
an assumption; any replacement must be recorded as a superseding decision.
