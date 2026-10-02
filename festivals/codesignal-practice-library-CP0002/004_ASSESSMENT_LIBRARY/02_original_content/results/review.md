# Sequence code review — 004/02_original_content

## Scope and reviewers

- Delegated reviewer: Cursor `claude-sonnet-5-thinking-high`, read-only plan
  mode, bounded to the uncommitted diff, `docs/content/`, both packaged
  exercise directories, `tests/oracles/`, `tests/test_original_content.py`,
  `scripts/check_content.py` and `scripts/run_packaged_browser.py`. It ran the
  content suite (7 OK) and `check_content.py` itself, traced every packaged
  assertion against the specifications by hand, and built its own mutants to
  probe test discrimination. Transcript kept in the session scratchpad.
- Coordinator review: ran the packaged tests directly against each oracle and
  corrected two arithmetic slips in hand-written expectations before the
  delegated review (recorded in results/content_and_correctness.md).

A reviewer verdict is not runtime verification; evidence is in results/testing.md.

## Findings and dispositions

**F1 — blocking (reviewer). Two specified Account Ledger rules were not
asserted by any packaged test.** "A schedule whose target was closed before
execution fails" and "closing into an heir with pending schedules leaves them
untouched" appeared in the specification's edge-case list but no group
exercised them; the reviewer's mutants that broke both rules scored 4/4.
Reachable trigger: a candidate who cancels the heir's schedules on closure or
treats a missing target as executed. Impact: a wrong implementation scored as
fully correct, defeating the group-discrimination guarantee. ACCEPTED, fixed
in 05_iterate: a new `test_group_4` scenario closes a schedule's target before
`execute_at` (asserts `FAILED`) and closes an account into an heir with its
own pending schedule (asserts `PENDING`, later `EXECUTED`); both reviewer
mutants are now part of `tests/test_original_content.py` and fail at group 4.

**F2 — non-blocking (reviewer). Schedules due at different times within one
timestamp jump were untested.** ACCEPTED in 05_iterate: a `test_group_3`
scenario schedules a later-created transfer due earlier and asserts time
order; a mutant that orders by schedule number fails at group 3; the
specification's edge-case list names the rule.

**F3 — non-blocking (reviewer). `check_content.py` did not scan for vendor
identifiers, and the starter-fails guarantee lives only in the unit tests.**
ACCEPTED in part: the check now scans all six candidate-facing files for
`codesignal`/`cp0002` (case-insensitive) with a specific error. The
starter-fails and mutant proofs stay in `tests/test_original_content.py`,
which `just check unit` runs; the docs say what `just check content` covers.

**F4 — non-blocking (reviewer). Archive path check would not catch an oracle
by filename.** Not reachable today (`packages.find where=["src"]`, no
`MANIFEST.in`). ACCEPTED as defense in depth: `oracles` added to
`FORBIDDEN_ARCHIVE_PARTS` and `_reference.py`/`_solution.py`/`_oracle.py`
suffixes rejected anywhere in an archive; unit-tested.

**F5 — non-blocking (reviewer). Garbled sentence in the ledger
specification.** ACCEPTED: rewritten; the candidate-facing prompt was already
correct.

**Nits (reviewer).** A line-gutter artifact the reviewer itself dismissed; the
`ast.walk` import scan does not special-case `__import__` (left as is: the
scorer's audit hook blocks any import outside the attempt and stdlib at run
time regardless).

## Areas the reviewer checked and found clean

Expiry boundary and same-second expiry; backup/restore lifetime rebasing
against the restore timestamp (mutant caught at group 4); schedule ordering by
(`execute_at`, number) and funds consumption; `BALANCE_AT` boundaries, closure
gap and recreation; byte-order ties in scans and rankings; no wall-clock,
randomness or unbounded loops; oracle leak paths (provider copies only
candidate files, allowlists enforced twice); all six original mutants fail at
their claimed group; starter fails all groups, reference passes all groups
deterministically.
