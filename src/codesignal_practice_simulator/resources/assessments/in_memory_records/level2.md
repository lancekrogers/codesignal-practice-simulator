# In-Memory Records — Level 2: Deterministic scans

Keep every Level 1 operation working and add two read-only scans.

| Query | Result |
| --- | --- |
| `SCAN <record>` | Every field of the record as `field(value)` entries, sorted by field name in ascending byte order, joined by `", "` (comma and one space). `""` when the record does not exist. |
| `SCAN_BY_PREFIX <record> <prefix>` | The same, restricted to fields whose name starts with `prefix`. `""` when the record does not exist or no field matches. |

Rules:

- Sorting is byte-wise on the field name: `"B"` sorts before `"a"`, `"a"`
  before `"a1"`, `"a1"` before `"a10"`, and `"a10"` before `"a2"`.
- `prefix` is a non-empty identifier and matches field names only, never values.
- A record with a single field scans to exactly `field(value)`.
- Scans never change state.

Example:

```
SET  cfg zeta   1
SET  cfg alpha  2
SET  cfg Alpha  3
SET  cfg alpha2 4
SCAN cfg                 -> "Alpha(3), alpha(2), alpha2(4), zeta(1)"
SCAN_BY_PREFIX cfg al    -> "alpha(2), alpha2(4)"
SCAN_BY_PREFIX cfg Z     -> ""
SCAN nothing             -> ""
```
