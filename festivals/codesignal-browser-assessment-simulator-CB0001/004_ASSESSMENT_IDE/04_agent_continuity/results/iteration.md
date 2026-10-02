# Iteration results

Date: 2026-09-09

## Testing findings copied from `testing.md`

No failed assertion, warning requiring application action, or missing evidence
was listed in `results/testing.md`. The Playwright `NO_COLOR`/`FORCE_COLOR`
message is runner-environment noise and requires no application change.

## Code-review findings copied from `review.md`

### Major

1. Evaluation snapshots could observe expiry after the prior derived refresh.
   - Fix: `_evaluation_snapshot_locked()` now refreshes derived status from the
     final `lifecycle.time()` observation before returning the snapshot.
   - Evidence: deterministic controlled-clock success and candidate-failure
     regressions both verify expired browser snapshot, `STATUS.md`, and CLI
     context surfaces.

### Minor

1. Derived refresh had nested best-effort exception guards.
   - Fix: retained both boundaries and documented that the renderer protects
     its filesystem/state failures while the application protects injected
     replacement services; the existing injected-renderer failure test remains
     green.
2. The browser continuity callback and fixture-server startup exceeded the
   focused-function guideline.
   - Fix: split the browser journey into focused lifecycle/coaching/terminal
     helpers and split fixture preparation, launch, and handle creation.
   - Evidence: all focused helpers and `startFixtureServer()` are under 50
     lines; authored continuity files remain under 500 lines.
3. Completed task bookkeeping retained unchecked verified boxes.
   - Fix: checked the verified Requirements and Done When boxes in tasks 01–03;
     no task status or generated lifecycle state was manually changed.

### Test gaps

1. No controlled-clock deadline transition covered snapshot rendering.
   - Fix: added success and candidate-failure snapshot regressions near expiry.
2. Repeat submit only checked authoritative bytes.
   - Fix: repeat-submit checks now assert terminal `STATUS.md` and public CLI
     context are byte/value unchanged in Python and browser continuity tests.
3. Context safety lacked exact allowlisted key checks.
   - Fix: added exact top-level, assessment, lifecycle, score, level-score, and
     event key-set assertions.
4. Browser and Python isolation evidence was uneven.
   - Fix: retained the real isolated-scorer browser coaching sentinel journey
     and preserved the independent Python exclusion checks for source, copied
     tests, prompts, fixture cache, and reference content without adding
     protected data to production paths.

## Verification

- Focused Python continuity/rendering/application tests: 18 passed.
- Controlled-clock snapshot regressions: 2 passed.
- Focused browser continuity spec: 1 passed.
- Full Python suite: 275 passed, 1 skipped.
- `python3 -m compileall -q src tests`: passed.
- `npm run check`: passed.
- `npm run build`: passed.
- `npm run check-assets`: passed for 13 assets.
- Full browser suite: 95 passed.
- `git diff --check`: passed.

## Post-iteration review

The fresh Cursor reviewer found no remaining critical, major, or test-gap
issues. Its only minor finding was that `testing.md` retained the pre-iteration
Python count of 273 while two new expiry regressions raised the final count to
275. The report now records both the gate count and the final acceptance count.
