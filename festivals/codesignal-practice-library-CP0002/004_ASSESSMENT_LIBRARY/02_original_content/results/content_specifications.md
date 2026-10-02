# Content specifications

Authored by the coordinator on 2026-09-12 after the D005 resolution recorded
the user's delegated decision (File Storage plus two original tracks:
In-Memory Records and Account Ledger). The prerequisite gate is satisfied by
that recorded decision; no spec work happened while D005 was open.

## Deliverables (project worktree, uncommitted until 06_fest_commit)

- `docs/content/README.md`: shared conventions — runner contract
  (`test_simulation.TestSimulateCodingFramework.test_group_1..4`, one group
  per level, group N covers levels 1..N), entry point
  `simulate(queries: list[list[str]]) -> list[str]`, query grammar, time
  semantics (non-decreasing timestamps, scheduled effects applied before the
  first query at or after their time), return conventions (`"true"`/`"false"`,
  decimal strings, `""` for missing, `", "` joins with specified order),
  error contract (unknown operation or wrong arity raises `ValueError`;
  well-formed queries never raise), determinism, bounds, level dependencies,
  packaging layout and the oracle exclusion.
- `docs/content/in_memory_records.md` (`in_memory_records`): L1 records and
  fields (`SET`/`GET`/`DELETE`), L2 deterministic scans (`SCAN`,
  `SCAN_BY_PREFIX`, byte-order sorting), L3 expiry through timestamped variants
  with TTL (live strictly before expiry, overwrite replaces expiry, emptied
  records cease to exist), L4 snapshots and restoration (`BACKUP` counts live
  records and stores remaining lifetimes; `RESTORE` picks the latest backup at
  or before `at` and rebases expiries). Worked example and asserted edge cases
  per level.
- `docs/content/account_ledger.md` (`account_ledger`): L1 accounts and
  transfers (`CREATE_ACCOUNT`, `DEPOSIT`, `TRANSFER`, zero and self-transfer
  rules), L2 `TOP_OUTGOING` ranking (total descending, ID ascending, closed
  accounts excluded), L3 scheduled transfers (`SCHEDULE_TRANSFER` with gapless
  IDs, execution before the first query at or after `execute_at` in
  (`execute_at`, number) order, funds not reserved, `CANCEL_TRANSFER`,
  `GET_SCHEDULE_STATUS`), L4 `BALANCE_AT` history semantics and
  `CLOSE_ACCOUNT` (inheritance, cancellation, recreation gap). Worked example
  and asserted edge cases per level.

## Checks required by the task

- Assessment IDs are `in_memory_records` and `account_ledger`; neither reuses
  `CP0002` or any festival or work-item identifier
  (`grep -rn CP0002 docs/content/` finds nothing).
- No vendor name or reproduced vendor text: `grep -rin codesignal docs/content/`
  finds nothing. The query-list-in, string-list-out shape is a generic
  simulation convention the existing runner and starter already use; every
  operation name, rule and scenario is original.
- Every level lists explicit edge cases: empty/missing lookups, boundary
  timestamps (expiry exactly at the query time, `BALANCE_AT` exactly at a
  change), invalid references (missing account, wrong schedule owner, same
  account), zero amounts, ties, wrong arity and unknown operations.
- Cross-check against the D003 runner contract (signoff): each exercise ships
  `simulation.py` and `test_simulation.py`; the test class and the four method
  names are exactly those `scoring.py` loads (`test_simulation.
  TestSimulateCodingFramework.test_group_{1..4}`); the starter returns `[]` so
  every group fails until implemented; the error contract keeps a runner from
  hanging on malformed input; bounds keep every group inside the runner's
  10-second per-group timeout. No runner extension is needed.
- `python3 -m unittest tests.test_documentation` OK; `git diff --check` clean.

## Decisions worth noting for task 02

- Untimestamped and timestamped families are never mixed in one run
  (In-Memory Records L1–L2 vs L3–L4); tests will respect that.
- Schedule execution is triggered lazily by the next query at or after
  `execute_at`, which keeps the model single-threaded and deterministic and
  avoids any wall-clock dependence.
- `content_version` placeholders (`records-1`, `ledger-1`) become the manifest
  values in task 02; the digest is computed by the packaged provider from the
  bundled files.
