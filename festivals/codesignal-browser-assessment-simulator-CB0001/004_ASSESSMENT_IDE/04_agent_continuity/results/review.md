# Code review results

Date: 2026-09-09

## Review execution

- Reviewer: fresh Cursor Agent CLI session
- Model: `gpt-5.6-luna-high`
- Mode: read-only `ask`
- Reviewed base: project commit `56c6ac8`
- Reviewed scope: complete uncommitted agent-continuity sequence diff plus surrounding application, lifecycle, rendering, web, CLI, documentation, and test code.
- Verdict: request changes; no critical findings.

## Findings

### Critical

None. No production command/file/coaching endpoint was introduced. Context rendering remains an explicit allowlist of session, score, events, and legal commands; generated status writes remain attempt-locked; and the documentation states the same-user limitation.

### Major

1. A browser evaluation snapshot can cross its deadline during `_evaluation_snapshot_locked()`. `_test_locked()` refreshes status after scoring, but the later `lifecycle.time()` call can persist expiry. The browser may therefore receive `expired` while `STATUS.md` still reports `active`; the candidate-failure snapshot has the same second-observation pattern.
   - Disposition: accepted. Refresh derived status from the final observed snapshot state and add a controlled deadline-transition regression.

### Minor

1. Derived refresh errors are swallowed both by `DerivedStatusService.refresh()` and the application wrapper, without distinguishing unavailable/corrupt state from renderer failure.
   - Disposition: review during iteration. Preserve the required best-effort outcome boundary; simplify or document the outer guard if it remains necessary for injected/replacement services.
2. The new browser continuity test callback and the modified `startFixtureServer()` exceed the 50-line function guideline.
   - Disposition: accepted. Extract focused helpers while retaining the separate under-500-line controls module.
3. Completed task files retain unchecked requirement/Done When boxes.
   - Disposition: accepted as sequence bookkeeping; reconcile the completed task checkboxes with the verified evidence.

### Test gaps

1. Continuity tests do not advance the controlled clock across expiry, so they cannot catch the stale-status race.
   - Disposition: accepted; add a deterministic final-observation expiry case.
2. Repeat submit verifies authoritative bytes but does not recheck `STATUS.md` and CLI context.
   - Disposition: accepted; assert terminal derived surfaces remain identical after the idempotent repeat.
3. Context safety tests assert selected values and forbidden strings but not exact top-level/nested allowlisted key sets.
   - Disposition: accepted; add exact schema-key assertions.
4. Python continuity uses the fixed fixture scorer, while the browser continuity test uses the real scorer but only the coaching sentinel.
   - Disposition: covered jointly but strengthen evidence during iteration where practical: keep the real-scorer coaching isolation journey and the independent source/test/prompt/cache/reference exclusions, without coupling protected sentinels into real scorer output.

## Confirmed strengths

- Web lifecycle actions go through `RuntimeApplication`; handlers do not open `STATUS.md`.
- Candidate-failing web tests now refresh the persisted score/event surface.
- Derived rendering failure cannot turn an authoritative success into a transport failure.
- Candidate coaching remains outside production source, scoring, API, and final-result paths.
- Same-user process limitations and explicit source/history permission are stated consistently.
- The full recorded matrix is green: 273 Python tests (1 skip), legacy checks, 95 browser tests, build, compile, and asset verification.
