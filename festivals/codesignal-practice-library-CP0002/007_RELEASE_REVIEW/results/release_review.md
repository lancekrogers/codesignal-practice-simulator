# Release review — independent assessment, findings, fixes and publication status

Recorded 2026-09-13. Reviewed tree: worktree
`projects/worktrees/codesignal-practice-simulator/cp0002-practice-library`,
branch `cp0002-practice-library`, commits `268c07c..7de41d3` (phases 003–006),
plus the fix commit recorded below.

## How the review was run

- Independent reviewer: Cursor `claude-sonnet-5-thinking-high`, read-only plan
  mode, briefed with R1–R11, D001–D005 and the six review criteria from
  PHASE_GOAL.md (brief and transcript in the session scratchpad
  `review-brief-007.md`, `review_007.txt`). It read the lifecycle,
  persistence, review/history, provider, catalog, route and webui modules,
  the bundled content and oracles, the packaging scripts and the docs, ran
  focused unit modules (75+ tests), and reproduced two findings live.
- Coordinator: independent confirmation of each finding against the code,
  fixes with regression tests, and a full rerun of every suite.

## Items in scope and coverage

| Item | Criteria applied | Reviewed |
|---|---|---|
| 003_ATTEMPT_LIFECYCLE (models, persistence, restart journal, abandon, history/review APIs) | 1 lifecycle/data-loss, 2 review integrity, 6 evidence | yes — `workspace.py`, `lifecycle.py`, `persistence.py`, `models.py`, `attempt_history.py`, `attempt_reviews.py`, `web/routes.py`; `tests/test_restart_journal.py`, `test_lifecycle_actions.py`, `test_attempt_reviews.py`, `test_history_review_routes.py` |
| 004_ASSESSMENT_LIBRARY (providers, catalog, original content, packaging) | 3 content correctness, 5 distribution | yes — `input_providers.py`, `catalog.py`, `assessments.py`, `resources/assessments/*`, `tests/oracles/*`, `scripts/check_content.py`, `scripts/run_packaged_browser.py` |
| 005_PRACTICE_EXPERIENCE (library, attempt controls, history, review screens) | 4 UX completeness, 6 evidence | yes — `webui/src/*`, `webui/tests/*` |
| 006_RELEASE_VERIFICATION (matrix, offline wheel, docs) | 5 distribution, 6 evidence | yes — `results/acceptance_matrix.md`, `results/offline_and_docs.md`, `README.md`, `docs/*` |

No item was skipped or deferred.

## Findings and dispositions

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | P1 | `attempt_reviews.py`: on a `session/v2` submission, deleting `review.json` and editing `session.json` made the review boundary fall back to the mutable session and label it a legacy record (`submitted_source_binding_unavailable`); reproduced live (edited score served as 4/4). | FIXED: `_assemble` now raises `SessionCorruptError` ("review record is missing for a submission that recorded one") whenever the state carries a `review_digest` and no review member exists; genuine pre-D002 records (no digest) keep the labelled legacy path. Test `tests/test_attempt_reviews.py::test_missing_review_member_for_a_recorded_submission_fails_closed` (deletes the member, flips the score, asserts fail-closed, path-free message, tree unchanged). `docs/cli-contract.md` states the rule. |
| 2 | P1 | Browser back/forward from a live attempt disposed the runtime immediately: pending debounced edits and in-flight saves were dropped with no warning, unlike the Leave dialog. | FIXED: `app.ts::showRoute` now calls `attempt_runtime.ts::settleAttemptBeforeLeaving` first: a dirty or saving buffer is flushed before the attempt is disposed; text that still cannot be saved keeps the attempt open, restores its address and announces it (the Leave dialog remains the explicit discard path); back/forward onto the attempt already open is a no-op. Test `webui/tests/acceptance_matrix.spec.mjs` "browser back with pending edits saves them first, and unsaved text keeps the attempt open" (typed text present in `simulation.py` after Back; with saves failing, Back keeps the attempt and the URL; after a successful save Back leaves). |
| 3 | P2 | `workspace.py` restart staging: only `OSError` during the journal write triggered rollback; a non-`OSError` failure would orphan the staging directory (unreachable today). | FIXED: the rollback path catches any exception; the durable-journal check still protects a written journal. Existing `tests/test_restart_journal.py` (24) pass. |
| 4 | P2 | CLI `review --attempt` on a corrupt `session.json` echoed persistence's message including the absolute workspace path (HTTP and history already path-free). | FIXED: `AttemptReviewService.get_review` rewraps corrupt/unavailable session errors as path-free messages naming only the UUID. Test `tests/test_attempt_reviews.py::test_corrupt_session_record_is_reported_without_a_path`. |
| 5 | P2 | `run_packaged_browser.py`: `SIMULATOR_DENY_EXTERNAL_NETWORK` is set for the two direct entry-point probes but only enforced by the installed fixture server used in the browser step. | DEFERRED with justification: those two probes import the package, print `--version`, bind loopback and fetch the served assets from it; no network-capable code is on those paths, and the browser step (199 journeys) runs under the enforced deny hook. Tracked for 006-style follow-up: enforce the audit hook in the probes too. |
| 6 | nit | `acceptance_matrix.spec.mjs` header read as if it were the R1–R11 matrix. | FIXED: header points at the festival matrix and lists the scenarios it adds. |
| 7 | nit | `docs/cli-contract.md` said a republished review must be "byte-identical"; the code accepts an equal record in a different byte layout. | FIXED: wording now matches `_published_review_matches` and states the new fail-closed rule from finding 1. |
| 8 | nit | `scripts/check_content.py` vendor-text scan is a narrow literal denylist. | LEFT: manual content review found no proprietary copying; the scan is one of three independent layers (archive allowlist and runtime manifest validation are the other two). |
| 9 | nit | No `beforeunload` guard for reload/tab close with unsaved edits. | LEFT with justification: browser-default behaviour rather than an app-controlled path; the existing reload journeys rely on the default; the in-app paths (Leave, back/forward) now all protect unsaved text. |

