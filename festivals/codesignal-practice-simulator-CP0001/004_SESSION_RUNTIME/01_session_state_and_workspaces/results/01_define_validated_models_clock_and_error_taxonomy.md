$ python3 -m unittest tests.test_models -v
test_clock_protocol_accepts_a_fake_clock_and_utc_clock_returns_utc (tests.test_models.ErrorAndClockTests.test_clock_protocol_accepts_a_fake_clock_and_utc_clock_returns_utc) ... ok
test_domain_errors_have_stable_exit_classes (tests.test_models.ErrorAndClockTests.test_domain_errors_have_stable_exit_classes) ... ok
test_assessment_profile_score_session_and_pointer_round_trip (tests.test_models.ModelRoundTripTests.test_assessment_profile_score_session_and_pointer_round_trip) ... ok
test_drill_profile_persists_an_explicit_duration_override (tests.test_models.ModelRoundTripTests.test_drill_profile_persists_an_explicit_duration_override) ... ok
test_event_round_trip_and_arguments_are_immutable (tests.test_models.ModelRoundTripTests.test_event_round_trip_and_arguments_are_immutable) ... ok
test_score_summary_derives_counts_from_independent_results (tests.test_models.ModelRoundTripTests.test_score_summary_derives_counts_from_independent_results) ... ok
test_active_pointer_rejects_unknown_schema_invalid_id_and_extra_field (tests.test_models.SchemaValidationTests.test_active_pointer_rejects_unknown_schema_invalid_id_and_extra_field) ... ok
test_assessment_rejects_unknown_and_malformed_values (tests.test_models.SchemaValidationTests.test_assessment_rejects_unknown_and_malformed_values) ... ok
test_event_rejects_invalid_schema_ids_timestamps_and_arguments (tests.test_models.SchemaValidationTests.test_event_rejects_invalid_schema_ids_timestamps_and_arguments) ... ok
test_profile_rejects_unknown_profile_mode_and_duration (tests.test_models.SchemaValidationTests.test_profile_rejects_unknown_profile_mode_and_duration) ... ok
test_score_rejects_every_invalid_four_level_shape (tests.test_models.SchemaValidationTests.test_score_rejects_every_invalid_four_level_shape) ... ok
test_session_rejects_deadline_order_and_duration_mismatch (tests.test_models.SchemaValidationTests.test_session_rejects_deadline_order_and_duration_mismatch) ... ok
test_session_rejects_illegal_submission_combinations (tests.test_models.SchemaValidationTests.test_session_rejects_illegal_submission_combinations) ... ok
test_session_rejects_malformed_ids_and_revisions (tests.test_models.SchemaValidationTests.test_session_rejects_malformed_ids_and_revisions) ... ok
test_session_rejects_malformed_score_object (tests.test_models.SchemaValidationTests.test_session_rejects_malformed_score_object) ... ok
test_session_rejects_naive_non_utc_and_malformed_timestamps (tests.test_models.SchemaValidationTests.test_session_rejects_naive_non_utc_and_malformed_timestamps) ... ok
test_session_rejects_unsupported_schema_and_invalid_field_sets (tests.test_models.SchemaValidationTests.test_session_rejects_unsupported_schema_and_invalid_field_sets) ... ok

----------------------------------------------------------------------
Ran 17 tests in 0.002s

OK
[exit 0]
$ python3 -m unittest discover -s tests -p 'test_models.py' -v
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

----------------------------------------------------------------------
Ran 17 tests in 0.002s

