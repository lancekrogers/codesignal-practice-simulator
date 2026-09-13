# Account Ledger — Level 2: Outgoing rankings

Keep every Level 1 operation working and add a ranking query.

| Query | Result |
| --- | --- |
| `TOP_OUTGOING <ts> <n>` | Up to `n` accounts ranked by total outgoing amount (the sum of every successful transfer out of the account), highest first; ties are broken by account ID in ascending byte order. Each entry is `account(total)`; entries are joined by `", "`. `""` when `n` is `0` or there are no accounts. |

Rules:

- Every existing account is rankable, including accounts with `0` outgoing.
- Deposits and incoming transfers never count as outgoing; failed transfers
  never count.
- Byte order ranks `"B"` before `"a"`.
- `n` larger than the number of accounts returns them all.

Example:

```
CREATE_ACCOUNT 1 a
CREATE_ACCOUNT 1 b
CREATE_ACCOUNT 1 c
DEPOSIT        2 a 100
DEPOSIT        2 b 100
TRANSFER       3 a c 40
TRANSFER       3 b c 40
TRANSFER       4 a c 10
TOP_OUTGOING   5 2       -> "a(50), b(40)"
TOP_OUTGOING   5 5       -> "a(50), b(40), c(0)"
TOP_OUTGOING   5 0       -> ""
```
