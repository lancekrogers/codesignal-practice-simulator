> **Deprecated historical archive — do not use as instructions.**
>
> This preserves the pre-CLI document for provenance, historical layout, and
> compatibility context. Its scripts, timestamp-named attempts, and Just
> commands are retired and unsupported. For a timed attempt, use the supported
> [CLI workflow](../../README.md#practice) and
> [canonical CLI contract](../cli-contract.md).

# CodeSignal Industry Coding Framework — file_storage

A solved copy of the Industry Coding Framework practice assessment, plus a
harness that runs it the way the real thing runs: 90 minutes, four levels in
order, partial credit for each level you finish.

The format matters because it is the one large companies use in place of
timed DSA puzzles — a single stateful service you extend four times, where the
grade is how far you got before the clock ran out. Having the harness sitting
here means a "you have a CodeSignal on Thursday" email costs a practice run,
not a setup afternoon.

## Quick start

```bash
just setup          # one-time: .venv with the assessment's numpy/sortedcontainers
just practice       # start a 90-minute attempt, copied from the untouched assessment
just task 1         # read the level-1 task
# ...edit attempts/<timestamp>/simulation.py...
just level 1        # score one level
just score          # score all four
just time           # clock check
just submit         # stop, score, write RESULT.md into the attempt
```

`just` on its own lists every recipe.

If you are studying the progression before doing a timed run, start with the
[simple staged solutions](solution/stages/README.md). They show the complete
program after each level without introducing production-style architecture.
For an active recall session, use the separate
[hand-coding study drill](study/README.md), which includes a blank starter and
a checker that can grade your own scratch file one level at a time.

## Layout

| Path | What it is |
| ---- | ---------- |
| `assessment/file_storage/` | The task verbatim: `level{1..4}.md`, the blank `simulation.py`, the bundled `test_simulation.py`. Never edited. |
| `assessment/vendor-readme.md` | Upstream README (timing table, framework notes). |
| `solution/stages/level{1..4}.py` | Simple cumulative answers, one complete Python program per level. |
| `solution/simulation.py` | Fully factored reference solution, levels 1–4, standard library only. |
| `solution/test_simulation.py` | The bundled tests, verbatim — 4/4 pass. |
| `solution/test_spec.py` | 26 tests for what the level docs actually say, including the edges the bundled tests skip. |
| `solution/test_stages.py` | Focused checks proving each simple stage works without later-level code. |
| `scripts/` | `new_attempt.py` (start the clock), `scorecard.py` (level-by-level scoring). |
| `attempts/` | One directory per timed run: your code, `attempt.json`, `RESULT.md`. |
| `notes/` | The level-by-level walkthrough and the level-4 finding. |

Verify the reference solution at any time:

```bash
just test-all       # bundled, spec-accurate, and staged tests
just score-solution # the same scorecard the practice runs use: 4/4
just test-stages    # independently verify the four simple staged programs
```

## Two things worth knowing before a timed run

**The bundled level-4 test contradicts the level-4 spec.** `level4.md` says
`ROLLBACK` restores the state at a timestamp; the shipped `test_group_4`
asserts output that only holds if rollback changes nothing at all. Both
readings are implemented and tested — see
[notes/level4-rollback-discrepancy.md](notes/level4-rollback-discrepancy.md).
In a real assessment the hidden tests are the spec, so implement the real
rollback and keep it behind one switch if the visible tests disagree.

**The output strings are the contract.** Every operation returns a log line
(`"uploaded Cars.txt"`, `"found [Baz.pdf, Bar.csv]"`, `"file not found"`), so a
correct data structure with the wrong string still fails. Read the assertions
in `test_simulation.py` before writing anything.

The full level-by-level breakdown — what each level demands, which refactor it
forces, and where the time goes — is in
[notes/walkthrough.md](notes/walkthrough.md).

## Provenance

Vendored from [`PaulLockett/CodeSignal_Practice_Industry_Coding_Framework`](https://github.com/PaulLockett/CodeSignal_Practice_Industry_Coding_Framework)
at commit `6aab304`, via the `exrepos` pin
(`ai_docs/example-repos/examples/CodeSignal_Practice_Industry_Coding_Framework`).
The assessment files here are byte-identical copies; everything under
`solution/`, `scripts/`, `notes/`, and the justfiles is new work.

Upstream targets Python 3.10.6 (CodeSignal's runtime). The reference solution
is standard library only and runs on anything 3.10+; the blank starter imports
`numpy` and `sortedcontainers`, which is what `just setup` installs.
