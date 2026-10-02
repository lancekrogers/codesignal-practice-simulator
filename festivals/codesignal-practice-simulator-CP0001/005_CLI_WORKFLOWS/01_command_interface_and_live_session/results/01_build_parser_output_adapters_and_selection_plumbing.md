test_bad_input_does_not_construct_an_application_or_mutate_workspace (tests.test_cli.CliTests.test_bad_input_does_not_construct_an_application_or_mutate_workspace) ... ok
test_console_adapter_and_module_help_are_identical (tests.test_cli.CliTests.test_console_adapter_and_module_help_are_identical) ... ok
test_domain_errors_have_stable_json_envelopes_and_exits (tests.test_cli.CliTests.test_domain_errors_have_stable_json_envelopes_and_exits) ... ok
test_explicit_selector_is_forwarded_without_active_pointer_fallback (tests.test_cli.CliTests.test_explicit_selector_is_forwarded_without_active_pointer_fallback) ... ok
test_human_success_and_error_envelopes_are_versioned (tests.test_cli.CliTests.test_human_success_and_error_envelopes_are_versioned) ... ok
test_options_are_parsed_after_the_subcommand_and_attempt_is_forwarded (tests.test_cli.CliTests.test_options_are_parsed_after_the_subcommand_and_attempt_is_forwarded) ... ok
test_parse_and_serializer_failures_are_safe_json_input_errors (tests.test_cli.CliTests.test_parse_and_serializer_failures_are_safe_json_input_errors) ... ok
test_parser_exposes_the_documented_command_tree_and_common_options (tests.test_cli.CliTests.test_parser_exposes_the_documented_command_tree_and_common_options) ... ok
test_unexpected_adapter_failure_uses_a_safe_internal_error (tests.test_cli.CliTests.test_unexpected_adapter_failure_uses_a_safe_internal_error) ... ok

----------------------------------------------------------------------
Ran 9 tests in 0.053s

OK
usage: codesignal-sim [-h] [--version] COMMAND ...

CodeSignal Practice Simulator

positional arguments:
  COMMAND
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
usage: codesignal-sim [-h] [--version] COMMAND ...

CodeSignal Practice Simulator

