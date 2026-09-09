# File storage interview drill

This is a post-attempt study track, not a timed simulator. It treats the
exercise as one program that grows four times, not as a system to architect up
front. Do not use its staged answers or explanations during a timed attempt.

## Use it today

Do not memorize the finished Level 4 file. Practice making the next small
change while keeping the previous tests green.

1. Copy `starter.py` to `scratch.py`.
2. Choose one staged checkpoint and write it without looking at that answer.
3. Run `python check.py 1 scratch.py` (or levels 2 through 4).
4. Compare with `level1.py`, fix your version, then continue to the next level.
5. Delete `scratch.py` and do one more run from memory.

From the repository root, the matching post-attempt helper is:

```bash
just study-check 1 scratch.py
```

Use the project virtual environment if `python` is unavailable:

```bash
../.venv/bin/python check.py 1 scratch.py
```

The checked-in answers can be verified with:

```bash
../.venv/bin/python check.py 1 level1.py
../.venv/bin/python check.py 2 level2.py
../.venv/bin/python check.py 3 level3.py
../.venv/bin/python check.py 4 level4.py
```

## What you need to remember

### Level 1

- A dictionary gives fast lookup by file name.
- Upload rejects an existing key.
- Copy rejects a missing source but overwrites the destination.
- Output strings must exactly match the tests.

### Level 2

- Convert `"200kb"` with `int(size[:-2])` so sorting is numeric.
- Filter with `name.startswith(prefix)`.
- Sort with `key=lambda name: (-files[name], name)`.
- Return only `matches[:10]`.

### Level 3

- Change each value from `size` to `(size, expiration)`.
- `None` means the file never expires.
- A file is alive while `now < expiration`.
- A copy keeps the source's expiration time.

### Level 4

- After each timestamped write, save `(timestamp, files.copy())`.
- On rollback, keep snapshots through the target and restore the last one.
- A shallow copy is sufficient because the dictionary values are immutable
  tuples.

This snapshot approach is not the most memory-efficient production design. It
is a reasonable interview solution when the prompt gives no scale constraint:
it is short, easy to verify, and easy to explain. Mention the memory tradeoff
if the interviewer asks.

## Suggested two-hour schedule

| Time | Work |
| --- | --- |
| 0:00–0:20 | Write and test Level 1. |
| 0:20–0:45 | Extend it through Level 2. |
| 0:45–1:25 | Add timestamps and TTL for Level 3. |
| 1:25–1:50 | Add snapshot rollback for Level 4. |
| 1:50–2:00 | Review mistakes and exact output strings. |

If you run short on time in the real assessment, submit a passing level before
starting the next one. Partial credit is the point of this format.

## Level 4 warning

The supplied Level 4 test expects rollback to do nothing, which contradicts
the written prompt. `level4.py` and `check.py` follow the written requirement:
files created after the rollback timestamp disappear.
