{"ok": true, "result": {"fixture_cache": "/tmp/build/tmp.OZyQmpa9ic/.cache/codesignal-fixtures/6aab304"}, "schema_version": "cli/v1"}
{"ok": true, "result": {"session": {"assessment": {"assessment_id": "file_storage", "display_name": "File Storage", "level_count": 4}, "attempt_id": "7af14521-dc73-4ac7-832e-be5db5c69983", "deadline_at": "2026-09-09T04:24:07.267207+00:00", "profile": {"duration_seconds": 1800, "mode": "drill", "profile_id": "drill-30m"}, "revision": 0, "schema_version": "session/v1", "score": null, "started_at": "2026-09-09T03:54:07.267207+00:00", "status": "active", "submitted_at": null}}, "schema_version": "cli/v1"}
{"ok": true, "result": {"context": "# Attempt status\n\nThis is derived, non-authoritative session context.\n\n## Assessment\n- Assessment: File Storage (`file_storage`)\n- Mode: `drill`\n- Profile: `drill-30m`\n\n## Lifecycle\n- Status: `active`\n- Started: 2026-09-09T03:54:07.267207+00:00\n- Deadline: 2026-09-09T04:24:07.267207+00:00\n\n## Score summary\n- Passed levels: 0 of 0\n- Highest contiguous level: 0\n\n## Event history\n- Revision 0: `started` (succeeded) at 2026-09-09T03:54:07.267207+00:00\n\n## Next legal commands\n- `codesignal-sim status --attempt 7af14521-dc73-4ac7-832e-be5db5c69983`\n- `codesignal-sim context --attempt 7af14521-dc73-4ac7-832e-be5db5c69983`\n- `codesignal-sim resume --attempt 7af14521-dc73-4ac7-832e-be5db5c69983`\n- `codesignal-sim time --attempt 7af14521-dc73-4ac7-832e-be5db5c69983`\n- `codesignal-sim test --attempt 7af14521-dc73-4ac7-832e-be5db5c69983`\n- `codesignal-sim submit --attempt 7af14521-dc73-4ac7-832e-be5db5c69983`\n", "format": "markdown"}, "schema_version": "cli/v1"}
[cli/v1] error (candidate_failure): one or more test groups did not pass
{"ok": true, "result": {"score": {"highest_contiguous_level": 0, "levels": [{"level": 1, "outcome": "error"}, {"level": 2, "outcome": "error"}, {"level": 3, "outcome": "error"}, {"level": 4, "outcome": "error"}], "passed_levels": 0}, "session": {"assessment": {"assessment_id": "file_storage", "display_name": "File Storage", "level_count": 4}, "attempt_id": "7af14521-dc73-4ac7-832e-be5db5c69983", "deadline_at": "2026-09-09T04:24:07.267207+00:00", "profile": {"duration_seconds": 1800, "mode": "drill", "profile_id": "drill-30m"}, "revision": 2, "schema_version": "session/v1", "score": {"highest_contiguous_level": 0, "levels": [{"level": 1, "outcome": "error"}, {"level": 2, "outcome": "error"}, {"level": 3, "outcome": "error"}, {"level": 4, "outcome": "error"}], "passed_levels": 0}, "started_at": "2026-09-09T03:54:07.267207+00:00", "status": "submitted", "submitted_at": "2026-09-09T03:54:07.730837+00:00"}}, "schema_version": "cli/v1"}
{"ok": true, "result": {"score": {"highest_contiguous_level": 0, "levels": [{"level": 1, "outcome": "error"}, {"level": 2, "outcome": "error"}, {"level": 3, "outcome": "error"}, {"level": 4, "outcome": "error"}], "passed_levels": 0}, "session": {"assessment": {"assessment_id": "file_storage", "display_name": "File Storage", "level_count": 4}, "attempt_id": "7af14521-dc73-4ac7-832e-be5db5c69983", "deadline_at": "2026-09-09T04:24:07.267207+00:00", "profile": {"duration_seconds": 1800, "mode": "drill", "profile_id": "drill-30m"}, "revision": 2, "schema_version": "session/v1", "score": {"highest_contiguous_level": 0, "levels": [{"level": 1, "outcome": "error"}, {"level": 2, "outcome": "error"}, {"level": 3, "outcome": "error"}, {"level": 4, "outcome": "error"}], "passed_levels": 0}, "started_at": "2026-09-09T03:54:07.267207+00:00", "status": "submitted", "submitted_at": "2026-09-09T03:54:07.730837+00:00"}}, "schema_version": "cli/v1"}
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
test_submit_is_byte_identical_and_never_rescores_after_finality (tests.test_cli.RuntimeCliTests.test_submit_is_byte_identical_and_never_rescores_after_finality) ... ok
test_submitted_resume_does_not_mutate (tests.test_cli.RuntimeCliTests.test_submitted_resume_does_not_mutate) ... ok
test_task_reads_only_copied_selected_prompt_and_validates_level (tests.test_cli.RuntimeCliTests.test_task_reads_only_copied_selected_prompt_and_validates_level) ... ok
test_test_all_passes_returns_zero_with_isolated_subprocess_score (tests.test_cli.RuntimeCliTests.test_test_all_passes_returns_zero_with_isolated_subprocess_score) ... ok
test_test_persists_all_four_outcomes_and_returns_candidate_failure (tests.test_cli.RuntimeCliTests.test_test_persists_all_four_outcomes_and_returns_candidate_failure) ... ok
test_unregistered_persisted_assessment_is_corrupt_in_json_and_human_output (tests.test_cli.RuntimeCliTests.test_unregistered_persisted_assessment_is_corrupt_in_json_and_human_output) ... ok
test_installed_wheel_fetches_offline_then_starts_outside_checkout (tests.test_cli.WheelRuntimeTests.test_installed_wheel_fetches_offline_then_starts_outside_checkout) ... ok

----------------------------------------------------------------------
Ran 24 tests in 3.019s

OK
 M docs/cli-contract.md
 M src/codesignal_practice_simulator/cli.py
 M src/codesignal_practice_simulator/lifecycle.py
 M src/codesignal_practice_simulator/rendering.py
 M src/codesignal_practice_simulator/workspace.py
 M tests/test_cli.py
 M tests/test_lifecycle.py
 M tests/test_rendering.py
?? src/codesignal_practice_simulator/evaluation.py
