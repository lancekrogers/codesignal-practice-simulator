# Runtime Composition Testing

Date: 2026-09-09
Worktree branch: `browser-assessment-app`
Base: `f1a178ae5276dd36cdba7c450dcc2fe39b5d49d3`

## Final evidence

- `python3 -m unittest tests.test_application tests.test_cli -q` — 29 passed
  before review remediation; all focused tests also passed after remediation.
- `python3 -m unittest discover -s tests -q` — 163 passed twice in the Cursor
  repair run and once again independently after it.
- `just verify` — passed: provenance/git-boundary checks, 26 spec tests, 12
  staged tests, four study-stage checks, 163 unittest tests, four real-process
  end-to-end tests, and `git diff --check`.
- `python3 -m unittest tests.test_end_to_end -v` — four passed.
- `python3 -m compileall -q src tests` — passed.
- Python import checks — passed on locally available 3.10, 3.11, 3.12, and
  3.14 interpreters.

The ignored worktree fixture cache was populated from the already validated
seven-file private-project cache through the normal `fetch --source` path. No
fixture bytes or attempts are tracked.

## Test issue found and resolved

The ps-based exact-scorer-argv end-to-end assertion intermittently missed one of
four 0.2-second child processes under machine load. Exact argv matching was not
weakened; the synthetic observation duration was increased and three subsequent
full-suite executions plus the focused E2E suite passed.

No failure artifact was retained.
