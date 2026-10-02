---
fest_type: task
fest_id: 02_shared_lifecycle_actions.md
fest_name: shared_lifecycle_actions
fest_parent: 02_restart_and_abandon
fest_order: 2
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-11T14:32:19.009153-06:00
fest_updated: 2026-09-12T15:27:27.075838-06:00
fest_tracking: true
---


# Task: shared_lifecycle_actions

## Objective

Expose explicit abandonment and restart through shared lifecycle/application services with common CLI/browser live-selection policy, safe stale/busy errors, and source reset kept distinct—no implicit deletion or submission.

## Requirements

- [ ] Read and apply **D001_attempt_lifecycle.md** (state contract, source reset vs restart, live-selection policy) and **D004_history_api_and_ux.md** (POST abandon/restart API shape).
- [ ] Extend `src/codesignal_practice_simulator/lifecycle.py` near `:82` and `:132` with abandon/restart orchestration calling restart journal from task 01.
- [ ] Extend `src/codesignal_practice_simulator/application.py` with shared service entrypoints used by CLI and web layers.
- [ ] Add CLI parser/serialization for abandon/restart with operation UUID and expected revision. This task owns shared services and CLI; 003/03/02 owns HTTP handlers and transport validation.
- [ ] Upgrade a legacy v1 record only inside an explicit recoverable lifecycle
  transaction. Preserve original identity/timestamps/source and label unknown
  content binding honestly; unknown or incompatible definitions block mutation,
  not read-only history. Add v1 abandon/restart and interrupted-upgrade tests.
- [ ] Keep source reset separate; plain start must not silently replace a selected live attempt in CLI or browser.
- [ ] Test terminal retries, stale tabs, two processes, restart versus submit serialization, retry after failed response, and unchanged legacy non-selected attempts.

## Implementation

1. **Service methods** — `abandon_attempt(...)`, `restart_attempt(operation_uuid, expected_revision, ...)` returning replacement identity or conflict/recovery-pending responses per D004.
2. **Selection policy** — Resolve implicit selection once under workspace lock; require explicit conflict resolution when selecting a different live attempt.
3. **CLI** — Add commands/flags mirroring web payloads; serialize errors with existing envelope conventions.
4. **Transport contract** — Provide shared validation/error semantics for HTTP integration in 003/03/02; do not duplicate those handlers here.
5. **Concurrency** — Serialize submit vs restart on old-attempt lock; duplicate clicks across tabs cannot create two replacements.
6. **Tests** — Extend lifecycle/application/CLI tests for stale revision, cross-process lock contention, terminal-state retries, and legacy non-selected attempt preservation.

### Affected files

- `src/codesignal_practice_simulator/lifecycle.py`
- `src/codesignal_practice_simulator/application.py`
- HTTP handlers are deferred to 003/03/02; application services remain shared.
- CLI module(s) hosting attempt commands
- `tests/test_lifecycle_actions.py` (or equivalent)

### Negative cases to prove

- Restart during scoring → bounded lock failure or wait, not workspace-wide deadlock.
- Abandon/restart on terminal attempt → safe error, no rescoring or deletion.
- Stale revision POST → conflict with actionable message.
- Source reset does not change attempt ID or deadline.

### Commands and evidence

```bash
python3 -m unittest tests.test_lifecycle_actions -v
just check unit
```

## Done When

- [ ] All requirements met
- [ ] CLI and web share identical lifecycle semantics with explicit error contracts
- [ ] Concurrency and terminal-state tests pass with recorded evidence
