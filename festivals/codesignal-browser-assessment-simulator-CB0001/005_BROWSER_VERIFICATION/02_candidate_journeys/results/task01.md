# Task 01 — entry, editor, and recovery

Primary implementation: Cursor Terra High, followed by Cursor Sol High for
focused review corrections. Independent initial review: Cursor Luna High.
See `task01-review.md`, the task's evidence table, and
`regression-checkpoint.md` for exact assertion mapping and canonical checks.

Added five synthetic real-browser tests: pre-start durations and all first-party
rules; Python syntax, automatic brackets and saved four-space indentation;
independent history content/hash/timestamp chain; saved source and exact identity
after refresh; and saved source/identity/deadline after actual server restart.
Existing source-save/editor/navigation/settings tests cover conflict reload/copy,
history preview/restore/reset, four levels/tabs, and settings preservation.

## Coordinator correction of a flaky assertion

The agent reported 26 passing focused tests, but the coordinator's immediate
five-test rerun failed the editor case (4 passed). An isolated loopback-only
diagnostic demonstrated that zero-delay script input can reach bracket handling
before Monaco tokenization is ready. Paced input produced the pair, syntax
colors and saved indentation were correct in both cases. The installed Monaco
auto-closing implementation deliberately declines when the line is not cheap to
tokenize. No custom editor behavior or dependency change was added.

The test now waits for the preceding Python line's computed token colors and
the rendered target line before typing the opening bracket. It still requires
the automatic closing bracket and independently checks the saved indented
source. No arbitrary sleep, reporter override, or assertion removal was used.

Verification: `npm --prefix webui run test:browser --
tests/candidate_journey.spec.mjs --repeat-each=3` (result recorded below).
Result: 15 passed, exit 0, with default privacy-safe reporters.
The diagnostic browser instances and owned workspaces were cleaned up; one
early diagnostic setup failure left an owned temporary fixture, subsequently
moved to Trash. No raw diagnostics or candidate data are retained as evidence.
