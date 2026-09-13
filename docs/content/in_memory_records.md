# In-Memory Records

| | |
| --- | --- |
| Assessment ID | `in_memory_records` |
| Display name | In-Memory Records |
| Content version | `records-1` (placeholder until the package manifest pins it) |
| Profiles | `full-90m` (5,400 s), `drill-30m` (default 1,800 s) |
| Entry point | `simulate(queries: list[list[str]]) -> list[str]` |
| Levels | 4, progressive; group N covers levels 1..N |

A record store keyed by record ID. Each record holds string fields. Levels 1
and 2 are untimestamped. Levels 3 and 4 use timestamped variants of every
operation; a run uses one family only.

## Level 1 — Records and fields

### Operations

| Query | Returns |
| --- | --- |
| `SET <record> <field> <value>` | `"true"` if this call created the record (it did not exist before), otherwise `"false"`. The field is created or overwritten either way. |
| `GET <record> <field>` | The field's value, or `""` if the record or the field does not exist. |
| `DELETE <record> <field>` | `"true"` if the field existed and was removed, otherwise `"false"`. When a record loses its last field it ceases to exist. |

### Rules

- Record IDs, field names and values match the shared identifier grammar.
  Values are opaque strings; `"0"` and `"00"` are different values.
- `SET` on an existing record never returns `"true"`, even when the field is new.
- `DELETE` of a missing record or missing field returns `"false"` and changes
  nothing.

### Worked example

```
SET    users alice  admin      -> "true"    (record created)
SET    users bob    viewer     -> "false"   (record existed)
GET    users alice             -> "admin"
GET    users carol             -> ""        (field missing)
GET    groups alice            -> ""        (record missing)
DELETE users alice             -> "true"
DELETE users alice             -> "false"
DELETE users bob               -> "true"    (record now gone)
SET    users bob    editor     -> "true"    (record re-created)
```

### Edge cases the group asserts

- Overwriting a field with the same value returns `"false"` and keeps one field.
- After deleting every field, `GET` returns `""` and a later `SET` returns `"true"`.
- `["GET", "users"]` (wrong arity) and `["FETCH", "users", "alice"]` (unknown
  operation) raise `ValueError`.

## Level 2 — Deterministic scans

### Operations

| Query | Returns |
| --- | --- |
| `SCAN <record>` | Every field of the record as `field(value)` entries, sorted by field name in ascending byte order, joined by `", "`. `""` if the record does not exist. |
| `SCAN_BY_PREFIX <record> <prefix>` | The same, restricted to fields whose name starts with `prefix`. `""` if the record does not exist or nothing matches. |

### Rules

- Ordering is byte-wise on the field name: `"B"` sorts before `"a"`, `"a"`
  before `"a1"`, `"a1"` before `"a10"`, `"a10"` before `"a2"`.
- `prefix` is a non-empty identifier; it matches field names only, never values.
- Scans never change state.

### Worked example

```
SET  cfg zeta   1
SET  cfg alpha  2
SET  cfg Alpha  3
SET  cfg alpha2 4
SCAN cfg                    -> "Alpha(3), alpha(2), alpha2(4), zeta(1)"
SCAN_BY_PREFIX cfg al       -> "alpha(2), alpha2(4)"
SCAN_BY_PREFIX cfg Z        -> ""
SCAN nothing                -> ""
```

### Edge cases the group asserts

- A record with a single field scans to exactly `field(value)` with no separator.
- Deleting fields changes later scans; a record emptied by `DELETE` scans to `""`.
- Values containing parentheses-like characters are impossible under the
  grammar, so `field(value)` is unambiguous.

## Level 3 — Expiry

Level 3 introduces timestamped variants. The timestamp is the first argument.
Timestamps are non-decreasing across the run.

### Operations