OK
[exit 0]
$ python3.10 -m unittest tests.test_models -v
test_clock_protocol_accepts_a_fake_clock_and_utc_clock_returns_utc (tests.test_models.ErrorAndClockTests) ... ok
test_domain_errors_have_stable_exit_classes (tests.test_models.ErrorAndClockTests) ... ok
test_assessment_profile_score_session_and_pointer_round_trip (tests.test_models.ModelRoundTripTests) ... ok
test_drill_profile_persists_an_explicit_duration_override (tests.test_models.ModelRoundTripTests) ... ok
test_event_round_trip_and_arguments_are_immutable (tests.test_models.ModelRoundTripTests) ... ok
test_score_summary_derives_counts_from_independent_results (tests.test_models.ModelRoundTripTests) ... ok
test_active_pointer_rejects_unknown_schema_invalid_id_and_extra_field (tests.test_models.SchemaValidationTests) ... ok
test_assessment_rejects_unknown_and_malformed_values (tests.test_models.SchemaValidationTests) ... ok
test_event_rejects_invalid_schema_ids_timestamps_and_arguments (tests.test_models.SchemaValidationTests) ... ok
test_profile_rejects_unknown_profile_mode_and_duration (tests.test_models.SchemaValidationTests) ... ok
test_score_rejects_every_invalid_four_level_shape (tests.test_models.SchemaValidationTests) ... ok
test_session_rejects_deadline_order_and_duration_mismatch (tests.test_models.SchemaValidationTests) ... ok
test_session_rejects_illegal_submission_combinations (tests.test_models.SchemaValidationTests) ... ok
test_session_rejects_malformed_ids_and_revisions (tests.test_models.SchemaValidationTests) ... ok
test_session_rejects_malformed_score_object (tests.test_models.SchemaValidationTests) ... ok
test_session_rejects_naive_non_utc_and_malformed_timestamps (tests.test_models.SchemaValidationTests) ... ok
test_session_rejects_unsupported_schema_and_invalid_field_sets (tests.test_models.SchemaValidationTests) ... ok

----------------------------------------------------------------------
Ran 17 tests in 0.002s

OK
[exit 0]
$ python3.10 -m unittest discover -s tests -p 'test_models.py' -v
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

----------------------------------------------------------------------
Ran 17 tests in 0.002s

OK
[exit 0]
$ python3 -m unittest discover -s tests -p 'test_*.py' -v
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

----------------------------------------------------------------------
Ran 31 tests in 0.431s

OK
[exit 0]
$ just test-all
cd /workspace/campaign/projects/codesignal-practice-simulator/solution && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="/workspace/campaign/projects/codesignal-practice-simulator/solution:/workspace/campaign/projects/codesignal-practice-simulator/.cache/codesignal-fixtures/6aab304/assessment/file_storage" python3 -m unittest -v test_simulation
test_group_1 (test_simulation.TestSimulateCodingFramework.test_group_1) ... ok
test_group_2 (test_simulation.TestSimulateCodingFramework.test_group_2) ... ok
test_group_3 (test_simulation.TestSimulateCodingFramework.test_group_3) ... ok
test_group_4 (test_simulation.TestSimulateCodingFramework.test_group_4) ... ok

----------------------------------------------------------------------
Ran 4 tests in 0.000s

