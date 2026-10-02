---
fest_type: phase
fest_id: 005_PRACTICE_EXPERIENCE
fest_name: PRACTICE_EXPERIENCE
fest_parent: codesignal-practice-library-CP0002
fest_order: 5
fest_status: completed
fest_created: 2026-09-11T14:31:59.408298-06:00
fest_updated: 2026-09-12T23:35:51.147063-06:00
fest_phase_type: implementation
fest_tracking: true
---


# Phase Goal: 005_PRACTICE_EXPERIENCE

**Phase:** 005_PRACTICE_EXPERIENCE | **Status:** Pending | **Type:** Implementation

## Phase Objective

**Primary Goal:** Select, repeat, browse, and review practice through library navigation, restart UX, history screens, and read-only review.

**Context:** Consumes 003 history/review APIs and 004 catalog/content. Delivers R10 UX journeys and surfaces R3/R4/R5–R7 behaviors to users via bundled web UI and documented CLI parity per D004.

## Required Outcomes

Deliverables this phase must produce:

- [x] Library and attempt routes with capability-safe navigation, reload/back/forward, and no accidental timer start (R10). Delivered: `webui/src/router.ts` (`parseRoute` :17, `navigateTo` :82, `installRouter` :64, `openAttempt` :59), `webui/src/app.ts` (`showRoute` :84, `showLibrary` :137, `showAttemptRoute` :195, `reconnect` :260), `webui/src/library_view.ts` (`renderLibrary` :34, `renderAttemptEntry` :140), server shell routing `web/routes.py::is_shell_path` :413 with CSP in `web/server.py` :370. Commit c72c8ab. Proof: `webui/tests/library_routes.spec.mjs` (6 journeys), `tests/test_web_server_static.py::test_browser_routes_serve_the_shell_without_touching_assets`.
- [x] Distinct End/Restart/Reset controls with confirmations and operation-lock integration (R3/R4). Delivered: `webui/src/attempt_lifecycle_actions.ts` (`endAttempt` :38, `restartAttempt` :49, `performEnd` :69, `performRestart` :101, `flushForTransition` :172, `currentRevision` :200), action bar in `webui/src/attempt_panes.ts`, `lifecycle` lease kind in `attempt_operation_lock.ts`, API helpers and fixed error copy in `webui/src/api.ts`. Commit c72c8ab. Proof: `webui/tests/restart_end.spec.mjs` (6 journeys, on-disk bytes and a real fixture process restart).
- [x] Filterable paginated history and read-only review with Retry conflict handling (R5–R7/R10). Delivered: `webui/src/history_state.ts` (`readHistoryFragment` :79, `normalizeHistoryPage` :142), `history_view.ts` (`renderHistory` :69), `history_screen.ts` (`mountHistory` :29); `review_state.ts` (`normalizeReview` :50), `review_view.ts` (`retryPlan` :58, `renderReview` :94), `review_screen.ts` (`mountReview` :33); server `attempt_reviews.py::AttemptReview.practice_score` :122. Commit 3409bd2. Proof: `webui/tests/history_screen.spec.mjs` (5), `webui/tests/review_screen.spec.mjs` (5), `tests/test_attempt_reviews.py::test_ended_attempt_reports_its_last_practice_result_not_a_submission`.

## Quality Standards

Quality criteria for all work in all sequences:

- [x] **API fidelity:** UI calls the same application services as CLI; no browser-only lifecycle shortcuts. End/Restart post the 003 abandon/restart routes with the same revision and operation-ID contract the CLI uses (`docs/cli-contract.md` "Attempt actions in the browser and their CLI equivalents"); Retry uses the ordinary start route; nothing bypasses `RuntimeApplication`.
- [x] **Metadata boundary:** History listing never requests source; review loads source only on explicit review route. Proven by request tracking in `history_screen.spec.mjs` (only `/api/bootstrap` and `/api/attempts`) and `review_screen.spec.mjs` (review and, for never-submitted attempts, the explicit source read only); library/continue screens request no source until the explicit reconnect (`library_routes.spec.mjs`).
- [x] **Synthetic browser proof:** Locked Playwright privacy reporters; keyboard, reload, and server-restart scenarios exercised. `just check browser` 197 passed (175 existing + 22 new); keyboard order and focus asserted in library, history and review specs; reload/back/forward in `library_routes.spec.mjs`; real fixture process restart mid-operation in `restart_end.spec.mjs`.

## Sequence Alignment

| Sequence | Goal | Key Deliverable |
|----------|------|-----------------|
| 01_library_and_restart | Select and repeat safely | app.ts routes, restart/end UX |
| 02_history_and_review | Revisit results without disturbing practice | History and review screens |

## Pre-Phase Checklist

Before starting implementation:

- [x] Planning phase complete (002_PLAN; D001–D005 resolved)
- [x] Architecture/design decisions documented (D001, D002, D004 applied; deliberate decisions recorded per task)
- [x] Dependencies resolved (003 lifecycle/history/review APIs, 004 catalog and content)
- [x] Development environment ready (linked worktree, esbuild toolchain, Playwright Chromium)

## Phase Progress

### Sequence Completion

- [x] 01_library_and_restart — all six tasks/gates completed; commit c72c8ab; results in `01_library_and_restart/results/`
- [x] 02_history_and_review — all six tasks/gates completed; commit 3409bd2; results in `02_history_and_review/results/`

### Verification summary (final code, 2026-09-12)

    just check unit                 455 tests OK (1 skipped)
    just check browser              197 passed, 0 failed (locked privacy reporters)
    just check frontend             passed
    just build assets-check         manifest verified
    verify_manifest.py tracked / git-boundary   passed
    python3 -m unittest tests.test_documentation  OK
    git diff --check                clean; worktree clean at 3409bd2

Full inventory with symbols, line numbers, tests and review dispositions:
`results/phase_evidence.md`.

## Notes

Anchors: `webui/src/app.ts:51/:97`, `application.py:174/:245`, `web/routes.py:120/:177/:208`. Do not introduce an external frontend router framework. Outcome: no framework was introduced; `webui/src/router.ts` is 96 lines of first-party code.

---

*Implementation phases use numbered sequences. Create sequences with `fest create sequence`.*
