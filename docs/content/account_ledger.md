# Account Ledger

| | |
| --- | --- |
| Assessment ID | `account_ledger` |
| Display name | Account Ledger |
| Content version | `ledger-1` (placeholder until the package manifest pins it) |
| Profiles | `full-90m` (5,400 s), `drill-30m` (default 1,800 s) |
| Entry point | `simulate(queries: list[list[str]]) -> list[str]` |
| Levels | 4, progressive; group N covers levels 1..N |

A ledger of accounts holding non-negative integer balances in minor units.
Every operation is timestamped from level 1; the timestamp is the first
argument and timestamps are non-decreasing across the run.

## Level 1 — Accounts and transfers

### Operations

| Query | Returns |
| --- | --- |
| `CREATE_ACCOUNT <ts> <account>` | `"true"` if created, `"false"` if an account with that ID already exists. |
| `DEPOSIT <ts> <account> <amount>` | The account's new balance as a decimal string; `""` if the account does not exist or `amount` is `0`. |
| `TRANSFER <ts> <source> <target> <amount>` | The source's new balance; `""` if either account does not exist, `source` equals `target`, `amount` is `0`, or the source balance is less than `amount`. |

### Rules

- Balances start at `0` and never go negative.
- Amounts are non-negative integers; `0` is rejected as above.
- A failed operation changes nothing.

### Worked example

```
CREATE_ACCOUNT 1 acc1          -> "true"
CREATE_ACCOUNT 1 acc1          -> "false"
CREATE_ACCOUNT 2 acc2          -> "true"
DEPOSIT        3 acc1 500      -> "500"
DEPOSIT        3 acc9 10       -> ""        (missing account)
TRANSFER       4 acc1 acc2 200 -> "300"
TRANSFER       4 acc1 acc2 400 -> ""        (insufficient funds)
TRANSFER       5 acc1 acc1 1   -> ""        (same account)
```

### Edge cases the group asserts

- A transfer of the exact balance succeeds and leaves `"0"`.
- `DEPOSIT` of `0` returns `""` and leaves the balance unchanged.
- `["DEPOSIT", "1", "acc1"]` (wrong arity) and `["WITHDRAW", "1", "acc1", "5"]`
  (unknown operation) raise `ValueError`.

## Level 2 — Outgoing rankings

### Operations

| Query | Returns |
| --- | --- |
| `TOP_OUTGOING <ts> <n>` | Up to `n` accounts ranked by total outgoing amount (the sum of every successful transfer out of the account, including scheduled transfers executed by level 3), highest first; ties broken by account ID in ascending byte order. Each entry is `account(total)`; entries are joined by `", "`. `""` when `n` is `0` or there are no accounts. |

### Rules

- Every existing account is rankable, including those with `0` outgoing.
- Deposits and incoming transfers never count as outgoing.
- Failed transfers never count.
- Closed accounts (level 4) are not ranked.

### Worked example

```
CREATE_ACCOUNT 1 a
CREATE_ACCOUNT 1 b
CREATE_ACCOUNT 1 c
DEPOSIT        2 a 100
DEPOSIT        2 b 100
TRANSFER       3 a c 40
TRANSFER       3 b c 40
TRANSFER       4 a c 10
TOP_OUTGOING   5 2             -> "a(50), b(40)"
TOP_OUTGOING   5 5             -> "a(50), b(40), c(0)"
TOP_OUTGOING   5 0             -> ""
```

### Edge cases the group asserts

- Equal totals order by ID: `"a(40), b(40)"`, never the reverse.
- `n` larger than the number of accounts returns them all.
- Byte order ranks `"B"` before `"a"`.

## Level 3 — Scheduled transfers

### Operations

| Query | Returns |
| --- | --- |
| `SCHEDULE_TRANSFER <ts> <source> <target> <amount> <execute_at>` | A new schedule ID `schedule1`, `schedule2`, … (a run-wide counter that advances only on success). `""` if either account does not exist, `source` equals `target`, `amount` is `0`, or `execute_at` is less than or equal to `ts`. |
| `CANCEL_TRANSFER <ts> <source> <schedule_id>` | `"true"` if the schedule exists, was created from `source`, and is still pending; it is then cancelled. Otherwise `"false"`. |
| `GET_SCHEDULE_STATUS <ts> <source> <schedule_id>` | `"PENDING"`, `"EXECUTED"`, `"FAILED"` or `"CANCELLED"`; `""` if the schedule does not exist or was not created from `source`. |

### Rules

- Funds are not reserved at scheduling time.
- Before the first query whose timestamp is greater than or equal to a
  schedule's `execute_at` is processed, every such pending schedule executes,
  in ascending order of (`execute_at`, schedule number). An execution succeeds
  only if both accounts still exist and the source balance is at least the
  amount; it then behaves like a successful `TRANSFER` at `execute_at`
  (including outgoing totals). Otherwise the schedule becomes `FAILED` and
  nothing moves.