OK
cd /workspace/campaign/projects/codesignal-practice-simulator/solution && python3 -m unittest -v test_spec
test_group_4_with_real_rollback (test_spec.TestBundledScriptUnderSpecSemantics.test_group_4_with_real_rollback) ... ok
test_copy_missing_source_raises (test_spec.TestLevel1.test_copy_missing_source_raises) ... ok
test_copy_overwrites_existing_destination (test_spec.TestLevel1.test_copy_overwrites_existing_destination) ... ok
test_duplicate_upload_raises (test_spec.TestLevel1.test_duplicate_upload_raises) ... ok
test_get_missing_file_returns_nothing (test_spec.TestLevel1.test_get_missing_file_returns_nothing) ... ok
test_missing_get_is_reported_in_the_output_log (test_spec.TestLevel1.test_missing_get_is_reported_in_the_output_log) ... ok
test_upload_then_get_returns_size (test_spec.TestLevel1.test_upload_then_get_returns_size) ... ok
test_orders_by_size_descending_then_name (test_spec.TestLevel2.test_orders_by_size_descending_then_name) ... ok
test_prefix_must_match_the_start_of_the_name (test_spec.TestLevel2.test_prefix_must_match_the_start_of_the_name) ... ok
test_returns_at_most_ten_files (test_spec.TestLevel2.test_returns_at_most_ten_files) ... ok
test_copy_dies_when_the_original_would_have (test_spec.TestLevel3.test_copy_dies_when_the_original_would_have) ... ok
test_copying_an_expired_source_raises (test_spec.TestLevel3.test_copying_an_expired_source_raises) ... ok
test_expired_files_are_hidden_from_search (test_spec.TestLevel3.test_expired_files_are_hidden_from_search) ... ok
test_expired_name_can_be_reused (test_spec.TestLevel3.test_expired_name_can_be_reused) ... ok
test_file_without_ttl_lives_forever (test_spec.TestLevel3.test_file_without_ttl_lives_forever) ... ok
test_ttl_boundary_is_half_open (test_spec.TestLevel3.test_ttl_boundary_is_half_open) ... ok
test_a_file_that_had_already_expired_does_not_return (test_spec.TestLevel4Rollback.test_a_file_that_had_already_expired_does_not_return) ... ok
test_copies_made_after_the_target_are_dropped (test_spec.TestLevel4Rollback.test_copies_made_after_the_target_are_dropped) ... ok
test_files_created_after_the_target_are_dropped (test_spec.TestLevel4Rollback.test_files_created_after_the_target_are_dropped) ... ok
test_operations_exactly_at_the_target_are_kept (test_spec.TestLevel4Rollback.test_operations_exactly_at_the_target_are_kept) ... ok
test_rollback_is_repeatable (test_spec.TestLevel4Rollback.test_rollback_is_repeatable) ... ok
test_ttls_are_recalculated_from_the_original_upload (test_spec.TestLevel4Rollback.test_ttls_are_recalculated_from_the_original_upload) ... ok
test_untimed_uploads_survive_any_rollback (test_spec.TestLevel4Rollback.test_untimed_uploads_survive_any_rollback) ... ok
test_sizes_compare_numerically_not_lexicographically (test_spec.TestSizeParsing.test_sizes_compare_numerically_not_lexicographically) ... ok
test_units_are_normalised_to_bytes (test_spec.TestSizeParsing.test_units_are_normalised_to_bytes) ... ok
test_unparseable_size_is_rejected (test_spec.TestSizeParsing.test_unparseable_size_is_rejected) ... ok

----------------------------------------------------------------------
Ran 26 tests in 0.001s

OK
cd /workspace/campaign/projects/codesignal-practice-simulator/solution && python3 -m unittest -v test_stages
test_basic_operations (test_stages.TestLevel1.test_basic_operations) ... ok
test_copy_overwrites_destination (test_stages.TestLevel1.test_copy_overwrites_destination) ... ok
test_duplicate_upload_raises (test_stages.TestLevel1.test_duplicate_upload_raises) ... ok
test_keeps_level_1_working (test_stages.TestLevel2.test_keeps_level_1_working) ... ok
test_searches_by_size_then_name (test_stages.TestLevel2.test_searches_by_size_then_name) ... ok
test_vendor_example (test_stages.TestLevel2.test_vendor_example) ... ok
test_file_expires_exactly_at_ttl_boundary (test_stages.TestLevel3.test_file_expires_exactly_at_ttl_boundary) ... ok
test_keeps_earlier_levels_working (test_stages.TestLevel3.test_keeps_earlier_levels_working) ... ok
test_timestamped_operations_and_expiration (test_stages.TestLevel3.test_timestamped_operations_and_expiration) ... ok
test_keeps_earlier_levels_working (test_stages.TestLevel4.test_keeps_earlier_levels_working) ... ok
test_rollback_can_be_repeated (test_stages.TestLevel4.test_rollback_can_be_repeated) ... ok
test_rollback_restores_the_requested_state (test_stages.TestLevel4.test_rollback_restores_the_requested_state) ... ok

----------------------------------------------------------------------
Ran 12 tests in 0.000s

OK
[exit 0]
$ python3 scripts/verify_manifest.py --manifest docs/migration-manifest.json --scope git-boundary
Manifest verification passed: git-boundary
[exit 0]
$ .githooks/pre-commit
Manifest verification passed: git-boundary
[exit 0]
$ .githooks/pre-push
Manifest verification passed: git-boundary
[exit 0]
$ git diff --check
[exit 0]
$ git diff --cached --check
[exit 0]
$ git status --short
A  docs/cli-contract.md
A  src/codesignal_practice_simulator/clock.py
A  src/codesignal_practice_simulator/errors.py
A  src/codesignal_practice_simulator/models.py
A  tests/test_models.py
[exit 0]
