# Sequence code review — 003/02_restart_and_abandon

## Scope and reviewers

- Delegated reviewer: Cursor `claude-sonnet-5-thinking-high`, read-only plan
  mode (`cursor-agent -p --mode plan`), bounded to this worktree's uncommitted
  `git diff`, the two new test modules and `docs/cli-contract.md`. Higher
  reasoning was used because the sequence is persistence, lock-order and race
  code, as the gate requires. It ran the focused modules (41 tests OK) and the
  full suite (405 OK, 1 skipped) itself and traced the commit/roll-forward/
  replay path, lock discipline and journal invariants. Transcript kept in the
  session scratchpad.
- Coordinator review: independent re-read of the lifecycle diff (lock nesting
  in `resume`, expiry-before-terminal ordering, replay of abandoned records,
  request fingerprint stability). The coordinator wrote the code, so the
  delegated review is the independent check.

A reviewer verdict is not runtime verification; evidence is in results/testing.md.

## Findings and dispositions

**Blocking:** none reported by either reviewer. The reviewer could not construct
a reachable sequence producing two replacements for one operation UUID,
changing old source bytes or the original timer, or giving a v1 record a
fabricated pinned identity outside `abandoned_record`.

**F1 — non-blocking (reviewer). `LockUnavailableError` not classified in
roll-forward.** `_roll_forward_locked` mapped `OSError`/`SessionUnavailableError`
to `recovery_pending` but a busy old-attempt lock during recovery would surface
as a generic busy (exit 4). Not currently reachable, since every caller
recovers under the workspace lock before taking any attempt lock. ACCEPTED as a
defensive fix in 05_iterate: the commit is durable, so "recovery pending" is
the honest answer.

**F2 — non-blocking (reviewer). No browser routes for abandon/restart yet.**
Correct and by design: this task owns shared services and CLI; 003/03/02 owns
the HTTP handlers (recorded as a follow-up in results/shared_lifecycle_actions.md).
The doc sentence "identical for CLI and browser" refers to the live-selection
policy, which is wired into both transports. NO CHANGE; noted for 003/03/02.

**F3 — non-blocking (reviewer). Submit-vs-restart contention was only proven
in-process.** The in-process test can be satisfied by the `_HELD_LOCKS` guard
rather than real `flock` contention. ACCEPTED in 05_iterate: a new test has
another process hold the attempt's `.session.lock` via `fcntl.flock` while
restart and abandon are attempted; both return the bounded busy error and
nothing is written.

**F4 — non-blocking (reviewer). Orphaned staging directories are never
garbage-collected.** A crash between staging and journal durability leaves a
dot-prefixed staging directory that the marker scan skips. Pre-existing for
plain create; the restart path adds a second window. NO CHANGE in this
sequence; recorded for 006 release verification as housekeeping, since a
leaked directory is inert and never selectable.

**F5 — nit (reviewer).** Submission-era naming in shared persistence helpers
and a missing comment explaining why `lifecycle.restart` releases its locks
before entering the workspace transaction. Comment ADDED in 05_iterate; the
helper names are left alone to keep the diff reviewable.

**F6 — accepted limitation (coordinator).** The request fingerprint includes
the pinned target content, as D001 requires. A retry after a failed response
that happens to straddle a content upgrade gets `operation_conflict` rather
than a replay. Safe (no second replacement; the pending journal is still
rolled forward first) and rare; documented here rather than changed.

## Areas the reviewer checked and found clean

Lock ordering (no path acquires the workspace lock while holding an attempt
lock; nested attempt locks only occur under the workspace lock); non-blocking
locks resolving every race to a bounded error, confirmed by the real
two-process test; idempotent replay and conflict detection before and after
recovery; durability ordering through `_atomic_bytes` for journal, receipt,
session and pointer; fail-closed classification (`SessionCorruptError` is never
coerced into pending); old bytes and timer preserved and the replacement timer
pinned to `committed_at`; the v1→v2 upgrade confined to `abandoned_record` with
the model forbidding an unpinned non-abandoned record; read-only review never
running recovery; CLI codes, exits and docs matching the code exactly.
