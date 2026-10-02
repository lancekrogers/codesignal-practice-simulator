# 005.02.02 command evidence

## Documented CLI workflow (managed temporary workspace)
Obtaining file:///workspace/campaign/projects/codesignal-practice-simulator
  Installing build dependencies: started
  Installing build dependencies: finished with status 'done'
  Checking if build backend supports build_editable: started
  Checking if build backend supports build_editable: finished with status 'done'
  Getting requirements to build editable: started
  Getting requirements to build editable: finished with status 'done'
  Preparing editable metadata (pyproject.toml): started
  Preparing editable metadata (pyproject.toml): finished with status 'done'
Building wheels for collected packages: codesignal-practice-simulator
  Building editable for codesignal-practice-simulator (pyproject.toml): started
  Building editable for codesignal-practice-simulator (pyproject.toml): finished with status 'done'
  Created wheel for codesignal-practice-simulator: filename=codesignal_practice_simulator-0.1.0-0.editable-py3-none-any.whl size=4480 sha256=4917926b1664f4b8a49761004993f67e3c1c88f20c67081e1ea0ca733bc52d1e
  Stored in directory: /tmp/build/pip-ephem-wheel-cache-ltpqwqo4/wheels/4d/6f/f8/0dcb998afb3c6ce1b4196cd4523993e15006219fb4fd3e916e
Successfully built codesignal-practice-simulator
Installing collected packages: codesignal-practice-simulator
Successfully installed codesignal-practice-simulator-0.1.0

[notice] A new release of pip is available: 26.1.2 -> 26.2.1
[notice] To update, run: /tmp/build/tmp.gyBHhFDFdb/venv/bin/python -m pip install --upgrade pip

$ /tmp/build/tmp.gyBHhFDFdb/venv/bin/codesignal-sim --help
usage: codesignal-sim [-h] [--version] COMMAND ...

CodeSignal Practice Simulator

positional arguments:
  COMMAND
    fetch     populate the ignored fixture cache
    start     create a new attempt
    resume    resume an active attempt
    status    show selected attempt status
    time      show selected attempt time
    test      score selected attempt
    submit    submit selected attempt
    context   show safe selected attempt context
    task      show a selected attempt task

options:
  -h, --help  show this help message and exit
  --version   show program's version number and exit
[exit: 0]

$ /tmp/build/tmp.gyBHhFDFdb/venv/bin/python -m codesignal_practice_simulator --help
usage: codesignal-sim [-h] [--version] COMMAND ...

CodeSignal Practice Simulator

positional arguments:
  COMMAND
    fetch     populate the ignored fixture cache
    start     create a new attempt
    resume    resume an active attempt
    status    show selected attempt status
    time      show selected attempt time
    test      score selected attempt
    submit    submit selected attempt
    context   show safe selected attempt context
    task      show a selected attempt task

options:
  -h, --help  show this help message and exit
  --version   show program's version number and exit
[exit: 0]

$ /tmp/build/tmp.gyBHhFDFdb/venv/bin/codesignal-sim fetch --workspace-root /tmp/build/tmp.5b9n6kOI9V --source /workspace/campaign/ai_docs/example-repos/examples/CodeSignal_Practice_Industry_Coding_Framework --json
{"ok": true, "result": {"fixture_cache": "/tmp/build/tmp.5b9n6kOI9V/.cache/codesignal-fixtures/6aab304"}, "schema_version": "cli/v1"}
[exit: 0]

$ /tmp/build/tmp.gyBHhFDFdb/venv/bin/codesignal-sim start --workspace-root /tmp/build/tmp.5b9n6kOI9V --json
{"ok": true, "result": {"session": {"assessment": {"assessment_id": "file_storage", "display_name": "File Storage", "level_count": 4}, "attempt_id": "145f8f18-2aa3-4c1a-8522-7b28283fd51c", "deadline_at": "2026-09-09T05:58:24.456224+00:00", "profile": {"duration_seconds": 5400, "mode": "full", "profile_id": "full-90m"}, "revision": 0, "schema_version": "session/v1", "score": null, "started_at": "2026-09-09T04:28:24.456224+00:00", "status": "active", "submitted_at": null}}, "schema_version": "cli/v1"}
[exit: 0]

$ /tmp/build/tmp.gyBHhFDFdb/venv/bin/codesignal-sim start --workspace-root /tmp/build/tmp.5b9n6kOI9V --mode drill --drill-duration-seconds 1800 --json
{"ok": true, "result": {"session": {"assessment": {"assessment_id": "file_storage", "display_name": "File Storage", "level_count": 4}, "attempt_id": "41792a5c-ef81-48fa-848a-4df1127b2fc1", "deadline_at": "2026-09-09T04:58:24.532170+00:00", "profile": {"duration_seconds": 1800, "mode": "drill", "profile_id": "drill-30m"}, "revision": 0, "schema_version": "session/v1", "score": null, "started_at": "2026-09-09T04:28:24.532170+00:00", "status": "active", "submitted_at": null}}, "schema_version": "cli/v1"}
[exit: 0]

$ /tmp/build/tmp.gyBHhFDFdb/venv/bin/codesignal-sim status --workspace-root /tmp/build/tmp.5b9n6kOI9V --attempt 145f8f18-2aa3-4c1a-8522-7b28283fd51c --json
{"ok": true, "result": {"session": {"assessment": {"assessment_id": "file_storage", "display_name": "File Storage", "level_count": 4}, "attempt_id": "145f8f18-2aa3-4c1a-8522-7b28283fd51c", "deadline_at": "2026-09-09T05:58:24.456224+00:00", "profile": {"duration_seconds": 5400, "mode": "full", "profile_id": "full-90m"}, "revision": 0, "schema_version": "session/v1", "score": null, "started_at": "2026-09-09T04:28:24.456224+00:00", "status": "active", "submitted_at": null}}, "schema_version": "cli/v1"}
[exit: 0]

