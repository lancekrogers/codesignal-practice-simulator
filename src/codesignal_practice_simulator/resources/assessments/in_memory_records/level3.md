# In-Memory Records — Level 3: Expiry

Level 3 adds timestamped variants of every operation. The timestamp is the
first argument after the operation name, an integer number of seconds.
Timestamps are non-decreasing across a run; equal timestamps are processed in
query order. A run uses either the untimestamped family (Levels 1–2) or the
timestamped family, never both.

| Query | Result |
| --- | --- |
| `SET_AT <ts> <record> <field> <value>` | As `SET`; the field never expires. |
| `SET_AT_WITH_TTL <ts> <record> <field> <value> <ttl>` | As `SET`; the field expires at `ts + ttl`. `ttl` is a positive integer number of seconds. |
| `GET_AT <ts> <record> <field>` | As `GET`, considering only fields live at `ts`. |
| `DELETE_AT <ts> <record> <field>` | As `DELETE`, considering only fields live at `ts`. |
| `SCAN_AT <ts> <record>` | As `SCAN`, over fields live at `ts`. |
| `SCAN_BY_PREFIX_AT <ts> <record> <prefix>` | As `SCAN_BY_PREFIX`, over fields live at `ts`. |

Rules:

- A field with expiry `E` is live for every query whose timestamp is strictly
  less than `E`, and absent (as if deleted) for every query whose timestamp is
  greater than or equal to `E`.
- Overwriting a field replaces its expiry: `SET_AT` makes it permanent,
  `SET_AT_WITH_TTL` sets a new expiry counted from the new timestamp.
- A record whose every field has expired does not exist: `SET_AT` on it
  returns `"true"` and scans return `""`.
- Expired fields never come back on their own.

Example:

```
SET_AT_WITH_TTL 1  s a 1 5   -> "true"    (a expires at 6)
SET_AT          2  s b 2     -> "false"
GET_AT          5  s a       -> "1"
GET_AT          6  s a       -> ""        (expired at 6)
SCAN_AT         6  s         -> "b(2)"
DELETE_AT       7  s a       -> "false"
SET_AT_WITH_TTL 8  s b 9 1   -> "false"   (b now expires at 9)
SCAN_AT         9  s         -> ""
SET_AT          9  s c 3     -> "true"    (the record was empty)
```
