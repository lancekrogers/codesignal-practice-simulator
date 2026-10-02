# Local Web API Testing

Date: 2026-09-09
Base commit: `ed05a6b`

## Final evidence

- Focused web resource/server suite: 17 passed after final MIME/cache repair.
- Focused web/CLI/end-to-end pytest run: 48 tests and 12 subtests passed.
- Full pytest suite: 242 tests and 108 subtests passed three times during the
  main hardening run.
- Final full unittest run after the isolated header repair: 205 passed.
- Legacy/provenance checks, offline fixture tests, wheel build/resource loading,
  Python 3.10 imports, compileall, size checks, and `git diff --check`: passed.

Coverage includes fixed routes, capability/Origin/method/query/path/body/header
boundaries, duplicate JSON and headers, prompt/response bounds, canonical CSP,
static symlinks/MIME/cache, no CORS, atomic source/evaluation snapshots,
concurrent save/test/submit, corrupt bootstrap, expiry/finality, first/repeated
submit, cross-attempt isolation, partial-body shutdown, bind/opener cleanup,
restart token rotation, and packaged/wheel assets.

No browser trace, attempt, cache, dependency directory, secret, or FETCH_ONLY
content is tracked.
