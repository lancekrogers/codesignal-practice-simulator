# Routes and catalog UI

Implemented by the coordinator directly on 2026-09-12 in the linked
cp0002-practice-library worktree. Uncommitted pending 06_fest_commit.

## What changed

- `webui/src/router.ts` (new): the validated route model from D004 without a
  framework. `parseRoute` accepts exactly `/`, `/attempt/<uuid>`, `/history`,
  `/history/review/<uuid>` (lowercase canonical UUIDs) and returns `unknown`
  for anything else; `navigateTo` pushes or replaces the path, keeps only the
  non-secret fragment (attempt id, level, tab), and `installRouter` routes
  `popstate`. No source text and no token ever enter route state; the capability
  is still captured and removed by `captureCapability` before the first route.
- `webui/src/app.ts` (rewritten): `showRoute` dispatches by route; every
  screen loads metadata only (`GET /api/bootstrap`, the manifest once). The
  library posts `/api/attempts` only from the confirmed dialog and then moves
  to `/attempt/<id>` silently. The attempt route on a cold load (reload,
  back, forward, typed address) renders the continue screen from the bootstrap
  session (or `GET /api/time` for a non-selected UUID) and requests the source
  only after the explicit "Reconnect to active session" / "View final session"
  action. History and review are metadata-only shells with Back actions (the
  listings arrive in 02_history_and_review). Unknown routes and unknown UUIDs
  render an error screen with "Back to library"; a route generation counter
  drops late responses from an abandoned route.
- `webui/src/library_view.ts` (new): `renderLibrary` shows the History entry,
  the selected session summary with the existing resume label, exercise cards
  (readiness badge "Ready"/"Setup required", path-free setup message, content
  version and provider label, `Select <name>` toggle buttons with
  `aria-pressed`; the bootstrap primary is listed and selected first), the
  outline for the selected exercise, the rules region, and one start form whose
  confirmation dialog (unchanged labels, exercise named in the copy) is the only
  path that starts a timer. `renderAttemptEntry` is the attempt route's continue
  screen (`main.entry.attempt-entry[data-active-attempt-id]`).
- `webui/src/views.ts`: `renderEntry` removed (replaced by the library);
  `renderError` takes one or many recovery actions and a title, returns the
  focusable heading; `renderNotice` for the history/review shells.
- Screen headings get `tabindex=-1` and receive focus on every route change
  (library, continue screen, notices, errors); dialogs keep the existing trap.
- `attempt_state.ts` / `attempt_state_normalization.ts`: `AttemptStatus` gains
  `abandoned`; `Bootstrap.catalog` (`CatalogEntry`) is validated (exactly four
  levels, full and drill profiles, string/boolean readiness fields, primary
  present) with a single-entry fallback for a bootstrap without `catalog`.
- `attempt_dom.ts`, `attempt_results.ts`, `attempt_panes.ts`: labels and
  read-only copy for ended attempts ("Ended", "This attempt was ended...",
  "ended without submission"); the attempt header uses the attempt's stored
  assessment display name (`attemptDisplayName`) so an original track shows its
  own name.
- `attempt_runtime_actions.ts`: "Back to start" navigates to the library route
  instead of `window.location.reload()`; the dialog copy says "library".
- `web/routes.py`: `is_shell_path` serves `index.html` for `/`,
  `/index.html` and every query-less path under `/attempt` or `/history`; the
  path never selects a file. `web/server.py` applies the shell CSP to the same
  set. Everything else remains a flat asset name or 404.
- `webui/tests/network_guard.mjs`: the documented same-origin request list
  gains the documented browser routes (shell documents only).
- `docs/cli-contract.md`: "Browser routes (web shell)" section.
- `webui/src/styles/base.css`: library, cards, badges, summary, action groups.

## Deliberate decisions

- The attempt route's cold load is an explicit continue screen rather than an
  automatic reconnect: the task's negative case ("direct URL does not start
  timer without explicit user continue"), the metadata-only rule for
  navigation, and the established reload → reconnect journeys all point the
  same way. Resume from the library and start from the form are explicit
  actions, so they open the attempt directly.
- Server route matching is prefix-based (`/attempt/...`, `/history/...`) so a
  mistyped address reaches the client's "Page not found" recovery instead of a
  bare JSON 404; the served bytes never depend on the path.
- Start with a live selection still goes to the server and shows the existing
  423 message; the library does not pre-empt it, so the API stays the arbiter.

## Negative cases proven

Browser (`webui/tests/library_routes.spec.mjs`, 6 journeys):

- Catalog readiness for all three exercises; the primary is listed and
  selected first; selection changes the outline and dialog copy; cancel returns
  focus to Start; zero POST/PUT until "Confirm and start"; the POST carries the
  selected exercise and drill duration; the attempt header shows the selected
  exercise name; URL becomes `/attempt/<id>`.
- Back → library with the active session summary; forward → continue screen
  (focused heading, summary, no `/api/source` request); explicit reconnect
  performs exactly one source request; back again and resume from the library;
  no mutation requests anywhere.
- Direct `/attempt/<id>` address: continue screen, no source request, no
  mutation; after the explicit action the deadline and status are unchanged and
  the bootstrap still names the same attempt and deadline (timer untouched).
- Unknown UUID → "Attempt not found" (404 declared to the guard) → Back to
  library; `/attempt/not-an-attempt` → "Page not found" → Back to library;
  neither requests source nor mutates.
- History and review shells: focus on heading, back/forward, review shell
  carries the reviewed id without selecting it (library shows no active
  session afterwards); no source or mutation requests.
- Bootstrap failure (503 with a path in the message): error heading focused,
  safe copy, no path leak, reload recovers.

Server (`tests/test_web_server_static.py`,
`test_browser_routes_serve_the_shell_without_touching_assets`): app routes and
`/attempt/not-an-attempt`, `/history/`, `/attempt` serve the shell bytes with
the shell content type, `no-store` and the same CSP for GET and HEAD;
`/attempt/../app.js`, `/attempts`, `/histories`, `/review/x`, and any route with
a query remain 404 without the shell; nested asset-like names under the route
prefixes still serve only the shell.

Existing journeys: `navigation.spec.mjs` "restores the selected level and tab"
now expects the attempt path `/attempt/<id>` (the only changed assertion);
every other reload → reconnect journey is unchanged because the continue screen
keeps `.entry`, `data-active-attempt-id`, the resume labels and the status copy.

## Evidence

    just check frontend                                   metadata/lockfile/license OK
    just build assets                                     rebuilt (app-*.js, styles-*.css, manifest)
    just build assets-check                               13 assets, manifest hash verified
    python3 -m unittest tests.test_web_server_static      8 tests OK (new route test included)
    just check unit                                       454 tests OK (1 skipped)
    npx playwright test library_routes shell_contract
        editor shell_layout harness --reporter=list       59 passed
    just check browser (locked privacy reporters)         181 passed (175 existing + 6 new)
    git diff --check                                      clean

Two existing journeys needed updates and nothing else changed behavior:
`navigation.spec.mjs` (attempt path after reconnect) and `shell_layout.spec.mjs`
(keyboard order now starts at the focused library heading and the History
button; the focus-indicator assertion itself is unchanged). `entry_page.mjs`
additionally asserts the library heading.

No TypeScript type-checker is installed in the toolchain (esbuild only), so
type correctness was verified by the bundle build and the browser journeys.

## Carried forward

- History listing and review screens (02_history_and_review) replace the
  shells; the route model and Back actions are in place.
- End/Restart controls on the attempt screen (02_restart_ux) reuse the
  `abandoned` status labels added here.
