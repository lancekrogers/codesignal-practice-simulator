"""Candidate-document content isolation and filesystem safety tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from codesignal_practice_simulator.candidate_documents import (
    CandidateDocumentConflictError,
    CandidateDocumentCorruptError,
    CandidateDocumentUnavailableError,
    HISTORY_DIRECTORY,
    HISTORY_ORDER_FILENAME,
    INITIAL_SOURCE_FILENAME,
    UnsafeCandidateDocumentError,
    etag_for,
)
from codesignal_practice_simulator.errors import ExitCode

try:
    from .candidate_document_test_support import (
        FORBIDDEN_FIXTURE_BYTES,
        CandidateDocumentTestCase,
        make_session,
    )
except ImportError:
    from candidate_document_test_support import (
        FORBIDDEN_FIXTURE_BYTES,
        CandidateDocumentTestCase,
        make_session,
    )


class CandidateDocumentSafetyTests(CandidateDocumentTestCase):
    def test_missing_candidate_has_unavailable_classification(self) -> None:
        (self.attempt / "simulation.py").unlink()
        with self.assertRaises(CandidateDocumentUnavailableError) as failure:
            self.service.read(self.state.attempt_id)
        self.assertEqual(failure.exception.exit_code, ExitCode.SESSION_UNAVAILABLE)
        for value in FORBIDDEN_FIXTURE_BYTES:
            self.assertNotIn(value, str(failure.exception).encode())

    def test_history_results_and_errors_exclude_exact_fixture_bytes(self) -> None:
        current = self.service.read(self.state.attempt_id)
        saved = self.service.save(self.state.attempt_id, "candidate-only\n", current.etag)
        history = self.service.list_history(self.state.attempt_id)
        preview = self.service.preview_history(
            self.state.attempt_id, history.snapshots[0].snapshot_id
        )
        results = (
            json.dumps(history.to_dict()).encode(),
            json.dumps(preview.to_dict()).encode(),
            json.dumps(saved.to_dict()).encode(),
        )
        errors: list[bytes] = []
        with self.assertRaises(CandidateDocumentConflictError) as conflict:
            self.service.save(self.state.attempt_id, "rejected\n", etag_for("wrong\n"))
        errors.append(str(conflict.exception).encode())
        (self.attempt / "simulation.py").unlink()
        with self.assertRaises(CandidateDocumentUnavailableError) as unavailable:
            self.service.read(self.state.attempt_id)
        errors.append(str(unavailable.exception).encode())

        for result_or_error in (*results, *errors):
            for forbidden in FORBIDDEN_FIXTURE_BYTES:
                self.assertNotIn(forbidden, result_or_error)

    def test_registered_candidate_symlink_is_rejected(self) -> None:
        outside = self.temporary.name + "/outside.py"
        with open(outside, "w", encoding="utf-8") as stream:
            stream.write("outside\n")
        source = self.attempt / "simulation.py"
        source.unlink()
        source.symlink_to(outside)
        with self.assertRaises(UnsafeCandidateDocumentError):
            self.service.read(self.state.attempt_id)
        with open(outside, encoding="utf-8") as stream:
            self.assertEqual(stream.read(), "outside\n")

    def test_orphan_history_records_are_not_published(self) -> None:
        current = self.service.read(self.state.attempt_id)
        saved = self.service.save(self.state.attempt_id, "next\n", current.etag)
        history_path = next((self.attempt / HISTORY_DIRECTORY).glob("*.json"))
        orphan = json.loads(history_path.read_text(encoding="utf-8"))
        orphan_id = str(uuid4())
        orphan.update(
            {
                "snapshot_id": orphan_id,
                "new_hash": etag_for("orphan\n"),
                "operation_order": 2,
            }
        )
        history_path.with_name(f"{orphan_id}.json").write_text(
            json.dumps(orphan), encoding="utf-8"
        )
        order_path = self.attempt / HISTORY_ORDER_FILENAME
        order = json.loads(order_path.read_text(encoding="utf-8"))
        order["next_order"] = 3
        order_path.write_text(json.dumps(order), encoding="utf-8")
        self.assertEqual(len(self.service.list_history(self.state.attempt_id).snapshots), 1)
        self.service.save(self.state.attempt_id, "latest\n", saved.etag)
        self.assertEqual(len(tuple(history_path.parent.glob("*.json"))), 2)

    def test_duplicate_persisted_operation_orders_are_corrupt(self) -> None:
        current = self.service.read(self.state.attempt_id)
        self.service.save(self.state.attempt_id, "next\n", current.etag)
        history_path = next((self.attempt / HISTORY_DIRECTORY).glob("*.json"))
        duplicate = json.loads(history_path.read_text(encoding="utf-8"))
        duplicate_id = str(uuid4())
        duplicate["snapshot_id"] = duplicate_id
        history_path.with_name(f"{duplicate_id}.json").write_text(
            json.dumps(duplicate), encoding="utf-8"
        )
        with self.assertRaises(CandidateDocumentCorruptError):
            self.service.list_history(self.state.attempt_id)

    def test_baseline_history_and_record_symlinks_and_ownership_are_rejected(self) -> None:
        outside = self.temporary.name + "/outside"
        with open(outside, "w", encoding="utf-8") as stream:
            stream.write("outside\n")
        baseline = self.attempt / INITIAL_SOURCE_FILENAME
        baseline.unlink()
        baseline.symlink_to(outside)
        with self.assertRaises(UnsafeCandidateDocumentError):
            self.service.read(self.state.attempt_id)
        baseline.unlink()
        self.service.read(self.state.attempt_id)

        current = self.service.read(self.state.attempt_id)
        self.service.save(self.state.attempt_id, "history\n", current.etag)
        history = self.attempt / HISTORY_DIRECTORY
        snapshot = next(history.glob("*.json"))
        snapshot_data = snapshot.read_text(encoding="utf-8")
        snapshot.unlink()
        snapshot.symlink_to(outside)
        with self.assertRaises(UnsafeCandidateDocumentError):
            self.service.list_history(self.state.attempt_id)
        snapshot.unlink()
        snapshot.write_text(snapshot_data, encoding="utf-8")
        owned = json.loads(snapshot_data)
        snapshot.write_text(
            json.dumps({**owned, "attempt_id": str(uuid4())}), encoding="utf-8"
        )
        with self.assertRaises(CandidateDocumentCorruptError):
            self.service.list_history(self.state.attempt_id)
        snapshot.write_text(snapshot_data, encoding="utf-8")
        real_history = history.with_name("history-real")
        history.rename(real_history)
        history.symlink_to(real_history, target_is_directory=True)
        with self.assertRaises(UnsafeCandidateDocumentError):
            self.service.list_history(self.state.attempt_id)

    def test_corrupt_metadata_and_neighboring_attempts_do_not_cross_boundaries(self) -> None:
        baseline = self.attempt / INITIAL_SOURCE_FILENAME
        baseline.write_text("{broken", encoding="utf-8")
        with self.assertRaises(CandidateDocumentCorruptError) as baseline_error:
            self.service.read(self.state.attempt_id)
        self.assertNotIn(str(self.attempt), str(baseline_error.exception))

        baseline.unlink()
        self.service.read(self.state.attempt_id)
        first_events = (self.attempt / "events.jsonl").read_bytes()
        second_state = make_session(str(uuid4()))
        second_attempt = self.manager.create_attempt(second_state)
        second_service = self.service.__class__(self.manager, self.clock)
        second_current = second_service.read(second_state.attempt_id)
        second_service.save(second_state.attempt_id, "second only\n", second_current.etag)
        self.assertEqual(
            self.service.read(self.state.attempt_id).content,
            "cached simulation.py fixture\n",
        )
        self.assertEqual((self.attempt / "events.jsonl").read_bytes(), first_events)
        self.assertNotEqual(
            (second_attempt / "simulation.py").read_bytes(),
            (self.attempt / "simulation.py").read_bytes(),
        )

        history_file = next((second_attempt / HISTORY_DIRECTORY).glob("*.json"))
        history_file.write_text("{broken", encoding="utf-8")
        with self.assertRaises(CandidateDocumentCorruptError):
            second_service.list_history(second_state.attempt_id)
