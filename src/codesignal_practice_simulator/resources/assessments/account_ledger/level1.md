# Account Ledger — Level 1: Accounts and transfers

Implement `simulate(queries)` in `simulation.py`. `queries` is a list of
queries; each query is a list of strings whose first element is the operation
name. Return a list with exactly one output string per query, in order.

Every operation is timestamped: the timestamp is the first argument after the
operation name, an integer number of seconds. Timestamps are non-decreasing
across a run; equal timestamps are processed in query order. Balances are
non-negative integers in minor units. Account IDs match `[A-Za-z0-9_.-]{1,64}`.

| Query | Result |
| --- | --- |
| `CREATE_ACCOUNT <ts> <account>` | `"true"` if created, `"false"` if an account with that ID already exists. |
| `DEPOSIT <ts> <account> <amount>` | The account's new balance as a decimal string; `""` if the account does not exist or `amount` is `0`. |
| `TRANSFER <ts> <source> <target> <amount>` | The source's new balance; `""` if either account does not exist, `source` equals `target`, `amount` is `0`, or the source balance is less than `amount`. |

Rules:

- Balances start at `0` and never go negative.
- A failed operation changes nothing.
- An unknown operation name, or an operation with the wrong number of
  arguments, must raise `ValueError`. Well-formed queries never raise.

Example:

```
CREATE_ACCOUNT 1 acc1           -> "true"
CREATE_ACCOUNT 1 acc1           -> "false"
CREATE_ACCOUNT 2 acc2           -> "true"
DEPOSIT        3 acc1 500       -> "500"
DEPOSIT        3 acc9 10        -> ""
TRANSFER       4 acc1 acc2 200  -> "300"
TRANSFER       4 acc1 acc2 400  -> ""
TRANSFER       5 acc1 acc1 1    -> ""
```

Your implementation must be deterministic: the same query list always yields
the same output list, independent of wall-clock time or environment.
