# Application Foundation Delivery Evidence

## Reviewed project state

Project worktree branch `browser-assessment-app` contains three traced commits:

- `42b27da` — public shared runtime composition and compatibility tests
- `ed05a6b` — candidate document models/storage/service and 24 focused tests
- `ff05632` — secure local server/API/static shell and web/security tests

`git status --short` is clean after the commits. The ignored fixture cache is
hash validated and not tracked.

## Required deliverable contents

### Shared application

`src/codesignal_practice_simulator/application.py` defines public
`RuntimeApplication`, `EvaluationSnapshot`, and `create_application`. It composes
the unchanged workspace/lifecycle/evaluation/prompt/scorer/context authorities,
adds the candidate-document collaborator, serializes browser-visible actions
with a reentrant action boundary, and returns coherent source/session/time/test/
submit snapshots. `cli.py` uses the same factory and retains prior commands.

### Candidate documents

The implementation is split into human-sized files:

- `candidate_document_models.py` — stable errors, JSON-safe immutable records,
  strict UTF-8/256-KiB validation, ETags, snapshot/order/history schemas.
- `candidate_document_storage.py` — registered-candidate path, regular-file and
  baseline storage helpers.
- `candidate_documents.py` — attempt-locked read/CAS save, durable monotonic
  predecessor history, newest-50 pruning, reset, restore, and final-state guards.

No method accepts a path. `WorkspaceManager` captures only the initial
`simulation.py`; `Persistence.atomic_json` supplies the public atomic primitive.

### Local web application

`src/codesignal_practice_simulator/web/` contains:

- `server.py` — `WebServerConfig`, `WebServer`, fixed loopback bind, 256-bit
  capability fragment, request timeouts, clean shutdown, and opener/bind cleanup.
- `routes.py` — the fixed D004 route table only.
- `security.py` — canonical path/query/UUID, token/Origin, strict duplicate-free
  headers/JSON, and bounded body validation.
- `resources.py` — manifest-only package resources with symlink/traversal checks.
- `responses.py` — bounded stable JSON/safe score serialization.
- `static/` — a minimal first-party entry shell placeholder for phase 004.

All responses enforce no CORS, nosniff, frame denial, no-referrer, permissions,
same-origin resource policy, canonical CSP, and correct cache/MIME rules.

### Tests

Production behavior is exercised by `test_application.py`, four focused
candidate-document test modules plus support, `test_web_resources.py`,
`test_web_server.py`, extended CLI/end-to-end tests, and existing suites.

Final evidence recorded in sequence `results/`:

- 24 candidate-document tests passed.
- 17 final focused web resource/server tests passed.
- 48 web/CLI/E2E tests and 12 subtests passed.
- Full pytest: 242 tests and 108 subtests, three passes.
- Final unittest after static MIME repair: 205 passed.
- Legacy/provenance, wheel/offline, Python 3.10, compile, size, and diff checks
  passed.

Independent Cursor reviewers repeatedly rejected intermediate work until the
document ordering, final-state immutability, HTTP concurrency, security, and
static MIME findings were fixed. There are no unresolved material findings.