| Query | Returns |
| --- | --- |
| `SET_AT <ts> <record> <field> <value>` | As `SET`; the field never expires. |
| `SET_AT_WITH_TTL <ts> <record> <field> <value> <ttl>` | As `SET`; the field expires at `ts + ttl`. `ttl` is a positive integer number of seconds. |
| `GET_AT <ts> <record> <field>` | As `GET`, considering only fields live at `ts`. |
| `DELETE_AT <ts> <record> <field>` | As `DELETE`, considering only fields live at `ts`. |
| `SCAN_AT <ts> <record>` | As `SCAN`, over fields live at `ts`. |
| `SCAN_BY_PREFIX_AT <ts> <record> <prefix>` | As `SCAN_BY_PREFIX`, over fields live at `ts`. |

### Rules

- A field with expiry E is live for every query whose timestamp is strictly
  less than E, and absent (as if deleted) for every query whose timestamp is
  greater than or equal to E.
- Overwriting a field replaces its expiry: `SET_AT` makes it permanent,
  `SET_AT_WITH_TTL` sets a new expiry from the new timestamp.
- A record whose every field has expired does not exist: `SET_AT` on it
  returns `"true"`, scans return `""`.
- Expired fields never come back on their own.

### Worked example

```
SET_AT_WITH_TTL 1  s a 1 5     -> "true"     (a expires at 6)
SET_AT          2  s b 2       -> "false"
GET_AT          5  s a         -> "1"
GET_AT          6  s a         -> ""          (expired at 6)
SCAN_AT         6  s           -> "b(2)"
DELETE_AT       7  s a         -> "false"     (already expired)
SET_AT_WITH_TTL 8  s b 9 1     -> "false"     (b now expires at 9)
SCAN_AT         9  s           -> ""
SET_AT          9  s c 3       -> "true"      (record was empty)
```

### Edge cases the group asserts

- Expiry exactly at the query timestamp counts as expired.
- Two fields expiring at the same second both disappear together.
- Re-setting an expired field is a fresh field (returns `"true"` when the
  record had no other live fields).

## Level 4 — Snapshots and restoration

### Operations

| Query | Returns |
| --- | --- |
| `BACKUP <ts>` | The number of records with at least one live field at `ts`, as a decimal string (`"0"` when none). Stores a snapshot of every live field with its remaining lifetime (`expiry - ts`; permanent fields stay permanent). |
| `RESTORE <ts> <at>` | `"true"` if a backup taken at a timestamp less than or equal to `at` exists; the most recent such backup replaces the entire current state, and every restored field's expiry becomes `ts + remaining lifetime`. `"false"` (state unchanged) when no such backup exists. |

### Rules

- `at` is any non-negative integer; it need not equal a backup timestamp.
- Backups are never deleted during a run; restoring does not consume them.
- A restore discards records created after the chosen backup.
- Remaining lifetime is measured at backup time, so a field with 3 seconds left
  when backed up has 3 seconds left after restoration, counted from `ts`.

### Worked example

```
SET_AT_WITH_TTL 1  r x 1 10    -> "true"      (x expires at 11)
SET_AT          2  r y 2       -> "false"
BACKUP          5               -> "1"         (x has 6 s left, y permanent)
DELETE_AT       6  r y         -> "true"
SET_AT          7  q z 9       -> "true"
BACKUP          8               -> "2"
RESTORE         20 6            -> "true"      (backup at 5; x expires at 26)
SCAN_AT         20 r           -> "x(1), y(2)"
SCAN_AT         20 q           -> ""           (q did not exist at backup 5)
GET_AT          26 r x         -> ""           (expired again)
RESTORE         30 4            -> "false"     (no backup at or before 4)
```

### Edge cases the group asserts

- `BACKUP` with no live records returns `"0"` and a later `RESTORE` to it
  yields an empty store.
- `RESTORE` with `at` equal to a backup timestamp selects that backup.
- Two backups at the same timestamp: the later one in query order wins.
- After a restore, a `BACKUP` reflects the restored state, not the discarded one.

## Deterministic correctness contracts

- Output length equals input length for every well-formed run.
- Replaying the same query list twice yields identical outputs.
- Scans are the only ordered outputs; their order is fully specified.
- No operation depends on wall-clock time or on the order in which the
  implementation stores fields.
