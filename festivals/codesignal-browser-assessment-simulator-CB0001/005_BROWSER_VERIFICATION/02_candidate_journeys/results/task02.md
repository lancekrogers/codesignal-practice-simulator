# Task 02 — expiry, submit, and restart journey

## Verification commands

All browser commands ran serially from `webui/` with the repository-default
Playwright configuration and privacy-safe reporters; no reporter or worker
overrides were supplied.

- `npm run test:browser -- actions expiry submit restart` — 17 passed, exit 0.
- `npm run test:browser -- tests/actions.spec.mjs tests/accepted_journeys.spec.mjs tests/fresh_findings.spec.mjs tests/source_terminal.spec.mjs tests/browser_continuity.spec.mjs` — 33 passed, exit 0.
- `python3 -m unittest tests.test_lifecycle tests.test_rendering -v` — 32 passed, exit 0 (`Ran 32 tests`, `OK`).

The browser filter command and the five-spec command were rerun after the
material coverage addition; the final counts above are the post-change
results. No concurrent browser suites were run.

## Requirement-to-assertion mapping

- Four-group pass/fail semantics and candidate-failure transport distinction:
  `actions.spec.mjs` asserts `4 of 4`, `3 of 4`, `Needs work`, failed-level
  status, score-only failure handling, and separate internal HTTP failure
  handling.
- Safe bounded output: `actions.spec.mjs` rejects oversized/unsupported
  practice evidence and asserts absence of `FETCH_ONLY` and
  `SCORER_INTERNAL_SENTINEL`; `accepted_journeys.spec.mjs` preserves safe
  failed/error evidence through restart.
- Save/test race and exact source ordering: `actions.spec.mjs` asserts one
  `PUT /api/source` before one `POST /api/test`, one evaluation for competing
  clicks, and shared operation locking during delayed testing and
  restore/reset. `source_terminal.spec.mjs` asserts delayed terminal saves are
  canceled without replacing the authoritative saved source.
- Injected-clock expiry and mutation locking: `accepted_journeys.spec.mjs`
  advances the fixture clock to the server deadline and asserts all browser
  mutations are disabled/read-only after the server reports `expired`.
  `fresh_findings.spec.mjs` also verifies timer resynchronization rejects
  another attempt's time snapshot without changing shell state.
- Timeout submission and final immutability: the added
  `expired attempt accepts one timeout submission and stays immutable` test
  submits through the API after injected expiry, asserts the
  `started → expired → submitted` event sequence, one scorer call, stored
  score/session/source equality on repeat (`newly_submitted: false`), unchanged
  `context --format json` and `STATUS.md` bytes, and the same final result
  after process restart.
- Cancel/confirm submit: `actions.spec.mjs` asserts cancel restores opener
  focus and confirmation locks the terminal UI; it also verifies exact source
  flush ordering before submit.
- Refresh/restart and no rescoring: `actions.spec.mjs`,
  `accepted_journeys.spec.mjs`, and `fresh_findings.spec.mjs` cover reload and
  real process restart. They assert final source/result persistence and stable
  scorer-call counts.
- Browser/terminal synchronization: `browser_continuity.spec.mjs` validates
  the JSON context schema, lifecycle, score, event history, next legal
  commands, and `STATUS.md` against browser responses before and after
  submission, while keeping coaching out of public read surfaces.
- Lifecycle/rendering unit coverage: the 32 passing tests include overdue
  submit, expiry byte stability, repeat submit without rescoring, terminal
  mutation refusal, safe derived context/status rendering, and preservation of
  newer lifecycle state.

## Scope

One material missing browser assertion was added to
`webui/tests/accepted_journeys.spec.mjs`: allowed timeout submission after
server expiry with repeat/restart immutability checks. Existing task01
changes were preserved. No task status was changed, no commit was created,
and no task03 work was performed.
