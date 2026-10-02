# Code review results

Date: 2026-09-09

## Review execution

- Reviewer: fresh Cursor Agent CLI session
- Model: `gpt-5.6-luna-high`
- Mode: read-only `ask`
- Reviewed base: project commit `937c9a867c5bf12c743780c51e46a70d9c51b784`
- Reviewed scope: the complete uncommitted sequence diff, including untracked source/spec modules and generated assets.
- Command form: `cursor-agent -p --mode ask --trust --model gpt-5.6-luna-high --output-format text` with the sequence goal, security/isolation checks, maintainability criteria, and file/function limits in the prompt.
- Verdict: request changes; no critical findings.

## Accepted findings

### Major

1. Active level-status markers do not rerender after Run Tests updates the score. The output is current, but navigation can retain old `not run` outcomes. Add an explicit navigation refresh API and browser assertion after a real test response.
2. Confirmation dialogs have visible headings/descriptions but no `aria-labelledby` or `aria-describedby`, leaving them unnamed to assistive technology. Add stable IDs/relationships and accessible assertions for submit, reset, and restore.
3. Monaco worker failure during an in-flight save calls `source.change(currentValue)` again, which can queue a duplicate PUT/history snapshot before the controller locks. Preserve the buffer and settle the existing save without enqueuing identical content.
4. `web/v1` now requires `practice` on scored evaluation responses without changing the schema version. Preserve backward compatibility by safely deriving score-only practice evidence when the field is absent, while continuing to reject malformed present data.
5. Countdown recovery remains clamped at zero after an authoritative resync reports the session still active with remaining time. Re-anchor and reset the displayed value on a fresh authoritative active snapshot without permitting ordinary ticks to increase it.

### Minor

1. `practice_result_from_runs()` accepts scorer runs and immediately discards them; `MAX_BROWSER_OUTPUT_BYTES` is therefore unused. Simplify the API to derive fixed safe evidence directly from `ScoreSummary` and remove the misleading diagnostics plumbing.
2. `application.py` and `editor.ts` remain under the 500-line limit but are close to it. Treat further growth as an extraction trigger.

### Test gaps

1. Four split suites call the now-async offline policy assertion without `await`, allowing unobserved teardown failures: `source_save`, `shell_lifecycle`, `shell_layout`, and `source_terminal`.
2. Add a browser assertion that active level markers change after an actual Run Tests response.
3. Add a real fixture-server clock-expiry browser journey rather than relying only on intercepted `/api/time` responses.
4. Add a lost/canceled submit-response recovery journey that retries and proves the stored result is returned without rescoring.
5. Exercise candidate failure and scorer error through the real backend scorer path, not only synthetic score objects or rewritten browser responses.

## Positive review conclusions

- CAS source recovery and shared-operation locking are structurally sound.
- Normal repeat submit returns stored results without rescoring.
- Backend session timing remains authoritative.
- Fixed browser evidence excludes raw scorer diagnostics and candidate-external content.
- Generated asset hashes are internally consistent.
- No FETCH_ONLY/reference bytes, secrets, or obvious local-only security regressions were found.
- The split browser modules remain discoverable and preserved the deleted monolithic test coverage.

## Disposition

All major and test-gap findings are accepted for task 08 iteration. The minor diagnostics API cleanup is also accepted because it removes misleading complexity. Near-limit module sizes are recorded as a constraint rather than requiring unrelated extraction in this sequence.
