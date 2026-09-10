"""Candidate-document lifecycle, history, and recovery tests."""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from codesignal_practice_simulator.candidate_documents import (
    CandidateDocumentConflictError,
    CandidateDocumentReadOnlyError,
    CandidateDocumentService,
    CandidateDocumentUnavailableError,
    HISTORY_DIRECTORY,
    HISTORY_LIMIT,
    HISTORY_ORDER_FILENAME,
    INITIAL_SOURCE_FILENAME,
)
from codesignal_practice_simulator.models import (
    EXPIRED,
    LevelResult,
    ScoreSummary,
    SUBMITTED,
)
from codesignal_practice_simulator.workspace import WorkspaceManager

try:
    from .candidate_document_test_support import (
        CandidateDocumentTestCase,
        CandidateFailureFilesystem,
    )
except ImportError:
    from candidate_document_test_support import (
        CandidateDocumentTestCase,
        CandidateFailureFilesystem,
    )


class CandidateDocumentLifecycleTests(CandidateDocumentTestCase):
    def test_restore_is_cas_guarded(self) -> None:
        baseline = self.service.read(self.state.attempt_id)
        changed = self.service.save(self.state.attempt_id, "changed\n", baseline.etag)
        snapshot = self.service.list_history(self.state.attempt_id).snapshots[0]
        restored = self.service.restore(
            self.state.attempt_id, snapshot.snapshot_id, changed.etag
        )
        self.assertEqual(restored.content, baseline.content)
        with self.assertRaises(CandidateDocumentConflictError):
            self.service.restore(
                self.state.attempt_id, snapshot.snapshot_id, changed.etag
            )

    def test_reset_changes_source_away_from_baseline_then_restores_it(self) -> None:
        baseline = self.service.read(self.state.attempt_id)
        changed = self.service.save(self.state.attempt_id, "changed\n", baseline.etag)
        self.assertNotEqual(changed.content, baseline.content)
        reset = self.service.reset(self.state.attempt_id, changed.etag)
        self.assertEqual(reset.content, baseline.content)
        self.assertEqual(self.service.read(self.state.attempt_id), baseline)

    def test_expired_and_submitted_mutations_preserve_all_durable_bytes(self) -> None:
        current = self.service.read(self.state.attempt_id)
        changed = self.service.save(self.state.attempt_id, "changed\n", current.etag)
        snapshot = self.service.list_history(self.state.attempt_id).snapshots[0]
        operations = (
            ("save", lambda: self.service.save(
                self.state.attempt_id, "late\n", changed.etag
            )),
            ("restore", lambda: self.service.restore(
                self.state.attempt_id, snapshot.snapshot_id, changed.etag
            )),
            ("reset", lambda: self.service.reset(
                self.state.attempt_id, changed.etag
            )),
        )

        self.clock.value = self.state.deadline_at
        for name, operation in operations:
            with self.subTest(status="expired", operation=name):
                self.assert_rejected_without_mutation(
                    operation, CandidateDocumentReadOnlyError
                )

        submitted = replace(
            self.state,
            status=SUBMITTED,
            revision=1,
            score=ScoreSummary(tuple(LevelResult(level, "passed") for level in range(1, 5))),
            submitted_at=self.state.started_at,
        )
        self.manager.persistence.write_session(self.attempt, submitted)
        self.clock.value = self.state.started_at
        for name, operation in operations:
            with self.subTest(status="submitted", operation=name):
                self.assert_rejected_without_mutation(
                    operation, CandidateDocumentReadOnlyError
                )

    def test_terminal_legacy_mutations_reject_before_initialization(self) -> None:
        current = self.service.read(self.state.attempt_id)
        changed = self.service.save(self.state.attempt_id, "changed\n", current.etag)
        snapshot = self.service.list_history(self.state.attempt_id).snapshots[0]
        (self.attempt / INITIAL_SOURCE_FILENAME).unlink()
        operations = (
            ("save", lambda: self.service.save(
                self.state.attempt_id, "late\n", changed.etag
            )),
            ("restore", lambda: self.service.restore(
                self.state.attempt_id, snapshot.snapshot_id, changed.etag
            )),
            ("reset", lambda: self.service.reset(
                self.state.attempt_id, changed.etag
            )),
        )

        for status in (EXPIRED, SUBMITTED):
            with self.subTest(status=status):
                terminal = replace(
                    self.state,
                    status=status,
                    revision=1,
                    score=(
                        ScoreSummary(
                            tuple(
                                LevelResult(level, "passed")
                                for level in range(1, 5)
                            )
                        )
                        if status == SUBMITTED
                        else None
                    ),
                    submitted_at=self.state.started_at if status == SUBMITTED else None,
                )
                self.manager.persistence.write_session(self.attempt, terminal)
                before = self.attempt_tree_bytes()
                for name, operation in operations:
                    with self.subTest(operation=name):
                        with self.assertRaises(CandidateDocumentReadOnlyError):
                            operation()
                        self.assertEqual(self.attempt_tree_bytes(), before)

    def test_active_legacy_reset_still_initializes_missing_baseline(self) -> None:
        current = self.service.read(self.state.attempt_id)
        (self.attempt / INITIAL_SOURCE_FILENAME).unlink()

        reset = self.service.reset(self.state.attempt_id, current.etag)

        self.assertEqual(reset, current)
        self.assertTrue((self.attempt / INITIAL_SOURCE_FILENAME).is_file())
        self.assertEqual(self.service.read(self.state.attempt_id), current)

    def test_repeated_content_and_noop_keep_oldest_predecessor_restorable(self) -> None:
        baseline = self.service.read(self.state.attempt_id)
        first = self.service.save(self.state.attempt_id, "first\n", baseline.etag)
        second = self.service.save(self.state.attempt_id, "second\n", first.etag)
        repeated = self.service.save(
            self.state.attempt_id, first.content, second.etag
        )
        noop = self.service.save(
            self.state.attempt_id, repeated.content, repeated.etag
        )

        history = self.service.list_history(self.state.attempt_id)

        self.assertEqual(
            [snapshot.content for snapshot in history.snapshots],
            [second.content, first.content, baseline.content],
        )
        self.assertEqual(
            [snapshot.operation_order for snapshot in history.snapshots],
            [3, 2, 1],
        )
        self.assertEqual(
            history.snapshots[0].new_hash,
            history.snapshots[2].new_hash,
        )
        self.assertNotIn(
            4,
            {snapshot.operation_order for snapshot in history.snapshots},
        )
        restored = self.service.restore(
            self.state.attempt_id,
            history.snapshots[-1].snapshot_id,
            noop.etag,
        )
        self.assertEqual(restored, baseline)

    def test_history_is_bounded_and_pruning_failure_keeps_new_source(self) -> None:
        current = self.service.read(self.state.attempt_id)
        for index in range(HISTORY_LIMIT + 5):
            current = self.service.save(
                self.state.attempt_id, f"revision-{index}\n", current.etag
            )
        history = self.service.list_history(self.state.attempt_id)
        self.assertLessEqual(len(history.snapshots), HISTORY_LIMIT)

        failing_manager = WorkspaceManager(
            self.workspace_root,
            self.cache,
            filesystem=CandidateFailureFilesystem("prune_flush"),
        )
        failing_service = CandidateDocumentService(failing_manager, self.clock)
        latest = failing_service.read(self.state.attempt_id)
        saved = failing_service.save(
            self.state.attempt_id, "after-prune-fault\n", latest.etag
        )
        self.assertEqual(failing_service.read(self.state.attempt_id), saved)

    def test_unpublished_orphan_is_omitted_then_pruned_after_retry(self) -> None:
        current = self.service.read(self.state.attempt_id)
        failing_manager = WorkspaceManager(
            self.workspace_root,
            self.cache,
            filesystem=CandidateFailureFilesystem("source_replace_cleanup"),
        )
        failing = CandidateDocumentService(failing_manager, self.clock)

        with self.assertRaises(CandidateDocumentUnavailableError):
            failing.save(self.state.attempt_id, "retried\n", current.etag)

        self.assertEqual(self.service.read(self.state.attempt_id), current)
        self.assertEqual(
            self.service.list_history(self.state.attempt_id).snapshots,
            (),
        )
        orphan_paths = tuple((self.attempt / HISTORY_DIRECTORY).glob("*.json"))
        self.assertEqual(len(orphan_paths), 1)

        saved = self.service.save(
            self.state.attempt_id, "retried\n", current.etag
        )
        history = self.service.list_history(self.state.attempt_id)

        self.assertEqual(history.current, saved)
        self.assertEqual(
            [snapshot.content for snapshot in history.snapshots],
            [current.content],
        )
        self.assertEqual(
            [snapshot.operation_order for snapshot in history.snapshots],
            [2],
        )
        self.assertEqual(
            tuple((self.attempt / HISTORY_DIRECTORY).glob("*.json")),
            (
                self.attempt
                / HISTORY_DIRECTORY
                / f"{history.snapshots[0].snapshot_id}.json",
            ),
        )

    def test_failure_before_snapshot_and_after_snapshot_preserves_safe_recovery(self) -> None:
        current = self.service.read(self.state.attempt_id)
        failing_manager = WorkspaceManager(
            self.workspace_root,
            self.cache,
            filesystem=CandidateFailureFilesystem("snapshot_flush"),
        )
        with self.assertRaises(CandidateDocumentUnavailableError):
            CandidateDocumentService(failing_manager, self.clock).save(
                self.state.attempt_id, "not published\n", current.etag
            )
        self.assertEqual(self.service.read(self.state.attempt_id), current)

        failing_manager = WorkspaceManager(
            self.workspace_root,
            self.cache,
            filesystem=CandidateFailureFilesystem("source_replace"),
        )
        failing = CandidateDocumentService(failing_manager, self.clock)
        with self.assertRaises(CandidateDocumentUnavailableError):
            failing.save(self.state.attempt_id, "published-with-report\n", current.etag)
        self.assertEqual(
            self.service.read(self.state.attempt_id).content,
            "published-with-report\n",
        )
        self.assertEqual(
            self.service.list_history(self.state.attempt_id).snapshots[0].operation_order,
            2,
        )
        self.assertTrue(tuple((self.attempt / HISTORY_DIRECTORY).glob("*.json")))

    def test_frozen_clock_retains_50_changes_across_pruned_noop_order_gaps(self) -> None:
        current = self.service.read(self.state.attempt_id)
        for index in range(HISTORY_LIMIT + 5):
            current = self.service.save(
                self.state.attempt_id, f"revision-{index}\n", current.etag
            )
            current = self.service.save(
                self.state.attempt_id, current.content, current.etag
            )
        history = self.service.list_history(self.state.attempt_id)
        self.assertEqual(
            [snapshot.operation_order for snapshot in history.snapshots],
            list(range((HISTORY_LIMIT + 5) * 2 - 1, 9, -2)),
        )
        self.assertEqual(
            [snapshot.content for snapshot in history.snapshots],
            [f"revision-{index}\n" for index in range(HISTORY_LIMIT + 3, 3, -1)],
        )
        sequence = json.loads(
            (self.attempt / HISTORY_ORDER_FILENAME).read_text(encoding="utf-8")
        )
        self.assertEqual(sequence["next_order"], (HISTORY_LIMIT + 5) * 2 + 1)