positional arguments:
  COMMAND
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
test_bad_input_does_not_construct_an_application_or_mutate_workspace (test_cli.CliTests.test_bad_input_does_not_construct_an_application_or_mutate_workspace) ... ok
test_console_adapter_and_module_help_are_identical (test_cli.CliTests.test_console_adapter_and_module_help_are_identical) ... ok
test_domain_errors_have_stable_json_envelopes_and_exits (test_cli.CliTests.test_domain_errors_have_stable_json_envelopes_and_exits) ... ok
test_explicit_selector_is_forwarded_without_active_pointer_fallback (test_cli.CliTests.test_explicit_selector_is_forwarded_without_active_pointer_fallback) ... ok
test_human_success_and_error_envelopes_are_versioned (test_cli.CliTests.test_human_success_and_error_envelopes_are_versioned) ... ok
test_options_are_parsed_after_the_subcommand_and_attempt_is_forwarded (test_cli.CliTests.test_options_are_parsed_after_the_subcommand_and_attempt_is_forwarded) ... ok
test_parse_and_serializer_failures_are_safe_json_input_errors (test_cli.CliTests.test_parse_and_serializer_failures_are_safe_json_input_errors) ... ok
test_parser_exposes_the_documented_command_tree_and_common_options (test_cli.CliTests.test_parser_exposes_the_documented_command_tree_and_common_options) ... ok
test_unexpected_adapter_failure_uses_a_safe_internal_error (test_cli.CliTests.test_unexpected_adapter_failure_uses_a_safe_internal_error) ... ok
test_corrupt_active_selection_fails_but_explicit_selection_still_works (test_lifecycle.LifecycleTests.test_corrupt_active_selection_fails_but_explicit_selection_still_works) ... ok
test_expired_resume_and_test_are_exit_four_and_byte_identical (test_lifecycle.LifecycleTests.test_expired_resume_and_test_are_exit_four_and_byte_identical) ... ok
test_expiring_one_attempt_leaves_neighbor_bytes_unchanged (test_lifecycle.LifecycleTests.test_expiring_one_attempt_leaves_neighbor_bytes_unchanged) ... ok
test_explicit_active_resume_replaces_selection (test_lifecycle.LifecycleTests.test_explicit_active_resume_replaces_selection) ... ok
test_first_overdue_status_observer_persists_exactly_one_expiry (test_lifecycle.LifecycleTests.test_first_overdue_status_observer_persists_exactly_one_expiry) ... ok
test_lock_contention_returns_exit_four_and_preserves_neighboring_attempt (test_lifecycle.LifecycleTests.test_lock_contention_returns_exit_four_and_preserves_neighboring_attempt) ... ok
test_next_command_recovers_a_missing_event_for_the_current_revision (test_lifecycle.LifecycleTests.test_next_command_recovers_a_missing_event_for_the_current_revision) ... ok
test_overdue_submit_persists_expiry_before_one_submission (test_lifecycle.LifecycleTests.test_overdue_submit_persists_expiry_before_one_submission) ... ok
test_record_test_result_updates_active_state_under_one_revision (test_lifecycle.LifecycleTests.test_record_test_result_updates_active_state_under_one_revision) ... ok
test_repeat_submit_without_scorer_preserves_submitted_missing_event_bytes (test_lifecycle.LifecycleTests.test_repeat_submit_without_scorer_preserves_submitted_missing_event_bytes) ... ok
test_start_creates_selected_full_or_drill_attempt (test_lifecycle.LifecycleTests.test_start_creates_selected_full_or_drill_attempt) ... ok
test_status_and_time_before_deadline_are_safe_reads (test_lifecycle.LifecycleTests.test_status_and_time_before_deadline_are_safe_reads) ... ok
test_submit_active_and_repeat_submit_returns_the_stored_result_without_writes (test_lifecycle.LifecycleTests.test_submit_active_and_repeat_submit_returns_the_stored_result_without_writes) ... ok
test_submit_finalizes_a_previously_expired_attempt_once (test_lifecycle.LifecycleTests.test_submit_finalizes_a_previously_expired_attempt_once) ... ok
test_submitted_attempt_refuses_resume_and_test_without_mutation (test_lifecycle.LifecycleTests.test_submitted_attempt_refuses_resume_and_test_without_mutation) ... ok
test_terminal_commands_do_not_recover_a_missing_current_event (test_lifecycle.LifecycleTests.test_terminal_commands_do_not_recover_a_missing_current_event) ... ok
test_test_runs_injected_scorer_then_records_result (test_lifecycle.LifecycleTests.test_test_runs_injected_scorer_then_records_result) ... ok
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
test_invalid_pointer_is_a_corruption_error (test_persistence.PersistenceTests.test_invalid_pointer_is_a_corruption_error) ... ok
test_jsonl_rejects_bad_nonfinal_records_and_only_ignores_one_tail (test_persistence.PersistenceTests.test_jsonl_rejects_bad_nonfinal_records_and_only_ignores_one_tail) ... ok
test_locked_recovery_does_not_reacquire_the_attempt_lock (test_persistence.PersistenceTests.test_locked_recovery_does_not_reacquire_the_attempt_lock) ... ok
test_pointer_write_faults_preserve_previous_pointer_bytes (test_persistence.PersistenceTests.test_pointer_write_faults_preserve_previous_pointer_bytes) ... ok
test_recovery_appends_one_event_for_a_missing_authoritative_revision (test_persistence.PersistenceTests.test_recovery_appends_one_event_for_a_missing_authoritative_revision) ... ok
test_recovery_rejects_event_records_owned_by_another_attempt (test_persistence.PersistenceTests.test_recovery_rejects_event_records_owned_by_another_attempt) ... ok
test_session_and_pointer_use_flushed_sibling_replacements (test_persistence.PersistenceTests.test_session_and_pointer_use_flushed_sibling_replacements) ... ok
test_state_write_faults_preserve_previous_session_bytes (test_persistence.PersistenceTests.test_state_write_faults_preserve_previous_session_bytes) ... ok
test_attempt_templates_state_the_operational_boundary (test_rendering.RenderingTests.test_attempt_templates_state_the_operational_boundary) ... ok
test_coaching_and_regenerated_status_preserve_candidate_state_cache_and_reference (test_rendering.RenderingTests.test_coaching_and_regenerated_status_preserve_candidate_state_cache_and_reference) ... ok
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
test_corrupt_pointer_and_explicit_selection_precedence (test_workspace.WorkspaceTests.test_corrupt_pointer_and_explicit_selection_precedence) ... ok
test_creation_copies_only_six_assessment_files_and_keeps_cache_immutable (test_workspace.WorkspaceTests.test_creation_copies_only_six_assessment_files_and_keeps_cache_immutable) ... ok
test_every_creation_filesystem_failure_rolls_back_only_new_attempt (test_workspace.WorkspaceTests.test_every_creation_filesystem_failure_rolls_back_only_new_attempt)
Exercise every individual mkdir/copy/write/flush/replace creation call. ... ok
test_hash_invalid_cache_creates_nothing (test_workspace.WorkspaceTests.test_hash_invalid_cache_creates_nothing) ... ok
test_invalid_or_absent_cache_creates_nothing (test_workspace.WorkspaceTests.test_invalid_or_absent_cache_creates_nothing) ... ok
test_publish_before_pointer_interruption_reconciles_only_owned_attempt (test_workspace.WorkspaceTests.test_publish_before_pointer_interruption_reconciles_only_owned_attempt) ... ok
test_reconciliation_never_deletes_unowned_or_pointer_selected_attempt (test_workspace.WorkspaceTests.test_reconciliation_never_deletes_unowned_or_pointer_selected_attempt) ... ok

