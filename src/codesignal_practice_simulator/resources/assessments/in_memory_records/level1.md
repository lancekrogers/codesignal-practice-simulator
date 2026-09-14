# In-Memory Records — Level 1: Records and fields

Implement `simulate(queries)` in `simulation.py`. `queries` is a list of
queries; each query is a list of strings whose first element is the operation
name. Return a list with exactly one output string per query, in order.

Level 1 introduces a record store. A record is identified by a record ID and
holds named string fields. Identifiers and values match `[A-Za-z0-9_.-]{1,64}`.

| Query | Result |
| --- | --- |
| `SET <record> <field> <value>` | `"true"` if this call created the record (it did not exist before), otherwise `"false"`. The field is created or overwritten either way. |
| `GET <record> <field>` | The field's value, or `""` when the record or the field does not exist. |
| `DELETE <record> <field>` | `"true"` if the field existed and was removed, otherwise `"false"`. A record that loses its last field ceases to exist. |

Rules:

- `SET` on an existing record returns `"false"` even when the field is new.
- Deleting a missing record or a missing field returns `"false"` and changes
  nothing.
- Values are opaque strings: `"0"` and `"00"` are different values.
- An unknown operation name, or an operation with the wrong number of
  arguments, must raise `ValueError`. Well-formed queries never raise.

Example:

```
SET    users alice  admin   -> "true"
SET    users bob    viewer  -> "false"
GET    users alice          -> "admin"
GET    users carol          -> ""
GET    groups alice         -> ""
DELETE users alice          -> "true"
DELETE users alice          -> "false"
DELETE users bob            -> "true"
SET    users bob    editor  -> "true"
```

Your implementation must be deterministic: the same query list always yields
the same output list, independent of wall-clock time or environment.