$ /tmp/build/tmp.gyBHhFDFdb/venv/bin/python -m codesignal_practice_simulator status --workspace-root /tmp/build/tmp.5b9n6kOI9V --attempt 145f8f18-2aa3-4c1a-8522-7b28283fd51c --json
{"ok": true, "result": {"session": {"assessment": {"assessment_id": "file_storage", "display_name": "File Storage", "level_count": 4}, "attempt_id": "145f8f18-2aa3-4c1a-8522-7b28283fd51c", "deadline_at": "2026-09-09T05:58:24.456224+00:00", "profile": {"duration_seconds": 5400, "mode": "full", "profile_id": "full-90m"}, "revision": 0, "schema_version": "session/v1", "score": null, "started_at": "2026-09-09T04:28:24.456224+00:00", "status": "active", "submitted_at": null}}, "schema_version": "cli/v1"}
[exit: 0]

$ /tmp/build/tmp.gyBHhFDFdb/venv/bin/codesignal-sim resume --workspace-root /tmp/build/tmp.5b9n6kOI9V --attempt 41792a5c-ef81-48fa-848a-4df1127b2fc1 --json
{"ok": true, "result": {"session": {"assessment": {"assessment_id": "file_storage", "display_name": "File Storage", "level_count": 4}, "attempt_id": "41792a5c-ef81-48fa-848a-4df1127b2fc1", "deadline_at": "2026-09-09T04:58:24.532170+00:00", "profile": {"duration_seconds": 1800, "mode": "drill", "profile_id": "drill-30m"}, "revision": 0, "schema_version": "session/v1", "score": null, "started_at": "2026-09-09T04:28:24.532170+00:00", "status": "active", "submitted_at": null}}, "schema_version": "cli/v1"}
[exit: 0]

$ /tmp/build/tmp.gyBHhFDFdb/venv/bin/codesignal-sim time --workspace-root /tmp/build/tmp.5b9n6kOI9V --json
{"ok": true, "result": {"elapsed_seconds": 0, "observed_at": "2026-09-09T04:28:24.789178+00:00", "remaining_seconds": 1799, "session": {"assessment": {"assessment_id": "file_storage", "display_name": "File Storage", "level_count": 4}, "attempt_id": "41792a5c-ef81-48fa-848a-4df1127b2fc1", "deadline_at": "2026-09-09T04:58:24.532170+00:00", "profile": {"duration_seconds": 1800, "mode": "drill", "profile_id": "drill-30m"}, "revision": 0, "schema_version": "session/v1", "score": null, "started_at": "2026-09-09T04:28:24.532170+00:00", "status": "active", "submitted_at": null}}, "schema_version": "cli/v1"}
[exit: 0]

$ /tmp/build/tmp.gyBHhFDFdb/venv/bin/codesignal-sim context --workspace-root /tmp/build/tmp.5b9n6kOI9V --format json --json
{"ok": true, "result": {"context": {"assessment": {"display_name": "File Storage", "id": "file_storage", "mode": "drill", "profile": "drill-30m"}, "attempt_id": "41792a5c-ef81-48fa-848a-4df1127b2fc1", "events": [{"name": "started", "occurred_at": "2026-09-09T04:28:24.532170+00:00", "outcome": "succeeded", "revision": 0}], "lifecycle": {"deadline_at": "2026-09-09T04:58:24.532170+00:00", "started_at": "2026-09-09T04:28:24.532170+00:00", "status": "active", "submitted_at": null}, "next_legal_commands": ["codesignal-sim status --attempt 41792a5c-ef81-48fa-848a-4df1127b2fc1", "codesignal-sim context --attempt 41792a5c-ef81-48fa-848a-4df1127b2fc1", "codesignal-sim resume --attempt 41792a5c-ef81-48fa-848a-4df1127b2fc1", "codesignal-sim time --attempt 41792a5c-ef81-48fa-848a-4df1127b2fc1", "codesignal-sim test --attempt 41792a5c-ef81-48fa-848a-4df1127b2fc1", "codesignal-sim submit --attempt 41792a5c-ef81-48fa-848a-4df1127b2fc1"], "schema_version": "attempt-context/v1", "score": {"highest_contiguous_level": 0, "levels": [], "passed_levels": 0}}, "format": "json"}, "schema_version": "cli/v1"}
[exit: 0]

$ /tmp/build/tmp.gyBHhFDFdb/venv/bin/codesignal-sim task --workspace-root /tmp/build/tmp.5b9n6kOI9V --level 1 --json
{"ok": true, "result": {"attempt_id": "41792a5c-ef81-48fa-848a-4df1127b2fc1", "level": 1, "prompt": "# Scenario\n\nYour task is to implement a simplified version of a file hosting service.\nAll operations that should be supported are listed below. Partial credit will be granted for each test passed, so\npress “Submit” often to run tests and receive partial credits for passed tests. Please check tests for requirements\nand argument types.\n\n### Implementation Tips\n\nRead the question all the way through before you start coding, but implement the operations and complete the\nlevels one by one, not all together, keeping in mind that you will need to refactor to support additional functionality.\nPlease, do not change the existing method signatures.\n\n## Task\n\nExample of file structure with various files:\n\n```plaintext\n[server34] - 24000 Bytes Limit\n    Size\n    +- file-1.zip 4321 Bytes\n    +- dir-a\n    |   +- dir-c\n    |   |   +- file-2.txt 1100 Bytes\n    |   |   +- file-3.csv 2122 Bytes\n    +- dir-b\n    |   +- file-4.mdx 3378 Bytes\n```\n\n## Level 1 – Initial Design & Basic Functions\n\n- **FILE_UPLOAD(file_name, size)**\n  - Upload the file to the remote storage server.\n  - If a file with the same name already exists on the server, it throws a runtime exception.\n- **FILE_GET(file_name)**\n  - Returns the size of the file, or nothing if the file doesn’t exist.\n- **FILE_COPY(source, dest)**\n  - Copy the source file to a new location.\n  - If the source file doesn’t exist, it throws a runtime exception.\n  - If the destination file already exists, it overwrites the existing file.\n"}, "schema_version": "cli/v1"}
[exit: 0]

$ /tmp/build/tmp.gyBHhFDFdb/venv/bin/codesignal-sim test --workspace-root /tmp/build/tmp.5b9n6kOI9V --json
{"error": {"code": "candidate_failure", "message": "one or more test groups did not pass"}, "ok": false, "schema_version": "cli/v1"}
[exit: 5]

