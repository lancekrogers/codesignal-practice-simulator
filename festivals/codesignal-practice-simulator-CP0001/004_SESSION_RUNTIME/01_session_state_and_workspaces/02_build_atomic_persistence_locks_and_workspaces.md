---
fest_type: task
fest_id: 02_build_atomic_persistence_locks_and_workspaces.md
fest_name: build_atomic_persistence_locks_and_workspaces
fest_parent: 01_session_state_and_workspaces
fest_order: 2
fest_status: completed
fest_autonomy: medium
fest_created: 2026-09-08T16:23:47.572382-06:00
fest_updated: 2026-09-08T19:38:11.927068-06:00
fest_tracking: true
---


# Task: 004.01.02 — Build Atomic Persistence, Locks, and Workspaces

## Objective

Create isolated attempts and recoverable state using only validated local cache
inputs.

## File anchors

Existing anchors: `scripts/fetch_fixture.py`, the validated ignored cache,
and 004.01.01 models. Create persistence/workspace modules and tests. Runtime
anchors include the ignored cache and
`attempts/<attempt-id>/{simulation.py,level1.md,level2.md,level3.md,level4.md,test_simulation.py,COACHING.md,AGENTS.md,session.json,events.jsonl,STATUS.md}`.

## Ordered implementation steps

1. Before creating an attempt, require the complete seven-record
   hash-validated cache. Copy exactly its six
   `assessment/file_storage/` inputs into a newly generated
   `attempts/<attempt-id>/`; never copy cache `vendor-readme.md`. Create
   candidate coaching/instruction and CLI-owned state/render files.
2. Use flushed temporary siblings plus `os.replace` for `session.json` and `active.json`; lock per attempt and workspace root for mutation.
3. Strictly parse JSONL: reject malformed non-final lines, ignore exactly one incomplete trailing line, and append a recovery event under lock if state revision lacks an event.
4. Maintain only validated versioned `attempts/active.json`; selector
   precedence is explicit `--attempt`, never newest directory. Build all
   workspace data in a unique sibling staging directory with a
   transaction-owned `.creation-owner.json` marker containing the attempt ID
   and creation token, flush it, atomically publish it, then atomically update
   the pointer. Under the workspace-root lock, startup reconciliation deletes
   an attempt only when its valid ownership marker identifies that newly owned
   attempt and `active.json` does not select it; it removes a marker from a
   pointer-selected attempt without deleting the attempt.
5. Inject filesystem operations and test every directory-creation, copy,
   write, flush, and replace failure. Each must roll back only the new
   staged/published attempt and leave no partial workspace, changed pointer,
   cache mutation, or effect on existing attempts.
6. Inject an interruption immediately after publish and before active-pointer
   replacement, then invoke reconciliation. Assert it deletes only the
   marker-owned unpublished attempt while preserving the prior active pointer
   and all pre-existing attempts. Test this case, locks, pointer corruption,
   fixture-hash invariance, and isolation.

## Error paths

On an absent/invalid cache, return a clear setup-required error and create no
attempt. On duplicate attempt ID, inaccessible root, injected directory/copy/
write/flush/replace failure, lock contention, corrupt pointer/state, or
interrupted write, leave the active pointer, cache, and other attempts
unchanged and remove only transaction-local staging/published data. Never
delete a directory merely because it is not active; reconciliation may delete
only a valid marker-owned, unpublished transaction attempt.

## Do-not-mutate boundaries

Never write the cached vendor files, another attempt, candidate `simulation.py`
after start, educational/reference material, or unrelated campaign state.

## Verification and evidence

Run from the directory named in the commands. Save complete output and exit codes to `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/004_SESSION_RUNTIME/01_session_state_and_workspaces/results/02_build_atomic_persistence_locks_and_workspaces.md`; a nonzero exit is blocking unless stated below.

```sh
PROJECT="/workspace/campaign/projects/codesignal-practice-simulator"
EVIDENCE="/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/004_SESSION_RUNTIME/01_session_state_and_workspaces/results/02_build_atomic_persistence_locks_and_workspaces.md"
mkdir -p "$(dirname "$EVIDENCE")"
set -e
set -o pipefail
{
cd "$PROJECT"
python3 -m unittest tests.test_persistence tests.test_workspace -v
python3 -m unittest discover -s tests -p 'test_*persistence.py' -v
python3 -m unittest discover -s tests -p 'test_*workspace.py' -v
git diff --check
git status --short
} 2>&1 | tee "$EVIDENCE"
```

Expected result: the commands produce the stated success output and `/workspace/campaign/festivals/active/codesignal-practice-simulator-CP0001/004_SESSION_RUNTIME/01_session_state_and_workspaces/results/02_build_atomic_persistence_locks_and_workspaces.md` records it.

## Definition of done

- [ ] New attempts are isolated and Git-ignored.
- [ ] Validated-cache hashes are invariant.
- [ ] Atomic, recovery, lock, pointer, and injected filesystem-failure
  rollback tests pass.
- [ ] A publish-before-pointer interruption deterministically removes only its
  owned unpublished attempt and preserves the former pointer and attempts.
- [ ] No selection uses directory recency.
