test_attempt_and_workspace_locks_reject_contention (tests.test_persistence.PersistenceTests.test_attempt_and_workspace_locks_reject_contention) ... ok
test_event_schema_corruption_is_not_an_incomplete_tail (tests.test_persistence.PersistenceTests.test_event_schema_corruption_is_not_an_incomplete_tail) ... ok
test_invalid_pointer_is_a_corruption_error (tests.test_persistence.PersistenceTests.test_invalid_pointer_is_a_corruption_error) ... ok
test_jsonl_rejects_bad_nonfinal_records_and_only_ignores_one_tail (tests.test_persistence.PersistenceTests.test_jsonl_rejects_bad_nonfinal_records_and_only_ignores_one_tail) ... ok
test_pointer_write_faults_preserve_previous_pointer_bytes (tests.test_persistence.PersistenceTests.test_pointer_write_faults_preserve_previous_pointer_bytes) ... ok
test_recovery_appends_one_event_for_a_missing_authoritative_revision (tests.test_persistence.PersistenceTests.test_recovery_appends_one_event_for_a_missing_authoritative_revision) ... ok
test_recovery_rejects_event_records_owned_by_another_attempt (tests.test_persistence.PersistenceTests.test_recovery_rejects_event_records_owned_by_another_attempt) ... ok
test_session_and_pointer_use_flushed_sibling_replacements (tests.test_persistence.PersistenceTests.test_session_and_pointer_use_flushed_sibling_replacements) ... ok
test_state_write_faults_preserve_previous_session_bytes (tests.test_persistence.PersistenceTests.test_state_write_faults_preserve_previous_session_bytes) ... ok
test_corrupt_pointer_and_explicit_selection_precedence (tests.test_workspace.WorkspaceTests.test_corrupt_pointer_and_explicit_selection_precedence) ... ok
test_creation_copies_only_six_assessment_files_and_keeps_cache_immutable (tests.test_workspace.WorkspaceTests.test_creation_copies_only_six_assessment_files_and_keeps_cache_immutable) ... ok
test_every_creation_filesystem_failure_rolls_back_only_new_attempt (tests.test_workspace.WorkspaceTests.test_every_creation_filesystem_failure_rolls_back_only_new_attempt)
Exercise every individual mkdir/copy/write/flush/replace creation call. ... ok
test_hash_invalid_cache_creates_nothing (tests.test_workspace.WorkspaceTests.test_hash_invalid_cache_creates_nothing) ... ok
test_invalid_or_absent_cache_creates_nothing (tests.test_workspace.WorkspaceTests.test_invalid_or_absent_cache_creates_nothing) ... ok
test_publish_before_pointer_interruption_reconciles_only_owned_attempt (tests.test_workspace.WorkspaceTests.test_publish_before_pointer_interruption_reconciles_only_owned_attempt) ... ok
test_reconciliation_never_deletes_unowned_or_pointer_selected_attempt (tests.test_workspace.WorkspaceTests.test_reconciliation_never_deletes_unowned_or_pointer_selected_attempt) ... ok

----------------------------------------------------------------------
Ran 16 tests in 0.203s

OK
test_attempt_and_workspace_locks_reject_contention (test_persistence.PersistenceTests.test_attempt_and_workspace_locks_reject_contention) ... ok
test_event_schema_corruption_is_not_an_incomplete_tail (test_persistence.PersistenceTests.test_event_schema_corruption_is_not_an_incomplete_tail) ... ok
test_invalid_pointer_is_a_corruption_error (test_persistence.PersistenceTests.test_invalid_pointer_is_a_corruption_error) ... ok
test_jsonl_rejects_bad_nonfinal_records_and_only_ignores_one_tail (test_persistence.PersistenceTests.test_jsonl_rejects_bad_nonfinal_records_and_only_ignores_one_tail) ... ok
test_pointer_write_faults_preserve_previous_pointer_bytes (test_persistence.PersistenceTests.test_pointer_write_faults_preserve_previous_pointer_bytes) ... ok
test_recovery_appends_one_event_for_a_missing_authoritative_revision (test_persistence.PersistenceTests.test_recovery_appends_one_event_for_a_missing_authoritative_revision) ... ok
test_recovery_rejects_event_records_owned_by_another_attempt (test_persistence.PersistenceTests.test_recovery_rejects_event_records_owned_by_another_attempt) ... ok
test_session_and_pointer_use_flushed_sibling_replacements (test_persistence.PersistenceTests.test_session_and_pointer_use_flushed_sibling_replacements) ... ok
test_state_write_faults_preserve_previous_session_bytes (test_persistence.PersistenceTests.test_state_write_faults_preserve_previous_session_bytes) ... ok