$ /tmp/build/tmp.gyBHhFDFdb/venv/bin/codesignal-sim submit --workspace-root /tmp/build/tmp.5b9n6kOI9V --json
{"ok": true, "result": {"score": {"highest_contiguous_level": 0, "levels": [{"level": 1, "outcome": "error"}, {"level": 2, "outcome": "error"}, {"level": 3, "outcome": "error"}, {"level": 4, "outcome": "error"}], "passed_levels": 0}, "session": {"assessment": {"assessment_id": "file_storage", "display_name": "File Storage", "level_count": 4}, "attempt_id": "41792a5c-ef81-48fa-848a-4df1127b2fc1", "deadline_at": "2026-09-09T04:58:24.532170+00:00", "profile": {"duration_seconds": 1800, "mode": "drill", "profile_id": "drill-30m"}, "revision": 2, "schema_version": "session/v1", "score": {"highest_contiguous_level": 0, "levels": [{"level": 1, "outcome": "error"}, {"level": 2, "outcome": "error"}, {"level": 3, "outcome": "error"}, {"level": 4, "outcome": "error"}], "passed_levels": 0}, "started_at": "2026-09-09T04:28:24.532170+00:00", "status": "submitted", "submitted_at": "2026-09-09T04:28:25.303550+00:00"}}, "schema_version": "cli/v1"}
[exit: 0]

$ /tmp/build/tmp.gyBHhFDFdb/venv/bin/codesignal-sim submit --workspace-root /tmp/build/tmp.5b9n6kOI9V --json
{"ok": true, "result": {"score": {"highest_contiguous_level": 0, "levels": [{"level": 1, "outcome": "error"}, {"level": 2, "outcome": "error"}, {"level": 3, "outcome": "error"}, {"level": 4, "outcome": "error"}], "passed_levels": 0}, "session": {"assessment": {"assessment_id": "file_storage", "display_name": "File Storage", "level_count": 4}, "attempt_id": "41792a5c-ef81-48fa-848a-4df1127b2fc1", "deadline_at": "2026-09-09T04:58:24.532170+00:00", "profile": {"duration_seconds": 1800, "mode": "drill", "profile_id": "drill-30m"}, "revision": 2, "schema_version": "session/v1", "score": {"highest_contiguous_level": 0, "levels": [{"level": 1, "outcome": "error"}, {"level": 2, "outcome": "error"}, {"level": 3, "outcome": "error"}, {"level": 4, "outcome": "error"}], "passed_levels": 0}, "started_at": "2026-09-09T04:28:24.532170+00:00", "status": "submitted", "submitted_at": "2026-09-09T04:28:25.303550+00:00"}}, "schema_version": "cli/v1"}
[exit: 0]

$ /tmp/build/tmp.gyBHhFDFdb/venv/bin/codesignal-sim resume --workspace-root /tmp/build/tmp.5b9n6kOI9V --json
{"error": {"code": "illegal_lifecycle", "message": "cannot resume an attempt in submitted state"}, "ok": false, "schema_version": "cli/v1"}
[exit: 4]

$ /tmp/build/tmp.gyBHhFDFdb/venv/bin/codesignal-sim test --workspace-root /tmp/build/tmp.5b9n6kOI9V --json
{"error": {"code": "illegal_lifecycle", "message": "cannot test an attempt in submitted state"}, "ok": false, "schema_version": "cli/v1"}
[exit: 4]

$ /tmp/build/tmp.gyBHhFDFdb/venv/bin/codesignal-sim start --workspace-root /tmp/build/tmp.5b9n6kOI9V --mode drill --drill-duration-seconds 900 --json
{"ok": true, "result": {"session": {"assessment": {"assessment_id": "file_storage", "display_name": "File Storage", "level_count": 4}, "attempt_id": "851cb71b-6bb1-4418-996a-15e633b72e4a", "deadline_at": "2026-09-09T04:43:25.526077+00:00", "profile": {"duration_seconds": 900, "mode": "drill", "profile_id": "drill-30m"}, "revision": 0, "schema_version": "session/v1", "score": null, "started_at": "2026-09-09T04:28:25.526077+00:00", "status": "active", "submitted_at": null}}, "schema_version": "cli/v1"}
[exit: 0]
[managed workspace and virtual environment removed after this command]

## Required verification
usage: codesignal-sim [-h] [--version] COMMAND ...

CodeSignal Practice Simulator

positional arguments:
  COMMAND
    fetch     populate the ignored fixture cache
    start     create a new attempt
    resume    resume an active attempt
    status    show selected attempt status
    time      show selected attempt time
    test      score selected attempt
    submit    submit selected attempt
    context   show safe selected attempt context
    task      show a selected attempt task

options:
  -h, --help  show this help message and exit
  --version   show program's version number and exit
[exit: 0]
usage: codesignal-sim [-h] [--version] COMMAND ...

CodeSignal Practice Simulator

positional arguments:
  COMMAND
    fetch     populate the ignored fixture cache
    start     create a new attempt
    resume    resume an active attempt
    status    show selected attempt status
    time      show selected attempt time
    test      score selected attempt
    submit    submit selected attempt
    context   show safe selected attempt context
    task      show a selected attempt task

options:
  -h, --help  show this help message and exit
  --version   show program's version number and exit
[exit: 0]
Available recipes:
    attempts                      # List UUID attempt directories. active.json selects the current one.
    clean                         # Remove Python caches
    context                       # Read safe, non-authoritative attempt context without candidate source.
    default                       # List available recipes
    fetch                         # Fetch the seven pinned assessment files into the ignored fixture cache.
    practice                      # Start a new 90-minute attempt with a UUID directory and session.json.
    practice-drill seconds="1800" # Start a drill with an explicit persisted duration.
    resume                        # Resume the selected active attempt.
    setup                         # Install the local simulator. FETCH_ONLY material is fetched separately.
    status                        # Show the selected attempt's derived status and remaining time.
    study-check level file        # Check a local post-attempt study file against a staged checker.
    study-spec                    # Post-attempt, spec-accurate reference tests: rollback, TTL, and error cases.
    study-stages                  # Post-attempt staged reference tests, one cumulative program per level.
    submit                        # Finalize the selected attempt once; a repeat returns its stored result.
    task n="1"                    # Read only the copied prompt from the selected attempt.
    test                          # Score all copied candidate test groups. Exit 5 means a candidate test failed.
    test-all                      # Deprecated aggregate of post-attempt compatibility and study suites.
    test-compat                   # It is not a timed simulator command and requires the ignored fixture cache.
    time
    verify                        # Run the maintained simulator suite and reject whitespace errors.
