---
fest_type: task
fest_id: 04_verify_document_safety_and_recovery.md
fest_name: verify document safety and recovery
fest_parent: 02_candidate_documents
fest_order: 4
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-09T03:13:28.091222-06:00
fest_updated: 2026-09-09T04:58:08.209699-06:00
fest_tracking: true
---


# Task: verify document safety and recovery

## Objective

Stress the candidate-document service at concurrency and crash boundaries before exposing it through HTTP.

## Requirements

- [ ] Use injectable `Filesystem` failure doubles modeled on `tests/test_persistence.py` to test failures before snapshot publish, after snapshot flush, during source replacement, and during pruning.
- [ ] Prove lock ordering, stale-write behavior, legacy baseline recovery, symlink rejection, content limits, strict UTF-8, expiry/submission read-only guards, and neighboring-attempt isolation.
- [ ] Verify successful source replacement always recovers the predecessor and that orphan duplicate snapshots do not change the current source.

## Implementation

Follow these steps in order:

1. Extend `tests/test_candidate_documents.py` with failure-injection filesystems and a barrier/thread case where two saves use the same old ETag; assert exactly one wins and the loser sees conflict.
2. Corrupt each metadata/snapshot boundary deliberately and assert a safe domain error with no raw path/trace leakage; repair only through the documented legacy initialization path.
3. Create two synthetic attempts under one temporary workspace and alternate explicit attempt IDs; confirm source/history never cross boundaries and lifecycle `revision`/`events.jsonl` remain unchanged by source operations.
4. Run `python3 -m unittest tests.test_candidate_documents tests.test_persistence tests.test_workspace tests.test_lifecycle -v` and then the full suite.

### Safety and content isolation

Test fixtures must be synthetic and temporary. Add assertions that no error or returned history contains FETCH_ONLY/vendor/reference bytes, `.cache` paths, solution/study names, or scorer internals.

### Focused verification commands

Run the commands named in the ordered steps from the project root or the explicitly named `webui/` directory. Use temporary workspaces and synthetic fixtures; retain only aggregate results or failure-only diagnostics.

## Done When

- [ ] Every specified interruption and concurrent-save case has a deterministic test result.
- [ ] Source correctness and predecessor recoverability hold after injected failures or orphan snapshots.
- [ ] The focused and full Python suites pass with no changes to existing persistence semantics.
