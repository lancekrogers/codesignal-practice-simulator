# 006.02.01 Verification Evidence

Date: 2026-09-08

## Required command

Working directory: `/workspace/campaign/projects/codesignal-practice-simulator`

```text
test_full_console_and_drill_module_complete_lifecycles (tests.test_end_to_end.EndToEndTests.test_full_console_and_drill_module_complete_lifecycles) ... ok
test_persisted_expiry_is_deterministic_and_submission_is_final_once (tests.test_end_to_end.EndToEndTests.test_persisted_expiry_is_deterministic_and_submission_is_final_once) ... ok
test_scorer_uses_the_exact_isolated_argv_and_rejects_external_imports (tests.test_end_to_end.EndToEndTests.test_scorer_uses_the_exact_isolated_argv_and_rejects_external_imports) ... ok
test_selection_jsonl_tail_lock_and_candidate_failure_paths (tests.test_end_to_end.EndToEndTests.test_selection_jsonl_tail_lock_and_candidate_failure_paths) ... ok

----------------------------------------------------------------------
Ran 4 tests in 15.412s

OK
MM README.md
M  justfiles/verify.just
AM tests/test_end_to_end.py
M  tests/test_scoring.py
EXIT_CODES e2e=0 ignored_status=0 diff_check=0 git_status=0
```

`git status --ignored --short attempts` produced no entries. `git diff --check`
also produced no output. The listed worktree changes are the scoped task changes.

## Additional compatibility verification

- `.venv/bin/python -m unittest discover -s tests -v`: 154 tests passed.
- `python3 -m unittest discover -s tests -v`: 154 tests passed.
- Cursor release judge: `APPROVE`; blockers: none.

The E2E suite uses a copied project, a fresh Python 3.10/3.11 virtual
environment, `pip --no-index --no-deps --no-build-isolation`, and the generated
`codesignal-sim` entry point. It covers console/module × full/drill, fixture
fetching from a synthetic seven-file source, lifecycle and failure paths,
checkout/cache/cwd isolation, exact scorer argv, and import sentinels.