----------------------------------------------------------------------
Ran 9 tests in 0.010s

OK
test_corrupt_pointer_and_explicit_selection_precedence (test_workspace.WorkspaceTests.test_corrupt_pointer_and_explicit_selection_precedence) ... ok
test_creation_copies_only_six_assessment_files_and_keeps_cache_immutable (test_workspace.WorkspaceTests.test_creation_copies_only_six_assessment_files_and_keeps_cache_immutable) ... ok
test_every_creation_filesystem_failure_rolls_back_only_new_attempt (test_workspace.WorkspaceTests.test_every_creation_filesystem_failure_rolls_back_only_new_attempt)
Exercise every individual mkdir/copy/write/flush/replace creation call. ... ok
test_hash_invalid_cache_creates_nothing (test_workspace.WorkspaceTests.test_hash_invalid_cache_creates_nothing) ... ok
test_invalid_or_absent_cache_creates_nothing (test_workspace.WorkspaceTests.test_invalid_or_absent_cache_creates_nothing) ... ok
test_publish_before_pointer_interruption_reconciles_only_owned_attempt (test_workspace.WorkspaceTests.test_publish_before_pointer_interruption_reconciles_only_owned_attempt) ... ok
test_reconciliation_never_deletes_unowned_or_pointer_selected_attempt (test_workspace.WorkspaceTests.test_reconciliation_never_deletes_unowned_or_pointer_selected_attempt) ... ok

----------------------------------------------------------------------
Ran 7 tests in 0.196s

OK
A  docs/cli-contract.md
A  src/codesignal_practice_simulator/clock.py
A  src/codesignal_practice_simulator/errors.py
A  src/codesignal_practice_simulator/filesystem.py
A  src/codesignal_practice_simulator/models.py
A  src/codesignal_practice_simulator/persistence.py
A  src/codesignal_practice_simulator/workspace.py
A  tests/test_models.py
A  tests/test_persistence.py
A  tests/test_workspace.py
Python 3.10.20
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
test_pointer_write_faults_preserve_previous_pointer_bytes (test_persistence.PersistenceTests) ... ok
test_recovery_appends_one_event_for_a_missing_authoritative_revision (test_persistence.PersistenceTests) ... ok
test_recovery_rejects_event_records_owned_by_another_attempt (test_persistence.PersistenceTests) ... ok
test_session_and_pointer_use_flushed_sibling_replacements (test_persistence.PersistenceTests) ... ok
test_state_write_faults_preserve_previous_session_bytes (test_persistence.PersistenceTests) ... ok
test_corrupt_pointer_and_explicit_selection_precedence (test_workspace.WorkspaceTests) ... ok
test_creation_copies_only_six_assessment_files_and_keeps_cache_immutable (test_workspace.WorkspaceTests) ... ok
test_every_creation_filesystem_failure_rolls_back_only_new_attempt (test_workspace.WorkspaceTests)
Exercise every individual mkdir/copy/write/flush/replace creation call. ... ok
test_hash_invalid_cache_creates_nothing (test_workspace.WorkspaceTests) ... ok
test_invalid_or_absent_cache_creates_nothing (test_workspace.WorkspaceTests) ... ok
test_publish_before_pointer_interruption_reconciles_only_owned_attempt (test_workspace.WorkspaceTests) ... ok
test_reconciliation_never_deletes_unowned_or_pointer_selected_attempt (test_workspace.WorkspaceTests) ... ok

----------------------------------------------------------------------
Ran 47 tests in 0.659s

OK
Manifest verification passed: tracked
Manifest verification passed: fixture-cache
Manifest verification passed: git-boundary
Manifest verification passed: git-boundary
Manifest verification passed: git-boundary
A  docs/cli-contract.md
A  src/codesignal_practice_simulator/clock.py
A  src/codesignal_practice_simulator/errors.py
A  src/codesignal_practice_simulator/filesystem.py
A  src/codesignal_practice_simulator/models.py
A  src/codesignal_practice_simulator/persistence.py
A  src/codesignal_practice_simulator/workspace.py
A  tests/test_models.py
A  tests/test_persistence.py
A  tests/test_workspace.py