[exit: 0]
cd /workspace/campaign/projects/codesignal-practice-simulator && python3 -m unittest discover -s tests -v
test_bad_input_does_not_construct_an_application_or_mutate_workspace (test_cli.CliTests.test_bad_input_does_not_construct_an_application_or_mutate_workspace) ... ok
test_console_adapter_and_module_help_are_identical (test_cli.CliTests.test_console_adapter_and_module_help_are_identical) ... ok
test_domain_errors_have_stable_json_envelopes_and_exits (test_cli.CliTests.test_domain_errors_have_stable_json_envelopes_and_exits) ... ok
test_explicit_selector_is_forwarded_without_active_pointer_fallback (test_cli.CliTests.test_explicit_selector_is_forwarded_without_active_pointer_fallback) ... ok
test_human_success_and_error_envelopes_are_versioned (test_cli.CliTests.test_human_success_and_error_envelopes_are_versioned) ... ok
test_options_are_parsed_after_the_subcommand_and_attempt_is_forwarded (test_cli.CliTests.test_options_are_parsed_after_the_subcommand_and_attempt_is_forwarded) ... ok
test_parse_and_serializer_failures_are_safe_json_input_errors (test_cli.CliTests.test_parse_and_serializer_failures_are_safe_json_input_errors) ... ok
test_parser_exposes_the_documented_command_tree_and_common_options (test_cli.CliTests.test_parser_exposes_the_documented_command_tree_and_common_options) ... ok
test_unexpected_adapter_failure_uses_a_safe_internal_error (test_cli.CliTests.test_unexpected_adapter_failure_uses_a_safe_internal_error) ... ok
test_context_is_safe_read_only_and_available_after_submission (test_cli.RuntimeCliTests.test_context_is_safe_read_only_and_available_after_submission) ... ok
test_expired_test_records_one_expiry_and_never_starts_a_runner (test_cli.RuntimeCliTests.test_expired_test_records_one_expiry_and_never_starts_a_runner) ... ok
test_missing_or_invalid_cache_reports_setup_repair_before_workspace_mutation (test_cli.RuntimeCliTests.test_missing_or_invalid_cache_reports_setup_repair_before_workspace_mutation) ... ok
test_no_or_corrupt_pointer_is_unavailable_but_explicit_selector_precedes_it (test_cli.RuntimeCliTests.test_no_or_corrupt_pointer_is_unavailable_but_explicit_selector_precedes_it) ... ok
test_overdue_submit_expires_then_finalizes_once_and_scoring_error_is_atomic (test_cli.RuntimeCliTests.test_overdue_submit_expires_then_finalizes_once_and_scoring_error_is_atomic) ... ok
test_runtime_adapter_delegates_derived_status_to_typed_service (test_cli.RuntimeCliTests.test_runtime_adapter_delegates_derived_status_to_typed_service) ... ok
test_start_uses_project_fixture_cache_and_persists_full_or_drill_profiles (test_cli.RuntimeCliTests.test_start_uses_project_fixture_cache_and_persists_full_or_drill_profiles) ... ok
test_status_and_time_expire_once_and_final_resume_does_not_mutate (test_cli.RuntimeCliTests.test_status_and_time_expire_once_and_final_resume_does_not_mutate) ... ok
test_submit_cli_recovers_a_failed_event_append_without_rescoring_or_touching_neighbors (test_cli.RuntimeCliTests.test_submit_cli_recovers_a_failed_event_append_without_rescoring_or_touching_neighbors) ... ok
test_submit_is_byte_identical_and_never_rescores_after_finality (test_cli.RuntimeCliTests.test_submit_is_byte_identical_and_never_rescores_after_finality) ... ok
test_submitted_resume_does_not_mutate (test_cli.RuntimeCliTests.test_submitted_resume_does_not_mutate) ... ok
test_task_reads_only_copied_selected_prompt_and_validates_level (test_cli.RuntimeCliTests.test_task_reads_only_copied_selected_prompt_and_validates_level) ... ok
test_test_all_passes_returns_zero_with_isolated_subprocess_score (test_cli.RuntimeCliTests.test_test_all_passes_returns_zero_with_isolated_subprocess_score) ... ok
test_test_persists_all_four_outcomes_and_returns_candidate_failure (test_cli.RuntimeCliTests.test_test_persists_all_four_outcomes_and_returns_candidate_failure) ... ok
test_unregistered_persisted_assessment_is_corrupt_in_json_and_human_output (test_cli.RuntimeCliTests.test_unregistered_persisted_assessment_is_corrupt_in_json_and_human_output) ... ok
test_installed_wheel_fetches_offline_then_starts_outside_checkout (test_cli.WheelRuntimeTests.test_installed_wheel_fetches_offline_then_starts_outside_checkout) ... ok
test_agent_and_legacy_documents_preserve_live_attempt_boundaries (test_documentation.DocumentationTests.test_agent_and_legacy_documents_preserve_live_attempt_boundaries) ... ok
test_contract_covers_envelopes_lifecycle_and_profiles (test_documentation.DocumentationTests.test_contract_covers_envelopes_lifecycle_and_profiles) ... ok
test_just_recipes_are_optional_cli_shortcuts_and_verify_the_project (test_documentation.DocumentationTests.test_just_recipes_are_optional_cli_shortcuts_and_verify_the_project) ... ok
test_readme_documents_the_session_based_cli_without_requiring_just (test_documentation.DocumentationTests.test_readme_documents_the_session_based_cli_without_requiring_just) ... ok
test_packaged_metadata_matches_the_canonical_fetch_records (test_fixture_setup.FixtureSetupTests.test_packaged_metadata_matches_the_canonical_fetch_records) ... ok
test_packaged_setup_logic_fetches_and_validates_without_checkout_scripts (test_fixture_setup.FixtureSetupTests.test_packaged_setup_logic_fetches_and_validates_without_checkout_scripts) ... ok
test_publish_never_removes_an_unowned_legacy_backup_path (test_fixture_setup.FixtureSetupTests.test_publish_never_removes_an_unowned_legacy_backup_path) ... ok
test_publish_restores_the_old_cache_after_staging_rename_failure (test_fixture_setup.FixtureSetupTests.test_publish_restores_the_old_cache_after_staging_rename_failure) ... ok
test_setup_refuses_an_attempts_symlink_to_its_cache_before_writing (test_fixture_setup.FixtureSetupTests.test_setup_refuses_an_attempts_symlink_to_its_cache_before_writing) ... ok
test_corrupt_active_selection_fails_but_explicit_selection_still_works (test_lifecycle.LifecycleTests.test_corrupt_active_selection_fails_but_explicit_selection_still_works) ... ok
test_expired_resume_and_test_are_exit_four_and_byte_identical (test_lifecycle.LifecycleTests.test_expired_resume_and_test_are_exit_four_and_byte_identical) ... ok
test_expiring_one_attempt_leaves_neighbor_bytes_unchanged (test_lifecycle.LifecycleTests.test_expiring_one_attempt_leaves_neighbor_bytes_unchanged) ... ok
test_explicit_active_resume_replaces_selection (test_lifecycle.LifecycleTests.test_explicit_active_resume_replaces_selection) ... ok
test_first_overdue_status_observer_persists_exactly_one_expiry (test_lifecycle.LifecycleTests.test_first_overdue_status_observer_persists_exactly_one_expiry) ... ok
test_lock_contention_returns_exit_four_and_preserves_neighboring_attempt (test_lifecycle.LifecycleTests.test_lock_contention_returns_exit_four_and_preserves_neighboring_attempt) ... ok
test_locked_state_read_rejects_a_registry_mismatch (test_lifecycle.LifecycleTests.test_locked_state_read_rejects_a_registry_mismatch) ... ok
test_next_command_recovers_a_missing_event_for_the_current_revision (test_lifecycle.LifecycleTests.test_next_command_recovers_a_missing_event_for_the_current_revision) ... ok
test_overdue_submit_persists_expiry_before_one_submission (test_lifecycle.LifecycleTests.test_overdue_submit_persists_expiry_before_one_submission) ... ok
test_record_test_result_updates_active_state_under_one_revision (test_lifecycle.LifecycleTests.test_record_test_result_updates_active_state_under_one_revision) ... ok
test_repeat_submit_without_scorer_preserves_submitted_missing_event_bytes (test_lifecycle.LifecycleTests.test_repeat_submit_without_scorer_preserves_submitted_missing_event_bytes) ... ok
test_scoring_does_not_hold_the_workspace_lock (test_lifecycle.LifecycleTests.test_scoring_does_not_hold_the_workspace_lock) ... ok
test_start_creates_selected_full_or_drill_attempt (test_lifecycle.LifecycleTests.test_start_creates_selected_full_or_drill_attempt) ... ok
test_status_and_time_before_deadline_are_safe_reads (test_lifecycle.LifecycleTests.test_status_and_time_before_deadline_are_safe_reads) ... ok
test_submit_active_and_repeat_submit_returns_the_stored_result_without_writes (test_lifecycle.LifecycleTests.test_submit_active_and_repeat_submit_returns_the_stored_result_without_writes) ... ok
test_submit_event_failure_leaves_a_recoverable_final_state_without_rescoring (test_lifecycle.LifecycleTests.test_submit_event_failure_leaves_a_recoverable_final_state_without_rescoring) ... ok
test_submit_finalizes_a_previously_expired_attempt_once (test_lifecycle.LifecycleTests.test_submit_finalizes_a_previously_expired_attempt_once) ... ok
test_submit_uses_a_short_selection_lock_before_scoring (test_lifecycle.LifecycleTests.test_submit_uses_a_short_selection_lock_before_scoring) ... ok
test_submitted_attempt_refuses_resume_and_test_without_mutation (test_lifecycle.LifecycleTests.test_submitted_attempt_refuses_resume_and_test_without_mutation) ... ok
test_terminal_commands_do_not_recover_a_missing_current_event (test_lifecycle.LifecycleTests.test_terminal_commands_do_not_recover_a_missing_current_event) ... ok
test_test_uses_a_short_selection_lock_then_records_result (test_lifecycle.LifecycleTests.test_test_uses_a_short_selection_lock_then_records_result) ... ok
test_absent_cache_requires_setup (test_migration.FetchFixtureTests.test_absent_cache_requires_setup) ... ok
test_complete_source_setup_includes_vendor_readme (test_migration.FetchFixtureTests.test_complete_source_setup_includes_vendor_readme) ... ok
test_hash_mismatch_preserves_existing_cache (test_migration.FetchFixtureTests.test_hash_mismatch_preserves_existing_cache) ... ok
test_incomplete_local_source_does_not_publish_cache (test_migration.FetchFixtureTests.test_incomplete_local_source_does_not_publish_cache) ... ok
test_invalid_manifest_path_is_rejected (test_migration.FetchFixtureTests.test_invalid_manifest_path_is_rejected) ... ok
test_mocked_downloader_failure_does_not_publish_cache (test_migration.FetchFixtureTests.test_mocked_downloader_failure_does_not_publish_cache) ... ok
test_git_boundary_rejects_head_vendor_hash (test_migration.ManifestVerifierTests.test_git_boundary_rejects_head_vendor_hash) ... ok
test_git_boundary_rejects_head_vendor_path (test_migration.ManifestVerifierTests.test_git_boundary_rejects_head_vendor_path) ... ok
test_git_boundary_rejects_staged_vendor_hash (test_migration.ManifestVerifierTests.test_git_boundary_rejects_staged_vendor_hash) ... ok
test_git_boundary_rejects_staged_vendor_path (test_migration.ManifestVerifierTests.test_git_boundary_rejects_staged_vendor_path) ... ok
test_git_boundary_safe_control (test_migration.ManifestVerifierTests.test_git_boundary_safe_control) ... ok
test_real_project_does_not_track_fixture_contents (test_migration.ManifestVerifierTests.test_real_project_does_not_track_fixture_contents) ... ok
test_attempt_uses_its_copied_tests (test_migration.ScorecardFixtureTests.test_attempt_uses_its_copied_tests) ... ok
test_solution_uses_cached_tests_with_solution_as_the_candidate (test_migration.ScorecardFixtureTests.test_solution_uses_cached_tests_with_solution_as_the_candidate) ... ok
test_clock_protocol_accepts_a_fake_clock_and_utc_clock_returns_utc (test_models.ErrorAndClockTests.test_clock_protocol_accepts_a_fake_clock_and_utc_clock_returns_utc) ... ok
test_domain_errors_have_stable_exit_classes (test_models.ErrorAndClockTests.test_domain_errors_have_stable_exit_classes) ... ok
test_assessment_profile_score_session_and_pointer_round_trip (test_models.ModelRoundTripTests.test_assessment_profile_score_session_and_pointer_round_trip) ... ok
test_drill_profile_persists_an_explicit_duration_override (test_models.ModelRoundTripTests.test_drill_profile_persists_an_explicit_duration_override) ... ok
test_event_round_trip_and_arguments_are_immutable (test_models.ModelRoundTripTests.test_event_round_trip_and_arguments_are_immutable) ... ok
test_score_summary_derives_counts_from_independent_results (test_models.ModelRoundTripTests.test_score_summary_derives_counts_from_independent_results) ... ok
test_active_pointer_rejects_unknown_schema_invalid_id_and_extra_field (test_models.SchemaValidationTests.test_active_pointer_rejects_unknown_schema_invalid_id_and_extra_field) ... ok
test_assessment_rejects_unknown_and_malformed_values (test_models.SchemaValidationTests.test_assessment_rejects_unknown_and_malformed_values) ... ok
test_event_rejects_invalid_schema_ids_timestamps_and_arguments (test_models.SchemaValidationTests.test_event_rejects_invalid_schema_ids_timestamps_and_arguments) ... ok
test_profile_rejects_unknown_profile_mode_and_duration (test_models.SchemaValidationTests.test_profile_rejects_unknown_profile_mode_and_duration) ... ok
test_score_rejects_every_invalid_four_level_shape (test_models.SchemaValidationTests.test_score_rejects_every_invalid_four_level_shape) ... ok
test_session_rejects_deadline_order_and_duration_mismatch (test_models.SchemaValidationTests.test_session_rejects_deadline_order_and_duration_mismatch) ... ok
test_session_rejects_illegal_submission_combinations (test_models.SchemaValidationTests.test_session_rejects_illegal_submission_combinations) ... ok
test_session_rejects_malformed_ids_and_revisions (test_models.SchemaValidationTests.test_session_rejects_malformed_ids_and_revisions) ... ok
test_session_rejects_malformed_score_object (test_models.SchemaValidationTests.test_session_rejects_malformed_score_object) ... ok
test_session_rejects_naive_non_utc_and_malformed_timestamps (test_models.SchemaValidationTests.test_session_rejects_naive_non_utc_and_malformed_timestamps) ... ok
test_session_rejects_unsupported_schema_and_invalid_field_sets (test_models.SchemaValidationTests.test_session_rejects_unsupported_schema_and_invalid_field_sets) ... ok
test_attempt_and_workspace_locks_reject_contention (test_persistence.PersistenceTests.test_attempt_and_workspace_locks_reject_contention) ... ok
test_event_schema_corruption_is_not_an_incomplete_tail (test_persistence.PersistenceTests.test_event_schema_corruption_is_not_an_incomplete_tail) ... ok
test_events_reject_duplicate_event_ids (test_persistence.PersistenceTests.test_events_reject_duplicate_event_ids) ... ok
test_invalid_pointer_is_a_corruption_error (test_persistence.PersistenceTests.test_invalid_pointer_is_a_corruption_error) ... ok
test_jsonl_rejects_bad_nonfinal_records_and_only_ignores_one_tail (test_persistence.PersistenceTests.test_jsonl_rejects_bad_nonfinal_records_and_only_ignores_one_tail) ... ok
test_locked_recovery_does_not_reacquire_the_attempt_lock (test_persistence.PersistenceTests.test_locked_recovery_does_not_reacquire_the_attempt_lock) ... ok
test_pointer_write_faults_preserve_previous_pointer_bytes (test_persistence.PersistenceTests.test_pointer_write_faults_preserve_previous_pointer_bytes) ... ok
test_recovery_appends_one_event_for_a_missing_authoritative_revision (test_persistence.PersistenceTests.test_recovery_appends_one_event_for_a_missing_authoritative_revision) ... ok
test_recovery_rejects_event_records_owned_by_another_attempt (test_persistence.PersistenceTests.test_recovery_rejects_event_records_owned_by_another_attempt) ... ok
test_session_and_pointer_use_flushed_sibling_replacements (test_persistence.PersistenceTests.test_session_and_pointer_use_flushed_sibling_replacements) ... ok
test_state_write_faults_preserve_previous_session_bytes (test_persistence.PersistenceTests.test_state_write_faults_preserve_previous_session_bytes) ... ok
test_submission_recovery_rejects_a_conflicting_event_without_publishing_state (test_persistence.PersistenceTests.test_submission_recovery_rejects_a_conflicting_event_without_publishing_state) ... ok
test_submission_recovery_rejects_a_session_other_than_its_exact_endpoints (test_persistence.PersistenceTests.test_submission_recovery_rejects_a_session_other_than_its_exact_endpoints) ... ok
test_submission_recovery_rewrites_an_event_whose_flush_failed_after_append (test_persistence.PersistenceTests.test_submission_recovery_rewrites_an_event_whose_flush_failed_after_append) ... ok
test_submission_recovery_survives_a_reported_session_publish_failure (test_persistence.PersistenceTests.test_submission_recovery_survives_a_reported_session_publish_failure) ... ok
test_active_selection_and_prompt_read_hold_workspace_then_attempt_locks (test_prompts.PromptServiceTests.test_active_selection_and_prompt_read_hold_workspace_then_attempt_locks) ... ok
test_explicit_selection_precedes_a_corrupt_active_pointer (test_prompts.PromptServiceTests.test_explicit_selection_precedes_a_corrupt_active_pointer) ... ok
test_reads_typed_result_under_attempt_lock (test_prompts.PromptServiceTests.test_reads_typed_result_under_attempt_lock) ... ok
test_rejects_invalid_levels_and_unsafe_or_unreadable_prompt_files (test_prompts.PromptServiceTests.test_rejects_invalid_levels_and_unsafe_or_unreadable_prompt_files) ... ok
test_revalidates_persisted_registry_state_before_reading (test_prompts.PromptServiceTests.test_revalidates_persisted_registry_state_before_reading) ... ok
test_attempt_templates_state_the_operational_boundary (test_rendering.RenderingTests.test_attempt_templates_state_the_operational_boundary) ... ok
test_coaching_and_regenerated_status_preserve_candidate_state_cache_and_reference (test_rendering.RenderingTests.test_coaching_and_regenerated_status_preserve_candidate_state_cache_and_reference) ... ok
test_derived_status_cannot_replace_newer_lifecycle_state (test_rendering.RenderingTests.test_derived_status_cannot_replace_newer_lifecycle_state) ... ok
test_derived_status_is_best_effort_and_does_not_reject_lifecycle_results (test_rendering.RenderingTests.test_derived_status_is_best_effort_and_does_not_reject_lifecycle_results) ... ok
test_invalid_session_or_events_return_unavailable_without_status_write (test_rendering.RenderingTests.test_invalid_session_or_events_return_unavailable_without_status_write) ... ok
test_lifecycle_transition_never_renders_and_explicit_refresh_uses_latest_state (test_rendering.RenderingTests.test_lifecycle_transition_never_renders_and_explicit_refresh_uses_latest_state) ... ok
test_markdown_and_json_contain_only_safe_derived_context (test_rendering.RenderingTests.test_markdown_and_json_contain_only_safe_derived_context) ... ok
test_renderer_failure_preserves_candidate_state_cache_and_reference_bytes (test_rendering.RenderingTests.test_renderer_failure_preserves_candidate_state_cache_and_reference_bytes) ... ok
test_candidate_fork_for_setsid_is_rejected_without_creating_a_child (test_scoring.ScoringTests.test_candidate_fork_for_setsid_is_rejected_without_creating_a_child) ... ok
test_coaching_status_and_cache_changes_do_not_affect_candidate_only_score (test_scoring.ScoringTests.test_coaching_status_and_cache_changes_do_not_affect_candidate_only_score) ... ok
test_failure_crash_timeout_and_missing_input_do_not_skip_later_groups (test_scoring.ScoringTests.test_failure_crash_timeout_and_missing_input_do_not_skip_later_groups) ... ok
test_isolation_excludes_editable_install_pythonpath_and_loose_reference (test_scoring.ScoringTests.test_isolation_excludes_editable_install_pythonpath_and_loose_reference) ... ok
test_launch_error_is_recorded_for_each_group (test_scoring.ScoringTests.test_launch_error_is_recorded_for_each_group) ... ok
test_lifecycle_persists_four_independent_results_from_exact_launches (test_scoring.ScoringTests.test_lifecycle_persists_four_independent_results_from_exact_launches) ... ok
test_output_is_bounded (test_scoring.ScoringTests.test_output_is_bounded) ... ok
test_registry_has_only_file_storage_with_its_complete_contract (test_scoring.ScoringTests.test_registry_has_only_file_storage_with_its_complete_contract) ... ok
test_runner_rejects_an_invalid_group_and_wrong_working_directory (test_scoring.ScoringTests.test_runner_rejects_an_invalid_group_and_wrong_working_directory) ... ok
test_setup_required_cache_failure_occurs_before_workspace_mutation (test_scoring.ScoringTests.test_setup_required_cache_failure_occurs_before_workspace_mutation) ... ok
test_timeout_kills_a_detached_descendant_from_the_immediate_snapshot (test_scoring.ScoringTests.test_timeout_kills_a_detached_descendant_from_the_immediate_snapshot) ... ok
test_workspace_copies_runner_and_only_registered_candidate_inputs (test_scoring.ScoringTests.test_workspace_copies_runner_and_only_registered_candidate_inputs) ... ok
test_attempts_symlink_to_cache_is_rejected_without_cache_mutation (test_workspace.WorkspaceTests.test_attempts_symlink_to_cache_is_rejected_without_cache_mutation) ... ok
test_cache_nested_in_attempts_is_rejected_without_cache_mutation (test_workspace.WorkspaceTests.test_cache_nested_in_attempts_is_rejected_without_cache_mutation) ... ok
test_corrupt_pointer_and_explicit_selection_precedence (test_workspace.WorkspaceTests.test_corrupt_pointer_and_explicit_selection_precedence) ... ok
test_creation_copies_only_six_assessment_files_and_keeps_cache_immutable (test_workspace.WorkspaceTests.test_creation_copies_only_six_assessment_files_and_keeps_cache_immutable) ... ok
test_every_creation_filesystem_failure_rolls_back_only_new_attempt (test_workspace.WorkspaceTests.test_every_creation_filesystem_failure_rolls_back_only_new_attempt)
Exercise every individual mkdir/copy/write/flush/replace creation call. ... ok
test_hash_invalid_cache_creates_nothing (test_workspace.WorkspaceTests.test_hash_invalid_cache_creates_nothing) ... ok
test_invalid_or_absent_cache_creates_nothing (test_workspace.WorkspaceTests.test_invalid_or_absent_cache_creates_nothing) ... ok
test_publish_before_pointer_interruption_reconciles_only_owned_attempt (test_workspace.WorkspaceTests.test_publish_before_pointer_interruption_reconciles_only_owned_attempt) ... ok
test_reconciliation_never_deletes_unowned_or_pointer_selected_attempt (test_workspace.WorkspaceTests.test_reconciliation_never_deletes_unowned_or_pointer_selected_attempt) ... ok
test_workspace_with_cache_symlink_ancestor_is_rejected_before_mutation (test_workspace.WorkspaceTests.test_workspace_with_cache_symlink_ancestor_is_rejected_before_mutation) ... ok

