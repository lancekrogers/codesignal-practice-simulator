---
fest_type: phase
fest_id: 006_RELEASE_VERIFICATION
fest_name: RELEASE_VERIFICATION
fest_parent: codesignal-practice-library-CP0002
fest_order: 6
fest_status: completed
fest_created: 2026-09-11T14:31:59.408298-06:00
fest_updated: 2026-09-13T00:33:21.560227-06:00
fest_phase_type: implementation
fest_tracking: true
---


# Phase Goal: 006_RELEASE_VERIFICATION

**Phase:** 006_RELEASE_VERIFICATION | **Status:** Pending | **Type:** Implementation

## Phase Objective

**Primary Goal:** Prove the complete user outcome and package evidence with synthetic acceptance flows and offline distribution checks.

**Context:** Final implementation phase before 007 independent review. Aggregates R1–R11 evidence using canonical Just recipes and locked browser harness—no second test runner. Depends on all prior phases complete.

## Required Outcomes

Deliverables this phase must produce:

- [x] Full acceptance matrix covering every accepted exercise and lifecycle outcome with recorded CLI/browser evidence (R1–R10). Delivered: `01_acceptance_and_distribution/results/acceptance_matrix.md` (35 rows, each with command/spec, environment, outcome). New executed evidence: `tests/test_end_to_end.py::test_original_exercise_console_lifecycle_restart_history_review_and_end` (console, packaged original, no fetch: start → test exit 5 → restart + replay → history → review → abandon → filtered two-page history → cursor mismatch) and `webui/tests/acceptance_matrix.spec.mjs` (stale second tab cannot restart; real `session/v1` record listed and reviewed without upgrade). Existing suites referenced by row: `tests/test_restart_journal.py` (24), `tests/test_lifecycle_actions.py` (18), `tests/test_attempt_history.py` (11), `tests/test_attempt_reviews.py` (16), `tests/test_original_content.py` (7), browser specs library_routes/restart_end/history_screen/review_screen (22). Commit 7de41d3.
- [x] Offline wheel install outside checkout, asset rebuild verification, and updated operating docs with negative-path examples (R11). Delivered: `just check wheel` exit 0 (`scripts/run_packaged_browser.py`; wheel 67, sdist 127, static 14 members; temp venv, `pip install --no-index --no-deps`; 199 browser journeys against the installed package with `SIMULATOR_DENY_EXTERNAL_NETWORK=1`; build_mode `pep517-hooks` via `scripts/packaging_support.py::discover_builder`); assets rebuilt twice with identical manifest hash; README (library table, End/Restart/Reset, history/review transcripts, record compatibility, offline install, troubleshooting), `docs/cli-contract.md`, `docs/agent-safety.md`. Two defects found and fixed by running the check on an installed wheel: `input_providers.py` `__pycache__` tolerance (`tests/test_input_providers.py::test_installed_bytecode_cache_is_tolerated_but_never_staged_or_widened`) and the builder fallback (`tests/test_packaging_support.py`, 3 new tests). Evidence: `01_acceptance_and_distribution/results/offline_and_docs.md`. Commit 7de41d3.

## Quality Standards

Quality criteria for all work in all sequences:

- [x] **No real candidate data:** Synthetic workspaces and privacy reporters only. Every browser run used the fixture server's synthetic cache and the locked reporters (`just check browser`, `just check wheel`); unit and end-to-end suites use temporary workspaces; no real attempt, cache or reference material was read.
- [x] **Canonical commands:** Use project Just recipes (`just verify`, `just check frontend`, `just build assets`, `just build assets-check`, `just check browser`, `just check wheel`) with documented prerequisites. All run except `just verify`'s fixture-cache manifest scope (cache absent; its unit/end-to-end/whitespace steps ran individually); prerequisites and the `just check wheel` fallback documented in README "Contributors".
- [x] **Honest gaps:** Unresolved limitations listed explicitly in results; no waiver of provenance checks. See "Unresolved rows and limitations" (acceptance_matrix.md) and "Known gaps" (offline_and_docs.md); `verify_manifest.py` tracked and git-boundary scopes passed, the fixture-cache scope is reported as not executed rather than waived.

## Sequence Alignment

| Sequence | Goal | Key Deliverable |
|----------|------|-----------------|
| 01_acceptance_and_distribution | Integrated evidence | Acceptance matrix, offline/docs results |

## Pre-Phase Checklist

Before starting implementation:

- [x] Planning phase complete (002_PLAN)
- [x] Architecture/design decisions documented (D001–D005)
- [x] Dependencies resolved (phases 003–005 completed with approved gates)
- [x] Development environment ready (linked worktree; python3.11 with setuptools/wheel/pip/venv for the packaged check)

## Phase Progress

### Sequence Completion

- [x] 01_acceptance_and_distribution — all six tasks/gates completed; commit 7de41d3; results in `01_acceptance_and_distribution/results/`

### Verification summary (final code, 2026-09-13)

    just check unit                 459 tests OK (1 skipped)
    just check browser              199 passed, 0 failed (locked privacy reporters)
    just check wheel                199 passed against the installed wheel, exit 0 (build_mode pep517-hooks)
    just check frontend             passed
    just build assets ×2 / assets-check   identical manifest hash; verified
    just check content              2 exercises × 7 files OK
    verify_manifest.py tracked / git-boundary   passed (fixture-cache: not executed, cache absent)
    python3 -m unittest tests.test_documentation  OK
    git diff --check                clean; worktree clean at 7de41d3

Full inventory: `results/phase_evidence.md`.

## Notes

Structural fest validation alone does not satisfy this phase. Each requirement row in IMPLEMENTATION_PLAN must map to executed evidence or an explicit unresolved entry.

---

*Implementation phases use numbered sequences. Create sequences with `fest create sequence`.*
