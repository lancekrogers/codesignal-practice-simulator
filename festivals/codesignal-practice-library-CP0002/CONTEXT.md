# CP0002 working context

## Scope and status

The user requested a festival for repeatable practice, multiple assessments,
history, and submission review. This replaces the proposed design work item.
Simulator schema foundation changes are isolated in the implementation worktree.
No real attempt data has been read or changed.
The configured local judge approved ingest PRESENT after sandbox restrictions
were removed. All intake phase gates subsequently passed. Planning review, gap
analysis, decomposition, design, and plan presentation are complete. The local
judge accepted PLAN PRESENT with the content-selection prerequisite retained.
Scaffold and bounded Cursor review are complete: 17 implementation tasks, 32
sequence gates, validation 100/100 and zero markers. All planning phase gates
passed. Promoted to active without auto-commit. Cursor Composer 2.5 implemented
003/01/01; coordinator corrected bounded reads and review timer validation.
Task marked complete; latest focused tests: 106 passed. Broader unit run before
the last size-limit write guard: 319 tests OK, one optional-build skip. Frontend
metadata/licensing passed after locked dependency installation. All Cursor jobs
exited. 2026-09-11 session: coordinator repaired the identity ordering by
inserting 003/01/02_creation_identity (fest create task --after 1; later tasks
renumbered), amended D002/D003, updated 003/02/01 and 004/01/01; fest validate
100/100, then completed the whole 003/01 sequence: creation identity with v2
activation, immutable submission capture, and the read-only review service, plus
the testing, review, iterate and commit gates. Implementation was done by the
coordinator directly; the review gate was delegated to Cursor
claude-sonnet-5-thinking-high read-only, which found one blocking issue (the
review boundary trusted mutable session fields) now fixed and regression-tested.
Project commit 268c07c (--no-root, not pushed) holds the code; festival files
remain uncommitted at root pending a scoped root commit.

Two cursor-agent processes from earlier sessions (~2 days old) were still
running on this machine; they were left alone. The earlier "all Cursor jobs have
exited" note is inaccurate.

2026-09-12 session: coordinator implemented 003/02/01_restart_journal (D001
journal, roll-forward recovery, receipts, legacy-identity upgrade) and
003/02/02_shared_lifecycle_actions (abandon/restart services and CLI, abandonment
WAL, shared live-selection policy) directly; verification in
003/02/results/*.md. The D001 live-selection rule changed four existing tests
(documented in results/shared_lifecycle_actions.md). All 003/02 gates passed;
project commit 4751dd5 (--no-root, not pushed) holds the sequence. Root commit
4e61aab (fest auto root commit, festival-scoped, no gitlinks) holds the
festival files for 003/01 and 003/02.

003/03_attempt_history_api followed the same pattern (coordinator implementation,
Cursor read-only review, project commit 661a9cb --no-root). Phase 003 complete.

Phase 003's implementation gate passed all four judge steps after evidence was
written into festival files (the judge cannot see the worktree). 004/01
(providers + catalog) followed the same coordinator/Cursor pattern; commit
614aaf5 (--no-root).

004/02 delivered the two original exercises (commit 9676ed5). Phase 004 is
complete pending its gate judge.

Remaining: UI (005), release verification (006) and publication (007). D005's content choice is still the user's to make
before 004/02. just check wheel remains unrunnable here (no interpreter with
setuptools/pip/venv/wheel/build).

## Additional source audit for architecture planning

Anchors below are relative to projects/codesignal-practice-simulator, inspected
at baseline 7833def. They identify design work, not finished fixes.

- workspace.py:116 validates the whole fetched cache before creating any attempt;
  application.py:343 validates it again. Adding original offline exercises cannot
  merely add registry entries: it needs an assessment-specific input provider.
- workspace.py:145 owns staging/publication and pointer rollback under the
  workspace lock. A restart spans an old-attempt transition and a new-attempt
  publication; do not assume the existing create rollback covers both.
- workspace.py:310 validates old metadata against today's registry. Legacy
  history must not disappear when a catalog entry is missing or changes version.
- workspace.py:329 copies each definition's files from the single fixture cache.
  Keep pinned File Storage validation intact while adding packaged original inputs.
- lifecycle.py:315 writes ahead submission state/event, but its interface does
  not include a source digest/snapshot. PLAN must specify exact result/source
  binding and avoid representing a legacy source as independently verified.
- candidate_documents.py:52 and :69 call initial-baseline creation on reads.
  Reusing those methods for a promised non-mutating legacy review needs scrutiny.
- candidate_documents.py:99 resets source to the baseline in the same attempt;
  this is distinct from restarting practice with a fresh clock/identity.

## Working tree / authority

The original checkout is now clean on docs-invite-readme at 33883ed, with a local
screenshot/documentation commit not in origin/main. Do not change that checkout.
Created dedicated branch/worktree cp0002-practice-library from origin/main
7f9e376 at projects/worktrees/codesignal-practice-simulator/cp0002-practice-library
using camp project worktree add. Festival link points to this worktree.

fest commit currently stages all changes in a linked project as well as festival
state and its pointer. Do not invoke it against the dirty audit checkout. Planning
artifacts currently remain local; preserve them until a safely scoped commit is
arranged. No blanket campaign staging or gitlink synchronization is authorized.
For project implementation commits use fest commit --no-root after inspecting
scope; the original checkout's gitlink must not be synced by accident.

## Delegation and verification

User explicitly requested Cursor sub-agents to control usage. Two read-only
Composer 2.5 source audits and one focused Sonnet 4.6 medium-thinking design
review informed D001-D004; findings and dispositions are in 002_PLAN/results.
Composer 2.5 completed scaffold/review and owns the first model implementation.
Do not claim measured billing savings.
Baseline synthetic checks in the new worktree:
python3 -m unittest tests.test_models tests.test_persistence -q — 35 passed.
The repository uses unittest and modular just checks, not pytest.

## Product choice (resolved)

On 2026-09-12 the user delegated the open decisions to the coordinator. D005 is
decided: File Storage plus the two original Python tracks (In-Memory Records,
Account Ledger). Rationale is recorded in the D005 resolution. The user also
asked that execution continue without pausing at sequence boundaries; only
irreversible or outward-facing actions (push, publish) still need per-action
authorization.