- Executed and failed schedules cannot be cancelled.
- A `GET_SCHEDULE_STATUS` at a timestamp before `execute_at` reports
  `"PENDING"` even if the source cannot currently afford the transfer.

### Worked example

```
CREATE_ACCOUNT      1 src
CREATE_ACCOUNT      1 dst
DEPOSIT             2 src 100
SCHEDULE_TRANSFER   3 src dst 60 10     -> "schedule1"
SCHEDULE_TRANSFER   3 src dst 60 10     -> "schedule2"
SCHEDULE_TRANSFER   3 src dst 5  3      -> ""           (execute_at <= ts)
GET_SCHEDULE_STATUS 4 src schedule1     -> "PENDING"
CANCEL_TRANSFER     5 dst schedule2     -> "false"      (not the owner)
TRANSFER            10 src dst 1        -> "39"         (schedule1 ran first: 100-60=40, then 40-1)
GET_SCHEDULE_STATUS 10 src schedule1    -> "EXECUTED"
GET_SCHEDULE_STATUS 10 src schedule2    -> "FAILED"     (39 < 60 at execution)
CANCEL_TRANSFER     11 src schedule2    -> "false"
TOP_OUTGOING        11 1                -> "src(61)"
```

### Edge cases the group asserts

- Two schedules with the same `execute_at` execute in schedule-number order,
  so the first can consume the funds the second needed.
- Schedules due at different times inside one timestamp jump execute in time
  order, not creation order.
- A schedule whose target was closed (level 4) before execution fails.
- Cancelling twice returns `"false"` the second time.
- A schedule ID from a failed `SCHEDULE_TRANSFER` is never issued, so numbering
  has no gaps.

## Level 4 — Historical balances and closure

### Operations

| Query | Returns |
| --- | --- |
| `BALANCE_AT <ts> <account> <at>` | The account's balance after every operation with timestamp less than or equal to `at` (including schedules executed at or before `at`) was applied, as a decimal string. `""` if `at` is greater than `ts`, if the account did not exist at `at` (created later, or never), or if it had been closed at or before `at`. |
| `CLOSE_ACCOUNT <ts> <account> <heir>` | Moves the account's whole balance to `heir`, cancels every pending schedule created from the account, removes the account, and returns the heir's new balance. `""` if either account does not exist or `account` equals `heir`. |

### Rules

- History is per account and is defined by the sequence of successful
  balance-changing operations and their timestamps; a query at `at` between two
  changes returns the earlier balance.
- Inheritance is not an outgoing transfer: neither the closed account's nor
  the heir's `TOP_OUTGOING` total changes.
- A closed account's ID may be recreated later with `CREATE_ACCOUNT`; its
  history starts again at `0`, and `BALANCE_AT` for times during the closed
  gap returns `""`.
- Pending schedules whose target is the closed account are left pending and
  fail when they execute.

### Worked example

```
CREATE_ACCOUNT 1 a
CREATE_ACCOUNT 1 b
DEPOSIT        2 a 100
TRANSFER       5 a b 30
BALANCE_AT     6 a 1            -> "0"
BALANCE_AT     6 a 4            -> "100"
BALANCE_AT     6 a 5            -> "70"
BALANCE_AT     6 a 7            -> ""          (at > ts)
SCHEDULE_TRANSFER 6 a b 10 20   -> "schedule1"
CLOSE_ACCOUNT  8 a b            -> "100"       (b: 30 + 70)
GET_SCHEDULE_STATUS 8 a schedule1 -> "CANCELLED"
BALANCE_AT     9 a 8            -> ""          (closed)
BALANCE_AT     9 b 8            -> "100"
CREATE_ACCOUNT 10 a             -> "true"
BALANCE_AT     11 a 9           -> ""          (gap between closure and re-creation)
BALANCE_AT     11 a 10          -> "0"
TOP_OUTGOING   11 2             -> "a(0), b(0)"  (a's old outgoing is gone with the closed account)
```

### Edge cases the group asserts

- `BALANCE_AT` exactly at a change timestamp includes the change.
- `BALANCE_AT` at a time when a scheduled transfer executed reflects it.
- Closing an account with balance `0` returns the heir's unchanged balance.
- Closing into an account that has pending schedules leaves those untouched.

## Deterministic correctness contracts

- Output length equals input length for every well-formed run.
- Schedule IDs are assigned in creation order without gaps.
- Ranking order is fully specified by (total descending, ID ascending).
- Historical queries never change state; replaying a run twice yields
  identical outputs.
