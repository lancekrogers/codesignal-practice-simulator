"""Candidate-document validation and serialization tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from codesignal_practice_simulator.candidate_documents import (
    CandidateDocument,
    CandidateDocumentError,
    CandidateDocumentTooLargeError,
    InvalidCandidateEncodingError,
    SourceHistory,
    SourceSnapshot,
    etag_for,
)

try:
    from .candidate_document_test_support import CandidateDocumentTestCase
except ImportError:
    from candidate_document_test_support import CandidateDocumentTestCase


class CandidateDocumentModelTests(CandidateDocumentTestCase):
    def test_limits_encoding_and_symlink_are_rejected_without_source_mutation(self) -> None:
        current = self.service.read(self.state.attempt_id)
        before = (self.attempt / "simulation.py").read_bytes()
        with self.assertRaises(CandidateDocumentTooLargeError):
            self.service.save(
                self.state.attempt_id,
                "x" * (256 * 1024 + 1),
                current.etag,
            )
        with self.assertRaises(InvalidCandidateEncodingError):
            self.service.save(self.state.attempt_id, "\ud800", current.etag)
        self.assertEqual((self.attempt / "simulation.py").read_bytes(), before)

    def test_exact_256_kibibytes_is_allowed(self) -> None:
        current = self.service.read(self.state.attempt_id)
        content = "x" * (256 * 1024)
        saved = self.service.save(self.state.attempt_id, content, current.etag)
        self.assertEqual(len(saved.content.encode("utf-8")), 256 * 1024)
        self.assertEqual(self.service.read(self.state.attempt_id), saved)

    def test_invalid_etag_and_snapshot_uuid_are_normalized(self) -> None:
        current = self.service.read(self.state.attempt_id)
        with self.assertRaises(CandidateDocumentError):
            self.service.save(self.state.attempt_id, "source\n", "invalid")
        with self.assertRaises(CandidateDocumentError):
            self.service.preview_history(self.state.attempt_id, "invalid")

    def test_model_roundtrips_are_json_safe_and_reject_bytes(self) -> None:
        current = self.service.read(self.state.attempt_id)
        self.assertEqual(CandidateDocument.from_dict(current.to_dict()), current)
        json.dumps(current.to_dict())
        with self.assertRaises(CandidateDocumentError):
            CandidateDocument(
                current.attempt_id,
                current.filename,
                b"bytes",  # type: ignore[arg-type]
                etag_for(""),
                etag_for(""),
            )
        snapshot = SourceSnapshot(
            str(uuid4()),
            current.attempt_id,
            current.filename,
            self.clock.now(),
            "save",
            current.etag,
            etag_for("next\n"),
            current.content,
        )
        self.assertEqual(SourceSnapshot.from_dict(snapshot.to_dict()), snapshot)
        history = SourceHistory(current, (snapshot,))
        self.assertEqual(SourceHistory.from_dict(history.to_dict()), history)
