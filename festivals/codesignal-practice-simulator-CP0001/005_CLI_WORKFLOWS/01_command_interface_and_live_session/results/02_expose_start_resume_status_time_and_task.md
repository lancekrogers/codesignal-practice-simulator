{"ok": true, "result": {"session": {"assessment": {"assessment_id": "file_storage", "display_name": "File Storage", "level_count": 4}, "attempt_id": "297906d1-f331-4e99-b35c-173c817a9e71", "deadline_at": "2026-09-09T04:22:29.227217+00:00", "profile": {"duration_seconds": 5400, "mode": "full", "profile_id": "full-90m"}, "revision": 0, "schema_version": "session/v1", "score": null, "started_at": "2026-09-09T02:52:29.227217+00:00", "status": "active", "submitted_at": null}}, "schema_version": "cli/v1"}
{"ok": true, "result": {"session": {"assessment": {"assessment_id": "file_storage", "display_name": "File Storage", "level_count": 4}, "attempt_id": "297906d1-f331-4e99-b35c-173c817a9e71", "deadline_at": "2026-09-09T04:22:29.227217+00:00", "profile": {"duration_seconds": 5400, "mode": "full", "profile_id": "full-90m"}, "revision": 0, "schema_version": "session/v1", "score": null, "started_at": "2026-09-09T02:52:29.227217+00:00", "status": "active", "submitted_at": null}}, "schema_version": "cli/v1"}
[cli/v1] success
session: {'schema_version': 'session/v1', 'attempt_id': '297906d1-f331-4e99-b35c-173c817a9e71', 'assessment': {'assessment_id': 'file_storage', 'display_name': 'File Storage', 'level_count': 4}, 'profile': {'mode': 'full', 'profile_id': 'full-90m', 'duration_seconds': 5400}, 'started_at': '2026-09-09T02:52:29.227217+00:00', 'deadline_at': '2026-09-09T04:22:29.227217+00:00', 'status': 'active', 'revision': 0, 'score': None, 'submitted_at': None}
observed_at: 2026-09-09T02:52:29.327132+00:00
elapsed_seconds: 0
remaining_seconds: 5399
[cli/v1] success
attempt_id: 297906d1-f331-4e99-b35c-173c817a9e71
level: 1
prompt: # Scenario

Your task is to implement a simplified version of a file hosting service.
All operations that should be supported are listed below. Partial credit will be granted for each test passed, so
press “Submit” often to run tests and receive partial credits for passed tests. Please check tests for requirements
and argument types.

### Implementation Tips

Read the question all the way through before you start coding, but implement the operations and complete the
levels one by one, not all together, keeping in mind that you will need to refactor to support additional functionality.
Please, do not change the existing method signatures.

## Task

Example of file structure with various files:

```plaintext
[server34] - 24000 Bytes Limit
    Size
    +- file-1.zip 4321 Bytes
    +- dir-a
    |   +- dir-c
    |   |   +- file-2.txt 1100 Bytes
    |   |   +- file-3.csv 2122 Bytes
    +- dir-b
    |   +- file-4.mdx 3378 Bytes
```

## Level 1 – Initial Design & Basic Functions

- **FILE_UPLOAD(file_name, size)**
  - Upload the file to the remote storage server.
  - If a file with the same name already exists on the server, it throws a runtime exception.
- **FILE_GET(file_name)**
  - Returns the size of the file, or nothing if the file doesn’t exist.
- **FILE_COPY(source, dest)**
  - Copy the source file to a new location.
  - If the source file doesn’t exist, it throws a runtime exception.
  - If the destination file already exists, it overwrites the existing file.

test_bad_input_does_not_construct_an_application_or_mutate_workspace (tests.test_cli.CliTests.test_bad_input_does_not_construct_an_application_or_mutate_workspace) ... ok
test_console_adapter_and_module_help_are_identical (tests.test_cli.CliTests.test_console_adapter_and_module_help_are_identical) ... ok
test_domain_errors_have_stable_json_envelopes_and_exits (tests.test_cli.CliTests.test_domain_errors_have_stable_json_envelopes_and_exits) ... ok
test_explicit_selector_is_forwarded_without_active_pointer_fallback (tests.test_cli.CliTests.test_explicit_selector_is_forwarded_without_active_pointer_fallback) ... ok
test_human_success_and_error_envelopes_are_versioned (tests.test_cli.CliTests.test_human_success_and_error_envelopes_are_versioned) ... ok
test_options_are_parsed_after_the_subcommand_and_attempt_is_forwarded (tests.test_cli.CliTests.test_options_are_parsed_after_the_subcommand_and_attempt_is_forwarded) ... ok
test_parse_and_serializer_failures_are_safe_json_input_errors (tests.test_cli.CliTests.test_parse_and_serializer_failures_are_safe_json_input_errors) ... ok
test_parser_exposes_the_documented_command_tree_and_common_options (tests.test_cli.CliTests.test_parser_exposes_the_documented_command_tree_and_common_options) ... ok
test_unexpected_adapter_failure_uses_a_safe_internal_error (tests.test_cli.CliTests.test_unexpected_adapter_failure_uses_a_safe_internal_error) ... ok
test_missing_or_invalid_cache_reports_setup_repair_before_workspace_mutation (tests.test_cli.RuntimeCliTests.test_missing_or_invalid_cache_reports_setup_repair_before_workspace_mutation) ... ok
test_no_or_corrupt_pointer_is_unavailable_but_explicit_selector_precedes_it (tests.test_cli.RuntimeCliTests.test_no_or_corrupt_pointer_is_unavailable_but_explicit_selector_precedes_it) ... ok
test_start_uses_project_fixture_cache_and_persists_full_or_drill_profiles (tests.test_cli.RuntimeCliTests.test_start_uses_project_fixture_cache_and_persists_full_or_drill_profiles) ... ok
test_status_and_time_expire_once_and_final_resume_does_not_mutate (tests.test_cli.RuntimeCliTests.test_status_and_time_expire_once_and_final_resume_does_not_mutate) ... ok
test_submitted_resume_does_not_mutate (tests.test_cli.RuntimeCliTests.test_submitted_resume_does_not_mutate) ... ok
test_task_reads_only_copied_selected_prompt_and_validates_level (tests.test_cli.RuntimeCliTests.test_task_reads_only_copied_selected_prompt_and_validates_level) ... ok

----------------------------------------------------------------------
Ran 15 tests in 0.114s

OK
M  docs/cli-contract.md
M  src/codesignal_practice_simulator/cli.py
M  src/codesignal_practice_simulator/workspace.py
A  tests/test_cli.py
M  tests/test_rendering.py
M  tests/test_workspace.py

verification exit code: 0
