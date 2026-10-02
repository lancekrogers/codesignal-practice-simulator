# Sequence code review — 005/01_library_and_restart

## Scope and reviewers

- Delegated reviewer: Cursor `claude-sonnet-5-thinking-high`, read-only plan
  mode, bounded to the uncommitted diff plus the five new files
  (`router.ts`, `library_view.ts`, `attempt_lifecycle_actions.ts`,
  `library_routes.spec.mjs`, `restart_end.spec.mjs`), generated bundle
  excluded. It ran `tests.test_web_server_static` (8 OK) and traced every
  route-load, resume, restart and end path against the stated invariants.
  Transcript: session scratchpad `review_005_01.txt`.
- Coordinator review: independent pass over `app.ts` generation handling,
  the lifecycle lease/finish paths and the shared confirmation dialog reuse.

A reviewer verdict is not runtime verification; evidence is in results/testing.md.

## Findings and dispositions

**Blocking:** none from either reviewer. No route load, popstate, reload or
library render posts or fetches source; generation checks gate every async
continuation and two attempt runtimes can never coexist; the restart lease has
no double release or leaked read-only editor; the operation ID is minted once,
reused across `operation_conflict`/`recovery_pending`/network retries and
dropped only on `stale_revision`/`lifecycle_locked`; error copy is fixed per
code and never carries server text; `is_shell_path` widens the static
namespace only to query-less `/attempt…`/`/history…` paths that always serve
`index.html`, with CSP and HEAD parity through the shared header path.

**F1 — non-blocking (reviewer). Restart success announcement is dropped.**
`attempt_lifecycle_actions.ts` announced "Restarted. Opening the new attempt."
and synchronously called `runtime.cleanup()`, whose `live.dispose()` cancels
the pending animation frame that paints the live region, so assistive
technology never heard it (the replacement still opened). ACCEPTED in
05_iterate: the pre-teardown announcement is removed; the replacement's own
reconnect screen (`role=status` "Reconnecting to the selected session…") and
attempt shell announce the transition instead.

**F2 — nit (reviewer). `navigateTo` keeps the current fragment on every
route.** After leaving an attempt the library URL can still carry the old
attempt's `attempt_id/level/tab`. LEFT AS IS, deliberately: the fragment is
non-secret view state, `readAttemptViewState` ignores it unless the attempt
ID matches, and preserving it is what lets "Back to library → Reconnect to
active session" restore the selected level and tab, which
`navigation.spec.mjs` asserts. Clearing it on non-attempt routes would regress
that accepted journey.

**Coordinator nit — nested dialog reuse.** The discard question reopens the
shared confirmation dialog from a confirm callback. Checked: the first dialog
is fully closed (native `close()` plus focus restore) before the network-bound
flush resolves and the second `open()` runs; the reviewer traced the same path
and reached the same conclusion. No change.

## Areas the reviewer checked and found clean

Route generation gating (`loadBootstrap`, `showAttemptRoute`, `reconnect`,
`openChosenAttempt`, library `onStart`/`onResume`); idempotent
`showAttempt`/`disposeAttempt`; lease handling in both lifecycle actions;
restart operation-ID lifecycle matching `restart_end.spec.mjs`; discard path
skipping the flush without skipping the lock; fixed error copy; DOM never
contains `/Users` or `/tmp`; server route prefixes, flat asset names
(`/attempts`, `/histories` still 404), CSP and HEAD coverage.
