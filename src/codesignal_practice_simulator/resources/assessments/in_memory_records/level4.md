# In-Memory Records — Level 4: Snapshots and restoration

Keep every earlier operation working and add snapshots of the timestamped
store.

| Query | Result |
| --- | --- |
| `BACKUP <ts>` | The number of records with at least one live field at `ts`, as a decimal string (`"0"` when none). Stores a snapshot of every live field together with its remaining lifetime (`expiry - ts`; permanent fields stay permanent). |
| `RESTORE <ts> <at>` | `"true"` if a backup taken at a timestamp less than or equal to `at` exists. The most recent such backup replaces the entire current state, and every restored field's expiry becomes `ts + remaining lifetime`. `"false"` (state unchanged) when no such backup exists. |

Rules:

- `at` is any non-negative integer; it does not have to equal a backup's
  timestamp.
- Backups are never deleted during a run, and restoring does not consume them.
- Restoring discards records created after the chosen backup.
- When two backups share a timestamp, the later one in query order wins.
- Remaining lifetime is measured at backup time: a field with 3 seconds left
  when backed up has 3 seconds left after restoration, counted from `ts`.

Example:

```
SET_AT_WITH_TTL 1  r x 1 10  -> "true"   (x expires at 11)
SET_AT          2  r y 2     -> "false"
BACKUP          5            -> "1"      (x has 6 s left, y permanent)
DELETE_AT       6  r y       -> "true"
SET_AT          7  q z 9     -> "true"
BACKUP          8            -> "2"
RESTORE         20 6         -> "true"   (backup at 5; x now expires at 26)
SCAN_AT         20 r         -> "x(1), y(2)"
SCAN_AT         20 q         -> ""       (q did not exist at that backup)
GET_AT          26 r x       -> ""       (expired again)
RESTORE         30 4         -> "false"  (no backup at or before 4)
```
