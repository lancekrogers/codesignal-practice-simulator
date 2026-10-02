# Editor asset code review

Date: 2026-09-09

Review command:

```sh
cursor-agent -p --mode ask --trust --model gpt-5.6-luna-high "Review the current uncommitted sequence diff against its Festival goal. Do not edit."
```

Reviewed diff base: project `HEAD ff05632` through the complete uncommitted
`004_ASSESSMENT_IDE/01_editor_assets` sequence.

Reviewer: fresh Cursor CLI sessions using `gpt-5.6-luna-high` in read-only ask
mode. The final narrow review returned `APPROVE`.

## Findings and dispositions

Critical findings: none.

Material findings raised during review and resolved before approval:

- Added exact runtime notices for Monaco, Monaco ThirdPartyNotices, DOMPurify,
  and marked. Lockfile closure, a fixed required mapping, fixed snapshot hashes,
  installed-package byte comparison, and mutation tests now prevent an
  incomplete notice bundle.
- Replaced unsafe partial publication with durable staged generations,
  atomically flushed transaction state, bounded builder/reader coordination,
  race-safe stale-owner reclamation, and recovery-only validation at every
  durable crash checkpoint.
- Added full generation-contract validation in both Node recovery and Python
  reader fallback. Invalid, incomplete, polluted, symlinked, or hash-mismatched
  generations fail closed.
- Canonicalized publication under trusted project/temporary roots and rejected
  immediate or nested symlink-ancestor escapes and untrusted transaction paths.
- Made directory flushing strict on POSIX and narrowly best-effort only for
  documented unsupported Windows directory-fsync errors; file flushes and
  atomic renames remain required.
- Removed the static route's two-read publication race and mapped a missing
  asset from the single validated read to `404`.
- Hardened capability storage precedence, font MIME handling, browser teardown,
  same-origin/offline assertions, and the forced Monaco read-only fallback.
- Made sdist, wheel, and installed-package asset membership and bytes exact;
  added archive/content/cache/source-path/secret/FETCH_ONLY negative checks.

Non-blocking observations:

- Stable `app.js`/`styles.css` aliases intentionally duplicate the current
  fingerprinted assets for compatibility. This can be removed in a later
  version once all consumers use manifest-derived names.
- Windows was not executed on this macOS host. Windows directory fsync uses a
  documented narrow fallback; all other publication errors remain fatal.

## Final rationale

The first-party TypeScript, build, verification, and Python resource code is
organized around explicit responsibilities and remains maintainable by a
human. The large generated Monaco file is reproducible third-party output, not
hand-maintained source. Exact provenance and notices identify its origin.

The approved implementation preserves FETCH_ONLY and candidate-content
isolation, has no runtime network dependency, serves only manifest-validated
same-origin assets, and provides a safe read-only source view if Monaco cannot
initialize. No material review finding remains open.
