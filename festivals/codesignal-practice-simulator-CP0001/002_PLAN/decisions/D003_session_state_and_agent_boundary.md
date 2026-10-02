# D003: Per-Attempt State, Persistence, and Lifecycle

**Status:** accepted<br>
**Date:** 2026-09-08

## Context

Current attempts have copied assessment files plus a one-time `attempt.json` at
`attempts/<timestamp>[_<name>]/attempt.json`; there is no root-level
an `attempt.json` directly at the project root.
The scorecard can calculate time and print JSON but does not persist test
results, track lifecycle changes, record resumes/submissions, or prevent
concurrent writers. The approved product needs reliable
`start`/`resume`/`status`/`time`/`task`/`test`/`submit` behavior that survives
an interrupted local command without using a shared service.

Markdown is useful to a person or terminal agent, but it is a poor authority:
it is easy to edit accidentally, loses typed validation, and cannot enforce
event ordering. Its rendering and the separate agent/coaching boundary are
therefore decided in D004.

## Options

### Option A: Continue with static metadata and derive current state from directory timestamps
- **Pros:** Few files and little implementation effort.
- **Cons:** Cannot represent legal lifecycle transitions, crashes, submission
  finality, results, or an auditable resume history; timestamps are ambiguous.

### Option B: One mutable session file plus append-only event log per isolated attempt
- **Pros:** Clear authority and history; validates machine data; supports
  atomic recovery; confines state mutation to the selected workspace.
- **Cons:** Requires schema/version design, atomic write discipline, and
  tests for interruption/concurrency behavior.

### Option C: A shared database or hosted session service
- **Pros:** Central multi-machine coordination.
- **Cons:** Unneeded infrastructure, authentication, privacy, and operational
  complexity outside the local-simulator scope.

## Decision

Choose Option B. Each attempt contains:

```text
attempts/<attempt-id>/
  simulation.py              # candidate-controlled solution
  level1.md ... level4.md    # copied from validated local cache
  test_simulation.py         # copied from validated local cache
  session.json               # authoritative validated lifecycle state
  events.jsonl               # append-only command/outcome audit trail
```

Attempt creation first requires the complete hash-validated ignored cache
populated by `scripts/fetch_fixture.py`. The cache is complete only if all
seven manifest fetch records exist and validate: the upstream `README.md`
cached as `vendor-readme.md` and the six
`practice_assessments/file_storage/` records cached under
`assessment/file_storage/`. Missing or invalid cache data returns an
actionable setup-required error and creates no attempt; attempts never read or
mutate a tracked upstream fixture.

`session.json` has a versioned, explicitly validated schema and is the
authority for one attempt. It contains immutable attempt and assessment
identity, mode/profile, effective duration, UTC start/deadline timestamps,
lifecycle state, a monotonically increasing revision, the latest per-level
score summary, and submission metadata. Its lifecycle is `active`,
`expired`, or `submitted`. Expiry is determined from the injected UTC clock;
the first command observing an expired active attempt persists the `expired`
transition. `status` and `time` may observe an overdue active attempt, atomically record
`expired`, and successfully render that final state. Only `active` attempts may
resume or test; expired/submitted resume and expired/submitted test return the
illegal-lifecycle result without mutation. `submit` may finalize active or
expired work: an overdue submit records expiry first, then exactly one final
result. Once submitted, every repeat submit returns the stored final result
without rerunning scoring or changing state/events.

Every command resolving an attempt takes its per-attempt advisory lock before
reading or changing state. A state transition validates the current revision
and legal transition, writes a complete temporary sibling, flushes it, and
atomically replaces `session.json`. It then appends a single JSON line to
`events.jsonl` containing a schema version, event ID, state revision, UTC
timestamp, safe command arguments, event type, and outcome. If interruption
occurs after the atomic state replacement but before the append, the next
locked command reconciles the missing revision with a recovery event; state
remains authoritative. Readers reject malformed state, reject invalid
non-final event lines, and ignore only a trailing incomplete JSONL line.

The workspace root maintains a small, validated active-attempt pointer. It
contains only the chosen attempt ID and pointer schema version, is updated
atomically under a workspace-root lock, and is never treated as session
authority. If it points to a missing, invalid, or finalized attempt, commands
require an explicit valid selector or fail with a repair-oriented error.

Workspace creation is one transaction. After cache validation, build every
attempt file in a unique sibling staging directory with a transaction-owned
`.creation-owner.json` marker containing the attempt ID and creation token;
flush required files, atomically publish the completed attempt, then atomically
update `active.json`. Under the workspace-root lock, startup reconciliation
deletes an attempt only when its valid ownership marker identifies that newly
published attempt and `active.json` does not select it. It removes the marker,
but not the attempt, when the pointer does select it. Therefore interruption
after publish and before pointer replacement removes only the newly owned
unpublished attempt and preserves the former pointer and all prior attempts.
If any directory, copy, write, flush, replace, or pointer operation fails,
remove only the new staging/published attempt and leave no active pointer
change, cache mutation, or effect on an existing attempt. Filesystem
operations are injected so deterministic tests cover every failure point.

## Consequences

- States such as active, submitted, expired, and invalid transition errors are
  explicit and testable; submission is final and idempotent.
- Full mode is exactly 90 minutes. Drill mode uses a documented 30-minute
  default, records the effective duration, and may accept an explicit
  override without being described as an authentic full assessment.
- Tests need fake-clock coverage, legal and illegal transitions, concurrent
  writer rejection, atomic-state recovery, trailing-JSONL recovery,
  active-pointer validation, idempotent submission behavior, atomic workspace
  rollback under injected filesystem failures, and reconciliation after
  publish-before-pointer interruption.
