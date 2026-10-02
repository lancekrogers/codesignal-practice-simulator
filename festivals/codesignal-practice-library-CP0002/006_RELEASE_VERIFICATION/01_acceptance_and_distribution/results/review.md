# Sequence code review — 006/01_acceptance_and_distribution

## Scope and reviewers

- Delegated reviewer: Cursor `claude-sonnet-5-thinking-high`, read-only plan
  mode, bounded to the uncommitted diff (provider `__pycache__` tolerance,
  packaging fallback, new end-to-end and browser tests, history result label,
  README/docs) plus the untracked `webui/tests/acceptance_matrix.spec.mjs`;
  generated bundle excluded. It ran the 21 targeted packaging/provider unit
  tests and the new end-to-end lifecycle test (all pass), traced the stale-tab
  behaviour through the unchanged client code, and cross-checked every README
  claim (exit codes, error codes and messages, compatibility statement)
  against `errors.py`, `workspace.py`, `lifecycle.py`, `attempt_reviews.py`
  and `attempt_history.py`. Transcript: session scratchpad `review_006_01.txt`.
- Coordinator review: independent pass over the two defects found by the
  wheel check (why an installed package failed, why the fallback is the same
  backend the frontend drives) and over the matrix rows' evidence pointers.

A reviewer verdict is not runtime verification; evidence is in results/testing.md.

## Findings and dispositions

**Blocking:** none from either reviewer.

**Non-blocking:** none. The reviewer confirmed the `__pycache__` tolerance
accepts only a real directory of that exact name, never reads or stages its
contents, and still refuses a plain file, a symlink or any other extra entry;
the PEP 517 fallback is chosen only when the `build` frontend is unavailable,
is gated on setuptools >= 61, runs from the checkout without network, and its
archives go through the unchanged `inspect_archives` allowlist (which already
excluded `__pycache__` members). The new tests assert byte-level snapshots, an
exact single-replacement listing, a captured zero-POST stale tab, byte-identical
legacy records and the absence of `active.json`; none passes trivially.

**Nit (reviewer).** The README's replayed-restart transcript omitted the
`abandoned_session: null` field the real response carries. ACCEPTED in
05_iterate: transcript completed.

## Areas the reviewer checked and found clean

Provider validation ordering and staging path; builder discovery order and
error text; archive inspection unaffected; test assertions non-trivial;
documentation claims verbatim-consistent with the code; no downgrade-safety
or official-equivalence claim anywhere in the docs.
