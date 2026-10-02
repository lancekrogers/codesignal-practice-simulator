---
fest_type: task
fest_id: 01_restart_journal.md
fest_name: restart_journal
fest_parent: 02_restart_and_abandon
fest_order: 1
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-11T14:32:19.009153-06:00
fest_updated: 2026-09-12T15:07:18.030375-06:00
fest_tracking: true
---


# Task: restart_journal

## Objective

Extend workspace and persistence with the D001 restart operation record, write-ahead commit intent, and recovery helpers that preserve old source/timer, roll forward after commit intent, and return the original replacement ID on duplicate identical requests.

## Requirements

- [ ] Read and apply **D001_attempt_lifecycle.md** (restart transaction, lock order, operation UUID, completion receipt immutability).
- [ ] Extend `src/codesignal_practice_simulator/workspace.py` near `:116` and `:145` for staging, pointer reconciliation, and journal discovery before workspace-selection mutations.
- [ ] Extend `src/codesignal_practice_simulator/persistence.py` with checksummed commit intent, completed operation identity, and recovery helpers.
- [ ] Validate content/profile before commit intent; preserve old source bytes and original timer; post-commit failures roll forward the same replacement—never delete prior work or mint a second replacement.
- [ ] Stage replacements through the verified v2 creation path from 003/01/02 (pinned identity, staged-byte hash check).
- [ ] session/v1 has no abandoned status, so abandoning or restarting a legacy v1 attempt upgrades only that record, inside this transaction, to session/v2 with an explicit legacy assessment identity (stored metadata, `content_identity: unavailable`). Extend the v2 model for that variant; never attach a PinnedAssessment or digest to it. Test both the upgrade and its recovery.
- [ ] Replay completed operations after replacement submission or later restart returns original replacement ID without changing current selection.
- [ ] Test every stage/rename/fsync boundary, mismatched replay payloads, unexpected revisions, and interrupted operation discovery.

## Implementation

1. **Operation record** — Persist caller-supplied operation UUID, expected old attempt ID/revision, target assessment/version/profile fingerprint; reject UUID reuse with different arguments.
2. **Lock order** — Acquire workspace lock → old-attempt lock → transaction-owned replacement staging; never acquire workspace lock while holding attempt lock (see D001 workspace.py:223 note).
3. **Commit intent** — Durably write prior/final states, event IDs, replacement identity, and expected pointer before publishing abandoned old state, replacement directory, and active pointer.
4. **Recovery** — On startup/explicit entry, reconcile pending journals first; verify allowed prior/target states; matching completed fingerprint returns original replacement without reselecting.
5. **Timer rule** — Replacement deadline starts at server timestamp committed with replacement; delayed recovery does not extend timer.
6. **Tests** — Add `tests/test_restart_journal.py` injecting failures before/after each journal/rename/pointer/flush boundary; assert old source bytes survive and exactly one replacement exists per operation UUID.

### Affected files

- `src/codesignal_practice_simulator/workspace.py`
- `src/codesignal_practice_simulator/persistence.py`
- `tests/test_restart_journal.py`

### Negative cases to prove

- Pre-commit failure leaves old attempt active and selectable.
- Post-commit failure rolls forward same replacement, not rollback over unrelated attempts.
- Changed operation UUID payload → conflict, not second replacement.
- Completed operation replay after replacement submitted → same ID, selection unchanged.

### Commands and evidence

```bash
python3 -m unittest tests.test_restart_journal -v
```

## Done When

- [ ] All requirements met
- [ ] Restart journal recovery is deterministic at every injected failure boundary
- [ ] Duplicate identical restart requests are idempotent with immutable completion receipt
