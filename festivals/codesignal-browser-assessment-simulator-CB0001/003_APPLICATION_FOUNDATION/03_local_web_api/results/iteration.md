# Local Web API Iteration

Material changes made after independent review:

- Added a reentrant application action boundary and typed coherent snapshots;
  save/test/submit and their returned session/time/source are serialized within
  the local server process.
- Made bootstrap distinguish absent selection from corrupt/unavailable state.
- Hardened canonical path/CSP, manifest resources/symlinks, token entropy,
  Origin/method/body/duplicate-header/duplicate-JSON parsing, prompt bounds,
  request timeout/shutdown, permissions, framing, and bind/opener cleanup.
- Preserved `newly_submitted` and stable candidate-failure semantics.
- Added concurrency, cross-attempt, final-state, restart, wheel, and exhaustive
  negative HTTP tests.
- Restored exactly one static `Content-Type` and `Cache-Control` in the final
  repair so `nosniff` assets load correctly.

All final focused/full/offline/legacy/wheel/compile/diff checks pass. No P0/P1
requirement was deferred and no forbidden route or content surface was added.
The sequence is commit-ready.
