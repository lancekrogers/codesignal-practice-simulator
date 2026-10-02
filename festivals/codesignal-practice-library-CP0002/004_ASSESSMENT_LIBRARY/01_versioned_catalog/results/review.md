# Sequence code review — 004/01_versioned_catalog

## Scope and reviewers

- Delegated reviewer: Cursor `claude-sonnet-5-thinking-high`, read-only plan
  mode, bounded to the uncommitted diff, the four new files and
  `docs/cli-contract.md`. It confirmed `workspace_cache.py`, `errors.py` and
  `models.py` have zero-line diffs, ran the focused modules (19 OK) and the
  full suite (444 OK, 1 skipped). Transcript kept in the session scratchpad.
- Coordinator review: independent pass over traversal/symlink handling in the
  packaged provider and over the route/catalog read-only paths.

A reviewer verdict is not runtime verification; evidence is in results/testing.md.

## Findings and dispositions

**Blocking:** none from either reviewer. File Storage digest and cache
validation are unchanged (pinned to the recorded pre-refactor tuple); every
mutation path validates the selected definition's provider first; staged bytes
are re-hashed; catalog enumeration is read-only and path-free.

**F1 — non-blocking (reviewer). No test planted a symlink against the packaged
provider.** The code rejected symlinks by inspection only. ACCEPTED in
05_iterate: new test covers a symlinked prompt, starter, manifest, final
directory and intermediate directory, each refused before `attempts/` exists.

**F2 — non-blocking (reviewer). Intermediate directory segments were not
symlink-checked.** Reachable only by someone who can already write inside the
installed package, but cheap to close. ACCEPTED in 05_iterate:
`PackagedOriginalProvider._directory` now checks every segment below the
resources root.

**F3 — non-blocking (reviewer). Docs wording could be read as "no directory is
created at all".** ACCEPTED in 05_iterate: the "Input providers" section now
says the shared `attempts/` root and its lock file may already exist.

**F4 — nits (reviewer).** Manifest re-read per call (left as is; the final
staged-byte check is the guarantee, and the cost is a few syscalls per
creation); archive allowlist directory check should reject `..` by shape
rather than by accident (ACCEPTED in 05_iterate: a segment regex matching the
registry's rule); duplicate input-directory check spans provider kinds
(harmless over-strictness, left as is).

## Areas the reviewer checked and found clean

Digest and legacy validation unchanged; fail-before-mutation ordering in
`create_attempt` and `restart_attempt`; only the selected provider runs;
staged-bytes re-check closes the validate-to-copy race; no post-construction
cache swap remains in `src/`; catalog read-only with static safe messages and
no `cache_directory` or path in any document; HTTP error mapping never leaks
paths; archive allowlist evaluated before the generic `.py` rule; both
providers pin identity through the shared `content_identity()`; all six
documented negative cases present and passing; docs consistent with code.
