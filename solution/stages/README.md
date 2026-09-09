# Simple staged solutions

These are four independent, cumulative answers to the assessment. Each file
can be pasted into CodeSignal as `simulation.py` for the matching level.
They are snapshots of one evolving program, not four programs a candidate
would type from scratch. The final Level 4 answer is 100 lines total.

| File | What changes at this level |
| --- | --- |
| `level1.py` | Use one dictionary for upload, get, and copy. |
| `level2.py` | Convert the supplied `"200kb"` sizes to integers and sort. |
| `level3.py` | Store `(size, expiration)` tuples and add one liveness check. |
| `level4.py` | Save dictionary snapshots and restore the latest valid one. |

The code deliberately favors what is easy to write and explain in a live
assessment:

- one public function, matching the provided starter;
- plain dictionaries, tuples, and lists;
- direct `if`/`elif` command handling;
- a linear scan for search, because the prompt gives no scale requirement;
- the exact `"<integer>kb"` size format shown by the supplied tests;
- chronological timestamped operations, as shown by the assessment.

Level 4 snapshots the whole dictionary after each write. That uses more memory
than a production design, but it is the shortest reliable solution under an
interview clock. If the interviewer supplies scale constraints, that is the
point to discuss a change log instead.

Run all staged checks from the assessment root with:

```bash
just test-stages
```

Level 4 implements the written rollback requirement. The vendor's bundled
Level 4 assertion expects rollback to do nothing, so it intentionally does not
match that one contradictory assertion. See
[`../../notes/level4-rollback-discrepancy.md`](../../notes/level4-rollback-discrepancy.md).
