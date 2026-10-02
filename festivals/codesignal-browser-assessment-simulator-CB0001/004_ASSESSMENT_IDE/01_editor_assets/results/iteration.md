# Editor asset iteration

Date: 2026-09-09

## Testing findings and fixes

- A real first-time resource reader could observe the static subpackage while a
  generation swap temporarily removed it and raise `ModuleNotFoundError`.
  The reader now resolves the static directory from the already-imported web
  package parent and participates in the publication lock protocol. The focused
  resource/publication suite and final 248-test suite pass with no skips.
- The external-URL scanner treated the inert MPL notice URL as a runtime network
  dependency. Notice URLs now use an exact, audited allowlist while executable
  network forms remain rejected; the negative network test proves application
  code cannot bypass that rule. Asset checks and both browser suites pass.
- A resource timeout test initially created a lock with a fixture name that did
  not match the production lock. The fixture now uses the real publication lock
  name and verifies the bounded timeout path. The focused suite passes.
- No warning requiring action or missing evidence remains. The final verification
  is 248 unit tests with no skips, 60 focused asset/resource/server tests, four
  source browser journeys, four installed-wheel browser journeys, deterministic
  asset generation, exact archive membership, compile checks, and legacy checks.

## Cursor review findings and fixes

- Runtime notices were incomplete. Exact Monaco, Monaco third-party, DOMPurify,
  and marked notice mappings, fixed snapshot hashes, installed-package byte
  comparisons, and mutation tests now enforce the complete license bundle.
- Publication was not fully atomic or crash durable. Assets now publish as a
  flushed staged generation with an atomically flushed transaction marker,
  bounded builder/reader coordination, recovery validation at every durable
  checkpoint, and a race-safe stale-owner reclaimer.
- Recovery validation did not initially enforce the complete generation
  contract. Node recovery and Python fallback now reject missing, extra,
  polluted, symlinked, or hash-mismatched generations, including an incomplete
  but internally hash-valid previous generation.
- Output and transaction paths could escape through nested symlink ancestors.
  Publication is constrained to canonical trusted project or temporary roots,
  and untrusted immediate or nested ancestors and marker paths fail closed.
- Directory flush handling was overly broad. POSIX directory flush failures are
  fatal; only documented unsupported Windows directory-flush errors are ignored.
  File flushes and atomic renames are always required.
- The static route performed two reads across a possible generation swap. It now
  performs one validated read and maps a missing asset from that read to `404`.
- Capability persistence, font MIME, browser teardown, offline-origin assertions,
  and forced Monaco failure behavior were hardened. A Monaco initialization
  failure exposes exact source read-only and sends no mutation request.
- Package verification was incomplete. Source, sdist, wheel, and installed
  package assets must now match the manifest exactly by membership and bytes;
  cache, source-path, secret, fixture, archive, and `FETCH_ONLY` sentinels have
  negative tests.

Critical findings: none. No critical, major, minor, or test-gap finding remains
open. The final independent Cursor CLI review returned `APPROVE` after checking
Python/Node contract parity and installed-resource compatibility.

## Final gate evidence

- `ASSET_BUILDER=/tmp/codesignal-build-env-48721/bin/python python3 -m unittest discover -s tests -q`
  passed 248 tests with no skips in 94.802 seconds.
- The final focused command passed 60 tests with no skips.
- `npm --prefix webui run check`, `npm --prefix webui run build`, and
  `npm --prefix webui run check-assets` pass.
- `git diff --check` passes. `git status --short` contains only expected source,
  tests, build tooling, audited notices, and deterministic manifest assets; it
  contains no dependency cache, attempt data, secret, or `FETCH_ONLY` content.
- No P0/P1 requirement was deferred and no exclusion was relaxed.
