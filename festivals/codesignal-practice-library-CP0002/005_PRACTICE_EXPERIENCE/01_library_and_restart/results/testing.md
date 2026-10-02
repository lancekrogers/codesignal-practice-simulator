# Sequence testing gate — 005/01_library_and_restart

Covers 01_routes_and_catalog_ui and 02_restart_ux. Per-task evidence, the
negative cases and the deliberate decisions are in the sibling results files.

## Commands run and results (final code, 2026-09-12)

    just check frontend                                        passed
    just build assets                                          rebuilt bundle (esbuild)
    just build assets-check                                    13 assets, manifest hash verified
    python3 -m unittest tests.test_web_server_static           8 tests, OK (route shell test new)
    just check unit                                            454 tests, OK (1 skipped)
    npx playwright test library_routes.spec.mjs --reporter=list     6 passed
    npx playwright test restart_end.spec.mjs --reporter=list        6 passed
    just check browser (locked privacy reporters)              187 passed, 0 failed
    python3 scripts/verify_manifest.py ... --scope tracked     see below
    python3 scripts/verify_manifest.py ... --scope git-boundary see below
    python3 -m unittest tests.test_documentation               OK
    git diff --check                                           clean

The full browser suite is the integration proof for this sequence: the entry
page became a routed library, the attempt shell gained three lifecycle
controls, and every previously accepted journey (175) still passes alongside
the 12 new ones.

## Acceptance criteria demonstrated

- **Validated route model, reload/back/forward** (`library_routes.spec.mjs`):
  `/`, `/attempt/<uuid>`, `/history`, `/history/review/<uuid>` reconstruct
  their screens; unknown addresses and unknown UUIDs recover to the library;
  focus lands on each screen heading; the server serves the shell for the
  route prefixes with the shell CSP and never resolves a nested path to an
  asset (`test_web_server_static`).
- **No accidental timer start**: zero POST/PUT on library load, on selection,
  on opening or cancelling the dialog, on a direct attempt address, on back and
  forward, and on history/review shells; the only POST is the confirmed start,
  and it names the selected exercise. A direct address leaves the bootstrap's
  session and deadline unchanged.
- **Metadata-only navigation**: no `/api/source` request until the explicit
  reconnect action; catalog readiness rendered from bootstrap with no path,
  hash or cache text in the DOM.
- **End / Restart / Reset distinct and confirmed** (`restart_end.spec.mjs`):
  three labelled controls, three dialogs, all disabled during a held submit and
  after any terminal state; Reset keeps ID, status and deadline.
- **Saved work preserved**: old `simulation.py` bytes identical after restart;
  old session `abandoned` with the right reason; replacement active with the
  same profile; End records `abandoned` without a score and leaves the source
  readable.
- **Unsaved buffer gated**: failing saves lead to the explicit discard dialog;
  Cancel keeps the buffer and sends no POST; discard restarts and the stored
  source contains only the saved marker.
- **Operation locks and idempotency**: duplicate clicks impossible while a
  request is in flight; a synthetic `recovery_pending` followed by a real
  fixture process restart retries with the same operation ID and yields one
  replacement plus its completion receipt; `stale_revision` refreshes and
  mints a new operation ID.

## Failure boundaries exercised

- Bootstrap 503 with a path in the message → safe error, heading focused,
  reload recovers.
- `/api/time` 404 for an unknown UUID → "Attempt not found"; malformed UUID →
  "Page not found"; both return to the library.
- Restart 503 `recovery_pending` and 409 `stale_revision` with paths in the
  server text → fixed safe copy, no path in the DOM, attempt still active.
- Save 503 during restart → discard gate; reset/restore unchanged.
- Fixture server stopped and relaunched between a failed restart and its retry.

## Test changes to existing journeys

- `navigation.spec.mjs`: reconnect now lands on `/attempt/<id>` (one
  assertion); "Back to start" → "Back to library" (label only).
- `shell_layout.spec.mjs`: keyboard order starts at the focused library
  heading and the History button; focus-indicator assertions unchanged.
- `actions.spec.mjs`: a one-shot `isVisible()` race replaced by waiting for the
  "View final session" button (failed twice under load, passes 3/3 after).
- `pages/entry_page.mjs`: also asserts the library heading.
- `network_guard.mjs`: documented requests gain the browser route documents
  and `/api/attempts/<uuid>/(abandon|restart)`.

## Not run here, with reasons

- `just check wheel`: no interpreter with packaging prerequisites on this
  machine (unchanged from 004; owned by 006/01).
- `just verify` fixture-cache scope: no fetched cache; fetching third-party
  content over the network is not authorized.
- TypeScript type checking: no `tsc` in the locked toolchain; the esbuild
  bundle and the browser journeys are the verification.
