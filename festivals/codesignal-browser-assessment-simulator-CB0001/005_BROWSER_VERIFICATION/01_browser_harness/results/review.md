# Independent browser-harness review — 2026-09-10

Reviewer: fresh Cursor CLI session, `gpt-5.6-luna-high`.

Command: `cursor-agent -p --mode ask --trust --model gpt-5.6-luna-high`
with a prompt requiring inspection of the complete uncommitted diff and
untracked harness files against `0ccdf6a`, surrounding code, sequence goal,
correctness, maintainability, compatibility, security, content isolation,
deterministic cleanup, and privacy-safe artifacts. No reviewer edits.

## Findings and disposition

1. **Major: cleanup failure is not surfaced.** `failure_artifacts_reporter.mjs`
   ignores a false result from descriptor-relative cleanup of a tainted output
   root. Raw failure artifacts could remain without a reported cleanup error.
   Accepted for correction and negative-path verification before commit.
2. **Minor: fixture preparation can leak its temporary directory.** The initial
   clock write can fail after allocation but before the caller owns cleanup.
   Accepted for correction and focused regression coverage.
3. **Packaged-run gap:** `scripts/run_packaged_browser.py` overrides the configured
   sanitizing reporters with `--reporter=line`. Accepted for correction now;
   complete installed-wheel proof belongs to sequence 03.
4. **Minor: module size.** `network_guard.mjs` and `failure_artifacts.mjs` exceed
   the festival's 500-line guideline. Documented exception: preserve the existing
   tested policy implementation while correcting concrete defects. The modules
   are confined to test infrastructure, with network policy and artifact
   sanitization separated from fixture lifecycle and page helpers. A broad
   repartition solely to meet a line count would expand the reviewed change and
   retesting without changing a candidate outcome. Tradeoff: these modules take
   longer to review; focused exported functions and negative tests remain the
   maintenance boundary. No requirement or exclusion is relaxed.
5. **Optional: black failure screenshots.** Keep the existing fail-closed
   behavior. Dimensions and sanitized action timelines are retained; screenshots
   intentionally provide no candidate-bearing pixels. They are not visual
   fidelity evidence.
6. **Installed CLI provenance concern:** continuity controls prepend checkout
   source even in installed mode. Accepted as a distribution verification gap
   for sequence 03; a wheel run must prove CLI and server origins separately.

The reviewer found no additional concrete FETCH_ONLY or candidate-content leak:
fixtures are synthetic, response scans bounded, and trace/text sanitizers discard
candidate-bearing fields. This rationale does not waive the cleanup finding.

## Coordinator finding

`EditorPage.applySettings()` calls `check()` for both true and false requested
values. Accepted: use the checkbox API that honors the requested value and prove
that disabling a default-enabled preference survives reload in the existing
settings test. Cursor Terra High owns this correction.

Fresh baseline checks now supersede the reviewer's older 101-test report:
144 browser tests pass and `just verify` passes. Final fix and re-review evidence
will be recorded in `iteration.md`.

## Focused correction review and later reproducer

A second fresh Luna High read-only session found no defect in the four scoped
corrections. Its claim that a coordinator CLI probe proved cleanup failure was
premature: the instrumented probe subsequently showed root initialization failed
before the intended condition. That review is not evidence for first-run safety.

The coordinator then reproduced a separate major defect using a fresh output
directory: `onBegin` could not open the nonexistent root and silently skipped
sanitizing its later files. Raw synthetic sentinel bytes remained in three files.
The harness failure probe applied an extra sanitizer after the runner exited,
masking this defect. Accepted for immediate correction by Cursor Sol High; fresh
execution and review are required. See `iteration.md`.

## Final startup review

The subsequent Luna High review accepted first-run sanitation and the actual CLI
cleanup-failure proof, but identified swallowed startup exceptions as a remaining
raw-artifact risk. Cursor Terra High corrected this with synchronous safe
diagnostics and immediate process termination after closing acquired roots.

A final fresh `cursor-agent -p --mode ask --trust --model gpt-5.6-luna-medium`
review inspected only this final startup correction and its direct/subprocess
tests. It found no remaining defect in that scope: default construction uses the
fatal terminator, injection is explicit in direct unit tests, acquired descriptors
close before exit, and the subprocess assertion checks exit 1 and unchanged
symlink-target contents. This is not a release review of the whole festival.

All accepted harness review findings are addressed. The installed-CLI provenance
and full distribution evidence remain explicitly assigned to sequence 03.
