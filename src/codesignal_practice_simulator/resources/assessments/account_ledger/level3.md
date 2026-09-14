# Account Ledger — Level 3: Scheduled transfers

Keep every earlier operation working and add transfers that execute later.

| Query | Result |
| --- | --- |
| `SCHEDULE_TRANSFER <ts> <source> <target> <amount> <execute_at>` | A new schedule ID `schedule1`, `schedule2`, … (a run-wide counter that advances only on success). `""` if either account does not exist, `source` equals `target`, `amount` is `0`, or `execute_at` is less than or equal to `ts`. |
| `CANCEL_TRANSFER <ts> <source> <schedule_id>` | `"true"` if the schedule exists, was created from `source`, and is still pending; it is then cancelled. Otherwise `"false"`. |
| `GET_SCHEDULE_STATUS <ts> <source> <schedule_id>` | `"PENDING"`, `"EXECUTED"`, `"FAILED"` or `"CANCELLED"`; `""` if the schedule does not exist or was not created from `source`. |

Rules:

- Funds are not reserved when a transfer is scheduled.
- Before the first query whose timestamp is greater than or equal to a
  schedule's `execute_at` is processed, every such pending schedule executes,
  in ascending order of (`execute_at`, schedule number). An execution succeeds
  only if both accounts still exist and the source balance is at least the
  amount; it then behaves exactly like a successful `TRANSFER` at
  `execute_at`, including outgoing totals. Otherwise the schedule becomes
  `FAILED` and nothing moves.
- Executed and failed schedules cannot be cancelled.
- Before `execute_at`, the status is `"PENDING"` even if the source cannot
  currently afford the transfer.

Example:

```
CREATE_ACCOUNT      1 src
CREATE_ACCOUNT      1 dst
DEPOSIT             2 src 100
SCHEDULE_TRANSFER   3 src dst 60 10    -> "schedule1"
SCHEDULE_TRANSFER   3 src dst 60 10    -> "schedule2"
SCHEDULE_TRANSFER   3 src dst 5  3     -> ""
GET_SCHEDULE_STATUS 4 src schedule1    -> "PENDING"
CANCEL_TRANSFER     5 dst schedule2    -> "false"
TRANSFER            10 src dst 1       -> "39"
GET_SCHEDULE_STATUS 10 src schedule1   -> "EXECUTED"
GET_SCHEDULE_STATUS 10 src schedule2   -> "FAILED"
CANCEL_TRANSFER     11 src schedule2   -> "false"
TOP_OUTGOING        11 1               -> "src(61)"
```
