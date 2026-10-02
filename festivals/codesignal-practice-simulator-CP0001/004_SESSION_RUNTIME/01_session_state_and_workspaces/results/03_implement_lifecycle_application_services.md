# 004.01.03 — Implement Lifecycle Application Services: verification evidence

Working directory: `/workspace/campaign/projects/codesignal-practice-simulator`

All commands below exited with code `0`.

```text
$ python3 -m unittest tests.test_lifecycle -v
test_corrupt_active_selection_fails_but_explicit_selection_still_works ... ok
test_expired_resume_and_test_are_exit_four_and_byte_identical ... ok
test_expiring_one_attempt_leaves_neighbor_bytes_unchanged ... ok
test_explicit_active_resume_replaces_selection ... ok
test_first_overdue_status_observer_persists_exactly_one_expiry ... ok
test_lock_contention_returns_exit_four_and_preserves_neighboring_attempt ... ok
test_next_command_recovers_a_missing_event_for_the_current_revision ... ok
test_overdue_submit_persists_expiry_before_one_submission ... ok
test_record_test_result_updates_active_state_under_one_revision ... ok
test_start_creates_selected_full_or_drill_attempt ... ok
test_status_and_time_before_deadline_are_safe_reads ... ok
test_submit_active_and_repeat_submit_returns_the_stored_result_without_writes ... ok
test_submit_finalizes_a_previously_expired_attempt_once ... ok
test_submitted_attempt_refuses_resume_and_test_without_mutation ... ok
test_test_runs_injected_scorer_then_records_result ... ok

----------------------------------------------------------------------
Ran 15 tests in 0.082s

OK
exit code: 0

$ python3 -m unittest discover -s tests -p 'test_lifecycle.py' -v
test_corrupt_active_selection_fails_but_explicit_selection_still_works ... ok
test_expired_resume_and_test_are_exit_four_and_byte_identical ... ok
test_expiring_one_attempt_leaves_neighbor_bytes_unchanged ... ok
test_explicit_active_resume_replaces_selection ... ok
test_first_overdue_status_observer_persists_exactly_one_expiry ... ok
test_lock_contention_returns_exit_four_and_preserves_neighboring_attempt ... ok
test_next_command_recovers_a_missing_event_for_the_current_revision ... ok
test_overdue_submit_persists_expiry_before_one_submission ... ok
test_record_test_result_updates_active_state_under_one_revision ... ok
test_start_creates_selected_full_or_drill_attempt ... ok
test_status_and_time_before_deadline_are_safe_reads ... ok
test_submit_active_and_repeat_submit_returns_the_stored_result_without_writes ... ok
test_submit_finalizes_a_previously_expired_attempt_once ... ok
test_submitted_attempt_refuses_resume_and_test_without_mutation ... ok
test_test_runs_injected_scorer_then_records_result ... ok

----------------------------------------------------------------------
Ran 15 tests in 0.080s

OK
exit code: 0

$ python3 -m unittest discover -s tests -v
----------------------------------------------------------------------
Ran 62 tests in 0.730s

OK
exit code: 0

$ /opt/homebrew/bin/python3.10 -m unittest discover -s tests -v
----------------------------------------------------------------------
Ran 62 tests in 0.744s

OK
exit code: 0

$ python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope tracked
Manifest verification passed: tracked
exit code: 0

$ python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope fixture-cache
Manifest verification passed: fixture-cache
exit code: 0

$ python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope git-boundary
Manifest verification passed: git-boundary
exit code: 0

$ .githooks/pre-commit
Manifest verification passed: git-boundary
exit code: 0

$ .githooks/pre-push
Manifest verification passed: git-boundary
exit code: 0

$ git diff --check
exit code: 0

$ git diff --cached --check
exit code: 0

$ git status --short
A  docs/cli-contract.md
A  src/codesignal_practice_simulator/clock.py
A  src/codesignal_practice_simulator/errors.py
A  src/codesignal_practice_simulator/filesystem.py
A  src/codesignal_practice_simulator/lifecycle.py
A  src/codesignal_practice_simulator/models.py
A  src/codesignal_practice_simulator/persistence.py
A  src/codesignal_practice_simulator/workspace.py
A  tests/test_lifecycle.py
A  tests/test_models.py
A  tests/test_persistence.py
A  tests/test_workspace.py
exit code: 0
```