----------------------------------------------------------------------
Ran 136 tests in 5.349s

OK
cd /workspace/campaign/projects/codesignal-practice-simulator && git diff --check HEAD
[exit: 0]
test_bad_input_does_not_construct_an_application_or_mutate_workspace (tests.test_cli.CliTests.test_bad_input_does_not_construct_an_application_or_mutate_workspace) ... ok
test_console_adapter_and_module_help_are_identical (tests.test_cli.CliTests.test_console_adapter_and_module_help_are_identical) ... ok
test_domain_errors_have_stable_json_envelopes_and_exits (tests.test_cli.CliTests.test_domain_errors_have_stable_json_envelopes_and_exits) ... ok
test_explicit_selector_is_forwarded_without_active_pointer_fallback (tests.test_cli.CliTests.test_explicit_selector_is_forwarded_without_active_pointer_fallback) ... ok
test_human_success_and_error_envelopes_are_versioned (tests.test_cli.CliTests.test_human_success_and_error_envelopes_are_versioned) ... ok
test_options_are_parsed_after_the_subcommand_and_attempt_is_forwarded (tests.test_cli.CliTests.test_options_are_parsed_after_the_subcommand_and_attempt_is_forwarded) ... ok
test_parse_and_serializer_failures_are_safe_json_input_errors (tests.test_cli.CliTests.test_parse_and_serializer_failures_are_safe_json_input_errors) ... ok
test_parser_exposes_the_documented_command_tree_and_common_options (tests.test_cli.CliTests.test_parser_exposes_the_documented_command_tree_and_common_options) ... ok
test_unexpected_adapter_failure_uses_a_safe_internal_error (tests.test_cli.CliTests.test_unexpected_adapter_failure_uses_a_safe_internal_error) ... ok
test_context_is_safe_read_only_and_available_after_submission (tests.test_cli.RuntimeCliTests.test_context_is_safe_read_only_and_available_after_submission) ... ok
test_expired_test_records_one_expiry_and_never_starts_a_runner (tests.test_cli.RuntimeCliTests.test_expired_test_records_one_expiry_and_never_starts_a_runner) ... ok
test_missing_or_invalid_cache_reports_setup_repair_before_workspace_mutation (tests.test_cli.RuntimeCliTests.test_missing_or_invalid_cache_reports_setup_repair_before_workspace_mutation) ... ok
test_no_or_corrupt_pointer_is_unavailable_but_explicit_selector_precedes_it (tests.test_cli.RuntimeCliTests.test_no_or_corrupt_pointer_is_unavailable_but_explicit_selector_precedes_it) ... ok
test_overdue_submit_expires_then_finalizes_once_and_scoring_error_is_atomic (tests.test_cli.RuntimeCliTests.test_overdue_submit_expires_then_finalizes_once_and_scoring_error_is_atomic) ... ok
test_runtime_adapter_delegates_derived_status_to_typed_service (tests.test_cli.RuntimeCliTests.test_runtime_adapter_delegates_derived_status_to_typed_service) ... ok
test_start_uses_project_fixture_cache_and_persists_full_or_drill_profiles (tests.test_cli.RuntimeCliTests.test_start_uses_project_fixture_cache_and_persists_full_or_drill_profiles) ... ok
test_status_and_time_expire_once_and_final_resume_does_not_mutate (tests.test_cli.RuntimeCliTests.test_status_and_time_expire_once_and_final_resume_does_not_mutate) ... ok
test_submit_cli_recovers_a_failed_event_append_without_rescoring_or_touching_neighbors (tests.test_cli.RuntimeCliTests.test_submit_cli_recovers_a_failed_event_append_without_rescoring_or_touching_neighbors) ... ok
test_submit_is_byte_identical_and_never_rescores_after_finality (tests.test_cli.RuntimeCliTests.test_submit_is_byte_identical_and_never_rescores_after_finality) ... ok
test_submitted_resume_does_not_mutate (tests.test_cli.RuntimeCliTests.test_submitted_resume_does_not_mutate) ... ok
test_task_reads_only_copied_selected_prompt_and_validates_level (tests.test_cli.RuntimeCliTests.test_task_reads_only_copied_selected_prompt_and_validates_level) ... ok
test_test_all_passes_returns_zero_with_isolated_subprocess_score (tests.test_cli.RuntimeCliTests.test_test_all_passes_returns_zero_with_isolated_subprocess_score) ... ok
test_test_persists_all_four_outcomes_and_returns_candidate_failure (tests.test_cli.RuntimeCliTests.test_test_persists_all_four_outcomes_and_returns_candidate_failure) ... ok
test_unregistered_persisted_assessment_is_corrupt_in_json_and_human_output (tests.test_cli.RuntimeCliTests.test_unregistered_persisted_assessment_is_corrupt_in_json_and_human_output) ... ok
test_installed_wheel_fetches_offline_then_starts_outside_checkout (tests.test_cli.WheelRuntimeTests.test_installed_wheel_fetches_offline_then_starts_outside_checkout) ... ok

----------------------------------------------------------------------
Ran 25 tests in 3.053s

OK
[exit: 0]
[exit: 0]
 M AGENTS.md
 M README.md
 M docs/agent-safety.md
M  docs/cli-contract.md
 M docs/legacy/explore-README.md
 M justfile
 M justfiles/practice.just
 M justfiles/verify.just
 M notes/level4-rollback-discrepancy.md
 M notes/walkthrough.md
M  src/codesignal_practice_simulator/cli.py
A  src/codesignal_practice_simulator/evaluation.py
M  src/codesignal_practice_simulator/filesystem.py
M  src/codesignal_practice_simulator/lifecycle.py
M  src/codesignal_practice_simulator/models.py
M  src/codesignal_practice_simulator/persistence.py
M  src/codesignal_practice_simulator/rendering.py
M  src/codesignal_practice_simulator/workspace.py
 M study/README.md
M  tests/test_cli.py
 M tests/test_documentation.py
M  tests/test_lifecycle.py
M  tests/test_persistence.py
M  tests/test_rendering.py
?? docs/drill-profiles.md
[exit: 0]