## Review criteria verdicts after incorporation

1. Lifecycle/data-loss — met. One replacement per operation UUID under real
   two-process races and injected crashes; old bytes unchanged; staging
   rollback now covers every failure class.
2. Review integrity — met after fix 1. Review GET never rescores or reselects;
   a missing review member on a recorded submission fails closed; legacy
   labels apply only to records that never recorded a review.
3. Content correctness — met. Originals deterministic and offline; no
   proprietary copying; oracles excluded by three independent layers.
4. UX completeness — met after fix 2. Keyboard, reload, back/forward and
   server-restart flows verified; back/forward no longer loses unsaved text.
5. Distribution — met. Wheel built and installed outside the checkout with
   network denied runs the originals; File Storage stays fetch-gated; the
   deny hook is enforced on the browser step (finding 5 tracked).
6. Evidence quality — met after fixes 1–2 and 6. Both coverage gaps the
   reviewer named now have regression tests; the matrix names its scope.

## Rerun evidence (final code)

Run sequentially on the tree containing every fix (before the fix commit,
same content):

    just check unit                                            461 tests OK (1 skipped)  [+2 review tests]
    just check browser (locked privacy reporters, source)      200 passed, 0 failed       [+1 back/forward journey]
    just check wheel (installed wheel, temp venv, no network)  200 passed, exit 0
    python3 -m unittest tests.test_attempt_reviews tests.test_restart_journal
        tests.test_history_review_routes tests.test_documentation   56 OK
    just build assets / assets-check                           rebuilt; verified
    git diff --check                                           clean; worktree clean after the commit

Reproduction of finding 1 before the fix (deleted `review.json`, flipped
outcomes): review served 4/4 with `submitted_source_binding_unavailable`.
After the fix: `SessionCorruptError: review record is missing for a submission
that recorded one: <uuid>`, tree unchanged, no path in the message.

## Publication status

- Fix commit: `b542d41` on `cp0002-practice-library`
  (`fest commit --no-root`).
- On 2026-09-13 the user explicitly authorized publication: `origin/main` was
  merged into the branch first (merge commit 9597579; only README/image/doc-test
  changes, documentation tests OK), the branch was pushed, and a ready PR was
  opened against `main`: https://github.com/lancekrogers/codesignal-practice-simulator/pull/7. Its description carries the
  requirement-to-evidence mapping. Merging remains the user's decision.
- D005 (shipping the two original exercises alongside File Storage) was
  decided on the user's delegation on 2026-09-12 and is recorded in
  `002_PLAN/decisions/D005_content_scope.md`.
- No merge, publication or user approval is claimed.
