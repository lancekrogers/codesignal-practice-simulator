# Harness iteration — 2026-09-10

Primary corrections were implemented by two bounded Cursor CLI sessions using
`gpt-5.6-terra-high`. Coordinator inspected their actual changes.

## Accepted corrections

- Cleanup: tainted-output cleanup failure now prints a fixed content-free message
  and returns `{ status: "failed" }`; owned descriptors close in `finally`.
  The regression forces descriptor cleanup failure, checks the status and
  diagnostic, and confirms the other root descriptor closes.
- Fixture preparation: the allocated workspace is removed if the initial clock
  write rejects. A malformed synthetic clock value exercises that path.
- Packaged execution: removed `--reporter=line`; installed runs retain the
  configured sanitizers while using their own temporary output root.
- Editor helper: false checkbox values use `setChecked(false)`. The existing
  settings persistence journey disables auto-close brackets and verifies the
  persisted preference and unchecked control after reload.

## Verification

- Focused artifact/setup browser command: 27 passed.
  `npm --prefix webui run test:browser -- tests/failure_artifacts.spec.mjs tests/browser_harness_setup.spec.mjs`
- Editor-settings browser command: 9 passed.
  `npm --prefix webui run test:browser -- tests/editor_settings.spec.mjs`
- `npm --prefix webui run check`, `git diff --check`, and packaged-runner Python
  syntax validation passed.
- Correction to the preliminary CLI probe: exit 1 alone was insufficient proof.
  Instrumentation showed output-root opening failed before the intended cleanup
  failure was injected. The next probe must prove successful root acquisition
  and passing test-body execution before asserting cleanup failure status.
- The skipped archive test was rerun with an isolated temporary build environment:
  `python3 -m unittest tests.test_asset_verification.DistributionTests.test_built_archives_contain_only_valid_packaged_assets -v`
  with `ASSET_BUILDER` pointing at that environment. One test passed; wheel and
  sdist contents were verified. No project runtime dependency was added.

## Other review dispositions

- Large test-infrastructure modules: documented bounded exception in `review.md`;
  no candidate requirement is deferred.
- Black screenshots: retained as privacy-preserving dimension-only diagnostics,
  not visual fidelity evidence.
- Installed continuity CLI provenance: tracked for sequence 03, alongside complete
  wheel/offline/clean-clone evidence. This harness does not claim distribution
  completion.
- No actionable baseline test warning remains. The shell's `compdef` notice from
  Cursor startup is not an application or test failure.

## Additional confirmed first-run defect

A real Playwright CLI run with a brand-new output directory could not open its
root in reporter `onBegin`. The reporter silently skipped the root thereafter.
A synthetic failing test retained raw sentinel bytes in the attachment, original
output file, and `error-context.md`. The existing full-browser failure probe
masked this because it separately sanitized the output after the child exited.

Cursor Sol High is correcting root acquisition and failure-artifact handling,
and removing this post-hoc sanitation from the proof. Fresh first-run regression,
focused/full verification and independent re-review are required before commit.

### First-run correction delivered

- Cursor Sol High implemented descriptor-owned creation of missing output roots,
  checked directory identity on acquisition, and added a bounded final sanitation
  sweep for unreferenced originals and error-context files.
- Removed the second sanitizer from the subprocess failure proof. The test now
  reads the actual reporter's retained trace and text artifacts directly.
- Added an actual CLI cleanup-failure regression: it requires an acquired root,
  a passing test body, a fixed cleanup warning, and a nonzero process exit.
- Artifact tests passed 28/28; combined artifact/harness tests passed 46/46.
- Coordinator reproduced the original failing attachment case against the final
  implementation in a separate brand-new output directory. Root acquisition was
  confirmed, the deliberate failure exited 1, and a direct recursive sentinel
  scan found no raw sentinel in any retained file. No second sanitizer was used.

### Successful-run cleanup correction

- Cursor Luna Medium corrected `SuccessCleanlinessReporter` to inspect distinct
  `config.projects[].outputDir` values. The previous root-only lookup silently
  skipped real Playwright output directories.
- Its focused test exercises real residue in a second project directory, then
  verifies clean success. One isolated test passed; the final canonical run will
  recheck it with configured privacy-safe reporters.
- Coordinator additionally replaced filesystem-read errors with a fixed,
  content-free diagnostic and added an invalid-directory regression to the same
  test. This avoids exposing raw paths when cleanliness cannot be checked.

Final full browser run and independent review of these final changes are pending.

### Final gate findings

- Full browser run: 149 passed, one failed. The failure was the new success-checker
  test expecting an inner safe error message rather than the final wrapper's safe
  message. Corrected the assertion; the focused success-checker spec passed 1/1
  with configured privacy-safe reporters. No product behavior changed.
- Fresh Luna High review verified first-run sanitation, direct retained-file
  scanning, actual cleanup-failure process status, and project-output cleanliness.
  It identified one remaining acquisition-error path: Playwright catches reporter
  exceptions and still runs test bodies. With no acquired roots, raw files could
  remain. Cursor Terra High is implementing fatal startup before test execution
  and a real rejected-path subprocess regression. Ordinary throwing is not
  accepted as proof of aborting the runner.

### Fatal startup verified

Cursor Terra High added a synchronous fixed stderr diagnostic and immediate
exit 1 after closing acquired roots. Direct unit tests explicitly inject a
non-exiting terminator; the real subprocess uses the default fatal behavior.
The subprocess checks that no probe-body artifact exists and that symlink-target
data remains unchanged. It invokes the installed Playwright CLI deterministically.

- Focused artifact suite: 28 passed.
- Real startup-ownership subprocess regression: 1 passed.
- Metadata and whitespace checks: passed.
- Fresh Luna Medium review of the exact startup change: no remaining blocker.
- Coordinator JavaScript/Python syntax checks: passed.

The final canonical browser rerun passed **151/151** tests. Configured privacy-safe
reporters and the corrected success-cleanliness checker remained enabled.
Tracked/Git provenance and staged whitespace checks passed. No known harness
finding remains; the sequence is ready to commit.
