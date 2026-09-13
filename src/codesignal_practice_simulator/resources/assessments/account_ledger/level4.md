# Account Ledger — Level 4: Historical balances and closure

Keep every earlier operation working and add history and account closure.

| Query | Result |
| --- | --- |
| `BALANCE_AT <ts> <account> <at>` | The account's balance after every operation with timestamp less than or equal to `at` (including schedules executed at or before `at`) was applied, as a decimal string. `""` if `at` is greater than `ts`, if the account did not exist at `at`, or if it had been closed at or before `at`. |
| `CLOSE_ACCOUNT <ts> <account> <heir>` | Moves the account's whole balance to `heir`, cancels every pending schedule created from the account, removes the account, and returns the heir's new balance. `""` if either account does not exist or `account` equals `heir`. |

Rules:

- A query at a time between two balance changes returns the earlier balance;
  a query exactly at a change includes it.
- Inheritance is not an outgoing transfer: neither account's outgoing total
  changes, and a closed account is no longer ranked.
- A closed account's ID may be recreated later; its history starts again at
  `0`, and `BALANCE_AT` for times in the gap between closure and re-creation
  returns `""`.
- Pending schedules whose target is the closed account stay pending and fail
  when they execute.

Example:

```
CREATE_ACCOUNT      1 a
CREATE_ACCOUNT      1 b
DEPOSIT             2 a 100
TRANSFER            5 a b 30
BALANCE_AT          6 a 1            -> "0"
BALANCE_AT          6 a 4            -> "100"
BALANCE_AT          6 a 5            -> "70"
BALANCE_AT          6 a 7            -> ""
SCHEDULE_TRANSFER   6 a b 10 20      -> "schedule1"
CLOSE_ACCOUNT       8 a b            -> "100"
GET_SCHEDULE_STATUS 8 a schedule1    -> "CANCELLED"
BALANCE_AT          9 a 8            -> ""
BALANCE_AT          9 b 8            -> "100"
CREATE_ACCOUNT      10 a             -> "true"
BALANCE_AT          11 a 9           -> ""
BALANCE_AT          11 a 10          -> "0"
TOP_OUTGOING        11 2             -> "a(0), b(0)"
```
