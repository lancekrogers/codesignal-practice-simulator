"""Core candidate-document ownership and concurrency tests."""

from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from codesignal_practice_simulator.candidate_documents import (
    CandidateDocumentConflictError,
    CandidateDocumentService,
    SourceHistory,
)
from codesignal_practice_simulator.errors import LockUnavailableError

try:
    from .candidate_document_test_support import CandidateDocumentTestCase
except ImportError:
    from candidate_document_test_support import CandidateDocumentTestCase


class CandidateDocumentCoreTests(CandidateDocumentTestCase):
    def test_initial_baseline_is_source_only_and_legacy_read_is_idempotent(self) -> None:
        baseline = self.attempt / ".candidate-initial.json"
        self.assertTrue(baseline.is_file())
        self.assertNotIn("vendor", baseline.read_text(encoding="utf-8"))
        baseline.unlink()

        first = self.service.read(self.state.attempt_id)
        self.assertTrue(baseline.is_file())
        self.assertEqual(first.content, "cached simulation.py fixture\n")
        baseline_after = baseline.read_bytes()
        self.assertEqual(self.service.read(self.state.attempt_id), first)
        self.assertEqual(baseline.read_bytes(), baseline_after)

    def test_save_uses_cas_and_exposes_recoverable_predecessor(self) -> None:
        original = self.service.read(self.state.attempt_id)
        saved = self.service.save(self.state.attempt_id, "new source\n", original.etag)
        self.assertEqual(saved.content, "new source\n")
        self.assertNotEqual(saved.etag, original.etag)
        history = self.service.list_history(self.state.attempt_id)
        self.assertIsInstance(history, SourceHistory)
        self.assertEqual(history.current, saved)
        self.assertEqual(history.snapshots[0].content, original.content)
        preview = self.service.preview_history(
            self.state.attempt_id, history.snapshots[0].snapshot_id
        )
        self.assertEqual(preview.content, original.content)
        with self.assertRaises(CandidateDocumentConflictError) as conflict:
            self.service.save(self.state.attempt_id, "lost\n", original.etag)
        self.assertEqual(conflict.exception.current.etag, saved.etag)
        self.assertEqual(self.service.read(self.state.attempt_id), saved)

    def test_separate_services_share_attempt_cas_and_lock(self) -> None:
        other = CandidateDocumentService(self.manager, self.clock)
        original = self.service.read(self.state.attempt_id)
        saved = self.service.save(self.state.attempt_id, "winner\n", original.etag)
        with self.assertRaises(CandidateDocumentConflictError) as conflict:
            other.save(self.state.attempt_id, "stale\n", original.etag)
        self.assertEqual(conflict.exception.current, saved)
        with self.manager.persistence.attempt_lock(self.attempt):
            with self.assertRaises(LockUnavailableError):
                other.read(self.state.attempt_id)

    def test_candidate_save_does_not_touch_session_or_events(self) -> None:
        before = (
            (self.attempt / "session.json").read_bytes(),
            (self.attempt / "events.jsonl").read_bytes(),
        )
        current = self.service.read(self.state.attempt_id)
        self.service.save(self.state.attempt_id, "candidate only\n", current.etag)
        self.assertEqual(
            before,
            (
                (self.attempt / "session.json").read_bytes(),
                (self.attempt / "events.jsonl").read_bytes(),
            ),
        )

    def test_same_etag_race_has_one_winner_and_one_conflict(self) -> None:
        current = self.service.read(self.state.attempt_id)
        barrier = threading.Barrier(2)
        outcomes: list[object] = []
        services = (
            CandidateDocumentService(self.manager, self.clock),
            CandidateDocumentService(self.manager, self.clock),
        )

        def save(service: CandidateDocumentService, value: str) -> None:
            barrier.wait()
            try:
                outcomes.append(service.save(self.state.attempt_id, value, current.etag))
            except Exception as error:  # assertion below distinguishes the only allowed failure
                outcomes.append(error)

        threads = [
            threading.Thread(target=save, args=(services[index], f"source-{index}\n"))
            for index in range(2)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sum(hasattr(item, "etag") for item in outcomes), 1)
        errors = [item for item in outcomes if isinstance(item, Exception)]
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(
            errors[0], (CandidateDocumentConflictError, LockUnavailableError)
        )
        self.assertEqual(self.service.read(self.state.attempt_id).content.count("source-"), 1)
