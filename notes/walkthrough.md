# Walkthrough: file_storage, level by level

How the reference solution in `solution/simulation.py` was built, one level at
a time, and what each level costs you if you build it the obvious way.

The framework's whole design is that level N+1 punishes a shortcut you took in
level N. Levels are scored independently, so a partial answer is worth real
points — but a level-1 shortcut you have to unwind at level 3 is what actually
eats the 90 minutes.

## Level 1 — upload, get, copy (10–15 min)

Three operations over a name → file mapping.

```python
FILE_UPLOAD(file_name, size)   # duplicate name -> runtime exception
FILE_GET(file_name)            # size, or nothing
FILE_COPY(source, dest)        # missing source -> exception; existing dest -> overwrite
```

The only trap is asymmetry: a duplicate *upload* raises, but a copy onto an
existing destination overwrites silently. Two different rules for "the name is
taken", and the tests check both.

Decisions that pay off later:

- **Store a record, not a bare size.** `StoredFile` starts as name + size and
  grows a `created_at` and `expires_at` at level 3. A `dict[str, str]` forces a
  rewrite of every operation instead.
- **Keep the raw size string.** `FILE_GET` returns what was uploaded
  (`"200kb"`), while ordering needs bytes. Keeping both from the start avoids
  formatting a number back into a string later.

## Level 2 — search (20–30 min)

```python
FILE_SEARCH(prefix)  # top 10, size descending, ties broken by name
```

Sizes arrive as `"100kb"`, `"200kb"`, `"300kb"` — strings. Sorting them as
strings passes the bundled test by luck (same unit, same digit count) and fails
the moment a `"9kb"` meets a `"10mb"`. Parse once at upload:

```python
_SIZE_UNITS = {"b": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3, "tb": 1024**4}
```

The whole level is then one line, and the tiebreak makes results deterministic:

```python
matches.sort(key=lambda stored: (-stored.size, stored.name))
return [stored.name for stored in matches[:SEARCH_LIMIT]]
```

`-stored.size` with an ascending name is the standard trick for "descending by
one key, ascending by another" without two passes.

A linear scan over every file is correct here. Prefix search over a big store
wants a trie or a sorted-key structure (`sortedcontainers` is preinstalled for
exactly this hint), but nothing in the assessment makes the scan too slow, and
the levels are timed. Say the trade out loud in a live round; don't build it.

## Level 3 — the `_AT` variants and TTLs (30–60 min)

> "Implement extensions of existing methods which inherit all functionality but
> also with an additional parameter to include a timestamp."

The word to notice is *inherit*. Nothing here says write eight methods. Make
the timestamped versions the real implementation and let the level-1/2 methods
delegate with no clock:

```python
def upload(self, file_name, size):
    self.upload_at(None, file_name, size)
```

`None` means "no clock", and `alive_at(None)` is always true, so untimed
operations keep working untouched. This is the level's actual test: whether you
refactor or duplicate.

TTL is an absolute expiry computed once at upload, never a countdown:

```python
expires_at = op.at + timedelta(seconds=int(ttl))   # ttl is None -> lives forever
```

Then liveness is a comparison, and the half-open interval is the choice to make
explicitly — a file uploaded at 12:00:00 with `ttl=1` is gone at 12:00:01, not
at 12:00:02:

```python
return when < self.expires_at
```

Three consequences fall out, all covered in `test_spec.py`:

- An expired file is invisible to `get`, `search`, and `copy` — `copy_at` from
  an expired source raises, same as a missing one.
- An expired name can be re-uploaded. It is not a duplicate; the old file is
  gone.
- A copy inherits the source's *expiry*, not a fresh TTL. It dies when the
  original would have. (The spec is silent here; state the assumption.)

Nothing is eagerly evicted. Lazy liveness checks are less code, and level 4
needs the history anyway.

## Level 4 — rollback (30–60 min)

```python
ROLLBACK(timestamp)  # restore the state at timestamp; recalculate all ttls
```

Journal every mutation, then rebuild by replaying the ones at or before the
target:

```python
replayable = [op for op in self._journal if op.at is None or op.at <= target]
self._files, self._journal = {}, []
for op in replayable:
    self._record(op)
```

Why replay beats snapshots: a snapshot forces you to pick a granularity and
copy the whole map per tick, and you still have to fix up TTLs by hand. Replay
derives any past state from operations you already have, and TTLs come out
right by construction because each file is rebuilt from its original upload
time.

Two details make the replay safe:

- **Validation lives in the public methods, mutation in `_apply`.** A replayed
  upload must not raise "file already exists" against a store that is being
  rebuilt from empty.
- **Untimed operations (`at is None`) always survive.** They have no position
  on the clock, so no timestamp can roll them away.

Ordering at the boundary: an operation stamped exactly at the target is kept
(`op.at <= target`) — "the state at 12:10" includes what happened at 12:10.

Then read `notes/level4-rollback-discrepancy.md`, because the bundled test for
this level expects the opposite of the spec.

## Where the time goes

| Level | Budget | Real cost |
| ----- | ------ | --------- |
| 1 | 10–15m | Fast if you write a record type; slow if you rewrite it at level 3. |
| 2 | 20–30m | Ten minutes, unless you skipped size parsing. |
| 3 | 30–60m | The refactor. Delegating the untimed methods is most of it. |
| 4 | 30–60m | Twenty minutes with a journal, an unbounded rewrite without one. |

Budgets total 90–165 minutes against a 90-minute clock. That is intentional:
the grade is how far you got, so bank each level with passing tests before
starting the next one, and never leave level N broken to start level N+1.

Run `just score` often. It is the same partial-credit view the real assessment
gives you, and it tells you whether a level-3 refactor quietly broke level 1.