----------------------------------------------------------------------
Ran 92 tests in 2.329s

OK
test_bad_input_does_not_construct_an_application_or_mutate_workspace (test_cli.CliTests) ... ok
test_console_adapter_and_module_help_are_identical (test_cli.CliTests) ... ok
test_domain_errors_have_stable_json_envelopes_and_exits (test_cli.CliTests) ... ok
test_explicit_selector_is_forwarded_without_active_pointer_fallback (test_cli.CliTests) ... ok
test_human_success_and_error_envelopes_are_versioned (test_cli.CliTests) ... ok
test_options_are_parsed_after_the_subcommand_and_attempt_is_forwarded (test_cli.CliTests) ... ok
test_parse_and_serializer_failures_are_safe_json_input_errors (test_cli.CliTests) ... ok
test_parser_exposes_the_documented_command_tree_and_common_options (test_cli.CliTests) ... ok
test_unexpected_adapter_failure_uses_a_safe_internal_error (test_cli.CliTests) ... ok
test_corrupt_active_selection_fails_but_explicit_selection_still_works (test_lifecycle.LifecycleTests) ... ok
test_expired_resume_and_test_are_exit_four_and_byte_identical (test_lifecycle.LifecycleTests) ... ok
test_expiring_one_attempt_leaves_neighbor_bytes_unchanged (test_lifecycle.LifecycleTests) ... ok
test_explicit_active_resume_replaces_selection (test_lifecycle.LifecycleTests) ... ok
test_first_overdue_status_observer_persists_exactly_one_expiry (test_lifecycle.LifecycleTests) ... ok
test_lock_contention_returns_exit_four_and_preserves_neighboring_attempt (test_lifecycle.LifecycleTests) ... ok
test_next_command_recovers_a_missing_event_for_the_current_revision (test_lifecycle.LifecycleTests) ... ok
test_overdue_submit_persists_expiry_before_one_submission (test_lifecycle.LifecycleTests) ... ok
test_record_test_result_updates_active_state_under_one_revision (test_lifecycle.LifecycleTests) ... ok
test_repeat_submit_without_scorer_preserves_submitted_missing_event_bytes (test_lifecycle.LifecycleTests) ... ok
test_start_creates_selected_full_or_drill_attempt (test_lifecycle.LifecycleTests) ... ok
test_status_and_time_before_deadline_are_safe_reads (test_lifecycle.LifecycleTests) ... ok
test_submit_active_and_repeat_submit_returns_the_stored_result_without_writes (test_lifecycle.LifecycleTests) ... ok
test_submit_finalizes_a_previously_expired_attempt_once (test_lifecycle.LifecycleTests) ... ok
test_submitted_attempt_refuses_resume_and_test_without_mutation (test_lifecycle.LifecycleTests) ... ok
test_terminal_commands_do_not_recover_a_missing_current_event (test_lifecycle.LifecycleTests) ... ok
test_test_runs_injected_scorer_then_records_result (test_lifecycle.LifecycleTests) ... ok
test_absent_cache_requires_setup (test_migration.FetchFixtureTests) ... ok
test_complete_source_setup_includes_vendor_readme (test_migration.FetchFixtureTests) ... ok
test_hash_mismatch_preserves_existing_cache (test_migration.FetchFixtureTests) ... ok
test_incomplete_local_source_does_not_publish_cache (test_migration.FetchFixtureTests) ... ok
test_invalid_manifest_path_is_rejected (test_migration.FetchFixtureTests) ... ok
test_mocked_downloader_failure_does_not_publish_cache (test_migration.FetchFixtureTests) ... ok
test_git_boundary_rejects_head_vendor_hash (test_migration.ManifestVerifierTests) ... ok
test_git_boundary_rejects_head_vendor_path (test_migration.ManifestVerifierTests) ... ok
test_git_boundary_rejects_staged_vendor_hash (test_migration.ManifestVerifierTests) ... ok
test_git_boundary_rejects_staged_vendor_path (test_migration.ManifestVerifierTests) ... ok
test_git_boundary_safe_control (test_migration.ManifestVerifierTests) ... ok
test_real_project_does_not_track_fixture_contents (test_migration.ManifestVerifierTests) ... ok
test_attempt_uses_its_copied_tests (test_migration.ScorecardFixtureTests) ... ok
test_solution_uses_cached_tests_with_solution_as_the_candidate (test_migration.ScorecardFixtureTests) ... ok
test_clock_protocol_accepts_a_fake_clock_and_utc_clock_returns_utc (test_models.ErrorAndClockTests) ... ok
test_domain_errors_have_stable_exit_classes (test_models.ErrorAndClockTests) ... ok
test_assessment_profile_score_session_and_pointer_round_trip (test_models.ModelRoundTripTests) ... ok
test_drill_profile_persists_an_explicit_duration_override (test_models.ModelRoundTripTests) ... ok
test_event_round_trip_and_arguments_are_immutable (test_models.ModelRoundTripTests) ... ok
test_score_summary_derives_counts_from_independent_results (test_models.ModelRoundTripTests) ... ok
test_active_pointer_rejects_unknown_schema_invalid_id_and_extra_field (test_models.SchemaValidationTests) ... ok
test_assessment_rejects_unknown_and_malformed_values (test_models.SchemaValidationTests) ... ok
test_event_rejects_invalid_schema_ids_timestamps_and_arguments (test_models.SchemaValidationTests) ... ok
test_profile_rejects_unknown_profile_mode_and_duration (test_models.SchemaValidationTests) ... ok
test_score_rejects_every_invalid_four_level_shape (test_models.SchemaValidationTests) ... ok
test_session_rejects_deadline_order_and_duration_mismatch (test_models.SchemaValidationTests) ... ok
test_session_rejects_illegal_submission_combinations (test_models.SchemaValidationTests) ... ok
test_session_rejects_malformed_ids_and_revisions (test_models.SchemaValidationTests) ... ok
test_session_rejects_malformed_score_object (test_models.SchemaValidationTests) ... ok
test_session_rejects_naive_non_utc_and_malformed_timestamps (test_models.SchemaValidationTests) ... ok
test_session_rejects_unsupported_schema_and_invalid_field_sets (test_models.SchemaValidationTests) ... ok
test_attempt_and_workspace_locks_reject_contention (test_persistence.PersistenceTests) ... ok
test_event_schema_corruption_is_not_an_incomplete_tail (test_persistence.PersistenceTests) ... ok
test_invalid_pointer_is_a_corruption_error (test_persistence.PersistenceTests) ... ok
test_jsonl_rejects_bad_nonfinal_records_and_only_ignores_one_tail (test_persistence.PersistenceTests) ... ok
test_locked_recovery_does_not_reacquire_the_attempt_lock (test_persistence.PersistenceTests) ... ok
test_pointer_write_faults_preserve_previous_pointer_bytes (test_persistence.PersistenceTests) ... ok
test_recovery_appends_one_event_for_a_missing_authoritative_revision (test_persistence.PersistenceTests) ... ok
test_recovery_rejects_event_records_owned_by_another_attempt (test_persistence.PersistenceTests) ... ok
test_session_and_pointer_use_flushed_sibling_replacements (test_persistence.PersistenceTests) ... ok
test_state_write_faults_preserve_previous_session_bytes (test_persistence.PersistenceTests) ... ok
test_attempt_templates_state_the_operational_boundary (test_rendering.RenderingTests) ... ok
test_coaching_and_regenerated_status_preserve_candidate_state_cache_and_reference (test_rendering.RenderingTests) ... ok
test_invalid_session_or_events_return_unavailable_without_status_write (test_rendering.RenderingTests) ... ok
test_lifecycle_transition_never_renders_and_explicit_refresh_uses_latest_state (test_rendering.RenderingTests) ... ok
test_markdown_and_json_contain_only_safe_derived_context (test_rendering.RenderingTests) ... ok
test_renderer_failure_preserves_candidate_state_cache_and_reference_bytes (test_rendering.RenderingTests) ... ok
test_candidate_fork_for_setsid_is_rejected_without_creating_a_child (test_scoring.ScoringTests) ... ok
test_coaching_status_and_cache_changes_do_not_affect_candidate_only_score (test_scoring.ScoringTests) ... ok
test_failure_crash_timeout_and_missing_input_do_not_skip_later_groups (test_scoring.ScoringTests) ... ok
test_isolation_excludes_editable_install_pythonpath_and_loose_reference (test_scoring.ScoringTests) ... ok
test_launch_error_is_recorded_for_each_group (test_scoring.ScoringTests) ... ok
test_lifecycle_persists_four_independent_results_from_exact_launches (test_scoring.ScoringTests) ... ok
test_output_is_bounded (test_scoring.ScoringTests) ... ok
test_registry_has_only_file_storage_with_its_complete_contract (test_scoring.ScoringTests) ... ok
test_runner_rejects_an_invalid_group_and_wrong_working_directory (test_scoring.ScoringTests) ... ok
test_setup_required_cache_failure_occurs_before_workspace_mutation (test_scoring.ScoringTests) ... ok
test_timeout_kills_a_detached_descendant_from_the_immediate_snapshot (test_scoring.ScoringTests) ... ok
test_workspace_copies_runner_and_only_registered_candidate_inputs (test_scoring.ScoringTests) ... ok
test_corrupt_pointer_and_explicit_selection_precedence (test_workspace.WorkspaceTests) ... ok
test_creation_copies_only_six_assessment_files_and_keeps_cache_immutable (test_workspace.WorkspaceTests) ... ok
test_every_creation_filesystem_failure_rolls_back_only_new_attempt (test_workspace.WorkspaceTests)
Exercise every individual mkdir/copy/write/flush/replace creation call. ... ok
test_hash_invalid_cache_creates_nothing (test_workspace.WorkspaceTests) ... ok
test_invalid_or_absent_cache_creates_nothing (test_workspace.WorkspaceTests) ... ok
test_publish_before_pointer_interruption_reconciles_only_owned_attempt (test_workspace.WorkspaceTests) ... ok
test_reconciliation_never_deletes_unowned_or_pointer_selected_attempt (test_workspace.WorkspaceTests) ... ok

----------------------------------------------------------------------
Ran 92 tests in 2.183s

OK
Manifest verification passed: tracked
Manifest verification passed: fixture-cache
Manifest verification passed: git-boundary
Manifest verification passed: git-boundary
Manifest verification passed: git-boundary
M  docs/cli-contract.md
M  src/codesignal_practice_simulator/cli.py
A  tests/test_cli.py
