# Original exercise specifications

These documents specify the simulator's original practice exercises. They are
first-party content: no text, query names or scenarios are reproduced from any
vendor assessment. Each exercise has a stable assessment ID that is distinct
from any festival or work-item identifier.

| Assessment ID | Title | Specification |
| --- | --- | --- |
| `in_memory_records` | In-Memory Records | [in_memory_records.md](in_memory_records.md) |
| `account_ledger` | Account Ledger | [account_ledger.md](account_ledger.md) |

## Shared conventions

**Runner contract.** Every exercise ships `simulation.py` (the candidate's
file) and `test_simulation.py`, whose class
`TestSimulateCodingFramework` defines exactly `test_group_1` through
`test_group_4`, one per level. The isolated scorer loads those four names and
nothing else (`scoring.py`, runner contract `unittest-groups-v1`). Group N
exercises level N together with every earlier level; a group passes only when
all of its assertions pass.

**Entry point.** `simulation.py` defines

```python
def simulate(queries: list[list[str]]) -> list[str]: ...
```

It receives the whole query list and returns one output string per query, in
order. Every token is a string. The starter returns `[]` so that every group
fails until the candidate implements it.

**Query grammar.** A query is a list whose first element is the operation name
in upper snake case and whose remaining elements are its arguments in the order
the specification lists. Identifiers (record IDs, field names, account IDs,
schedule IDs) match `[A-Za-z0-9_.-]{1,64}`. Non-negative integers are decimal
ASCII with no sign and no leading `+`. Timestamps are integer seconds.

**Time.** Where an exercise is timestamped, the timestamp is the first argument
after the operation name, and timestamps are non-decreasing across the whole
query list. Equal timestamps are processed in list order. Anything scheduled
to happen "at" time T is applied before the first query whose timestamp is
greater than or equal to T is processed.

**Return conventions.** Boolean results are the strings `"true"` and `"false"`.
Numbers are decimal strings. A lookup of something that does not exist returns
the empty string `""` unless the specification says otherwise. Lists are joined
with `", "` (comma, space) and are ordered as the specification states, never
by insertion order unless it says so.

**Errors.** A well-formed query never raises. An unknown operation name or an
operation with the wrong number of arguments raises `ValueError`; group tests
include one such case per exercise so a runner never hangs on bad input.

**Determinism.** Given the same query list, `simulate` returns the same output
list. Implementations must not depend on wall-clock time, randomness, dict
iteration order for anything the specification orders, or environment state.

**Bounds.** At most 10,000 queries per run; at most 1,000 records or accounts;
values up to 10^12. Reference implementations complete every group well under
the runner's per-group timeout.

**Level dependencies.** Level N may use every operation from levels 1 through
N. A level never changes the meaning of an earlier level's operation for
untimestamped runs; where a later level introduces timestamped variants, the
run uses either the untimestamped or the timestamped family, never both.

**Packaging.** Each exercise directory under the package's
`resources/assessments/<assessment_id>/` contains exactly `level1.md` …
`level4.md`, `simulation.py`, `test_simulation.py` and `content-manifest.json`.
Development oracles (correct and deliberately wrong implementations) live under
`tests/` and are never packaged.
