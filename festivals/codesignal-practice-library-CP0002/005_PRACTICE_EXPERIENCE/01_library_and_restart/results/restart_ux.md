# Restart UX

Implemented by the coordinator directly on 2026-09-12 in the linked
cp0002-practice-library worktree. Uncommitted pending 06_fest_commit.

## What changed

- `webui/src/attempt_lifecycle_actions.ts` (new): `endAttempt` and
  `restartAttempt`. Each opens a confirmation dialog with the D001/D004 copy
  (saved work kept, timer restarts only in the replacement, unsaved edits saved
  first or explicitly discarded), then runs under a new `lifecycle` operation
  lease so it cannot overlap a save, Run Tests, Submit or another lifecycle
  action. Before the request the editor buffer is flushed (`source.flush()`,
  which retries a failed save once); when the result is not `clean` a second
  dialog ("Unsaved edits could not be saved") requires the explicit "Discard
  unsaved edits and …" choice, and Cancel leaves the attempt untouched. The
  expected revision is read from a fresh `/api/time` snapshot (metadata only);
  an attempt that turned terminal meanwhile refreshes into the read-only view
  instead of posting. End posts `/api/attempts/{uuid}/abandon` and refreshes
  the runtime (the countdown snapshot carries the `abandoned` status into the
  terminal transition). Restart mints `crypto.randomUUID()` once per attempt
  (`AttemptRuntime.restartOperationId`), reuses it on every retry, and drops it
  only after `stale_revision`/`lifecycle_locked` (different arguments would be
  an operation conflict); on 201/200 it opens the replacement through the
  router's registered opener.
- `webui/src/api.ts`: `abandonAttempt`, `restartAttempt`; `describeApiError`
  actions `ending`/`restarting` with fixed safe messages for `stale_revision`
  (refresh), `operation_conflict` (retry same operation), `recovery_pending`
  (retry same operation, no second attempt), `lifecycle_locked` (refresh) and
  unreachable server (retry). Server text never reaches the DOM.
- `webui/src/attempt_panes.ts`: action bar takes a callbacks object and renders
  "Reset source", "End attempt", "Restart", "Submit" as mutation controls;
  header leave button is "Back to library". `attempt_dom.ts`,
  `attempt_controls.ts`, `attempt_shell.ts`, `attempt_types.ts`
  (`onEnd`/`onRestart`), `attempt_operation_lock.ts` (`lifecycle` kind),
  `attempt_runtime_types.ts`, `attempt_runtime_actions.ts` wired accordingly.
- `webui/src/router.ts`: `registerAttemptOpener`/`openAttempt`; `app.ts`
  registers `openChosenAttempt` (silent route change + reconnect), so the
  replacement opens directly rather than at the continue screen.
- `webui/tests/network_guard.mjs`: `/api/attempts/<uuid>/(abandon|restart)`
  are documented requests.
- `docs/cli-contract.md`: "Attempt actions in the browser and their CLI
  equivalents" (Reset source has no CLI command; End = `abandon
  --expected-revision`, Restart = `restart --expected-revision
  [--operation-id]`) and the failure-to-state mapping.
- Existing specs: "Back to start" → "Back to library" (label only).

## Deliberate decisions

- The revision is fetched immediately before each action instead of trusting
  the session captured at start; saves and resyncs cannot then produce a
  spurious stale conflict, and the fetch is metadata only.
- End attempt applies the same save-or-discard gate as Restart: D001's rule is
  about not losing unsaved text at any lifecycle transition, and the copy tells
  the user which case applies.
- The restart dialog does not offer a different format; the server reuses the
  old attempt's profile (D001 default). A different format is a new start from
  the library.

## Negative cases proven (`webui/tests/restart_end.spec.mjs`, 6 journeys)

- Restart: cancel changes nothing (no request, `session.json` identical);
  confirm posts one request with `{operation_id, expected_revision}` equal to
  the stored revision, returns 201 with a new UUID; the browser is on
  `/attempt/<new>` with an Active header and without the old text; on disk the
  old `simulation.py` bytes are identical, the old session is `abandoned` with
  reason `restarted`, `STATUS.md` says abandoned, the replacement is active
  with the same profile and a later start.
- Duplicate clicks / lost response: a synthetic `recovery_pending` 503 (with a
  path in the server text) leaves the attempt active, shows the safe retry
  message without the path, and while the request is in flight Restart, End
  attempt and Submit are disabled by the operation lock. The fixture server is
  then really stopped and relaunched; the retried Restart sends the same
  `operation_id` and `expected_revision`, returns 201, the receipt
  `attempts/.restart-completed/<operation>.json` exists, and exactly two
  restart POSTs were made in total.
- Unsaved text: with saves failing (503), Restart → flush retries the save →
  "Unsaved edits could not be saved" dialog; Cancel keeps the buffer, sends no
  POST, and the session stays active; the explicit discard restarts, and the
  old attempt's stored source has the saved marker but not the unsaved one.
- Submit in flight (held `/api/submit`): Restart, End attempt and Reset source
  are disabled; after submission every lifecycle control stays disabled.
  Reset source: same attempt ID, still Active, unchanged deadline, source back
  to the baseline (200 from `/api/source/reset`).
- End attempt: cancel changes nothing; confirm posts `{expected_revision}`
  once, 200 with `newly_abandoned: true`; the shell shows "Ended", the output
  pane says the attempt ended before submission, the source is read-only, every
  mutation control is disabled; on disk `abandoned` with reason `ended`,
  `score: null`, saved marker present; the active pointer still names it.
- Stale revision (synthetic 409 with a path): safe message, view refreshed,
  still the same attempt; the next Restart uses a different `operation_id` and
  succeeds.

## Evidence

    just check frontend                                   metadata/lockfile/license OK
    just build assets                                     rebuilt
    just build assets-check                               13 assets, manifest hash verified
    npx playwright test restart_end.spec.mjs --reporter=list   6 passed
    just check browser (locked privacy reporters)         187 passed (181 + 6 new)
    just check unit                                       454 tests OK (1 skipped)
    git diff --check                                      clean

One pre-existing race was fixed in `actions.spec.mjs` ("submitted reconnect
reloads authoritative source after a real process restart"): it checked the
"View final session" button with a one-shot `isVisible()` right after
navigation and failed twice under load; it now waits for the button, which the
library always renders for a terminal selected session. Verified with
`--repeat-each 3`.

The restart dialog and the CLI parity table live in `docs/cli-contract.md`
("Attempt actions in the browser and their CLI equivalents").

## Carried forward

- `WorkspaceManager.recover_restarts()` at server startup (006) — the browser
  retry path is proven with a real process restart here, so the pending
  journal is rolled forward by the retried request rather than at boot.
- History/review screens (02_history_and_review) surface abandoned attempts
  and their saved work with the status labels added in 01.
