"""Immutable submission capture: bound source, WAL replay, and payload rules."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from tests.workspace_test_support import (
    ValidatedFixtureCache,
    WorkspaceManager,
    make_cache,
    session,
    tree_snapshot,
)

from codesignal_practice_simulator.application import RuntimeApplication
from codesignal_practice_simulator.candidate_document_models import (
    CandidateDocumentReadOnlyError,
    etag_for,
)
from codesignal_practice_simulator.errors import (
    ScoredSourceChangedError,
    SessionCorruptError,
)
from codesignal_practice_simulator.filesystem import LocalFilesystem
from codesignal_practice_simulator.lifecycle import LifecycleService
from codesignal_practice_simulator.models import (
    CONTENT_IDENTITY_PINNED,
    CONTENT_IDENTITY_UNAVAILABLE,
    EXPIRED,
    SUBMITTED,
    AssessmentMetadata,
    LevelResult,
    PinnedAssessment,
    ReviewRecord,
    ScoreSummary,
    SessionStateV2,
    canonical_review_bytes,
    review_digest,
)
from codesignal_practice_simulator.persistence import (
    REVIEW_FILENAME,
    SUBMISSION_RECOVERY_FILENAME,
    Persistence,
)


START = datetime(2026, 9, 8, 19, tzinfo=timezone.utc)
FILE_STORAGE_METADATA = AssessmentMetadata("file_storage", "File Storage")
EDITED_SOURCE = "def simulate():\n    return 'edited'\n"


class FakeClock:
    def __init__(self, value: datetime = START) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


class SpyScorer:
    """Score a fixed result, optionally editing the source mid-run."""

    def __init__(self, edit_to: str | None = None) -> None:
        self.calls: list[Path] = []
        self.edit_to = edit_to
        self.forbidden = False

    def __call__(self, attempt: Path) -> ScoreSummary:
        if self.forbidden:
            raise AssertionError("scorer ran during recovery")
        self.calls.append(attempt)
        if self.edit_to is not None:
            (attempt / "simulation.py").write_text(self.edit_to, encoding="utf-8")
        return ScoreSummary(
            tuple(
                LevelResult(level, "passed" if level < 4 else "failed")
                for level in range(1, 5)
            )
        )


class FailOnceFilesystem(LocalFilesystem):
    """Fail one durable operation on one filename, optionally after it succeeds."""

    def __init__(self, operation: str, filename: str, *, after: bool = False) -> None:
        self.operation = operation
        self.filename = filename
        self.after = after
        self.failed = False

    def _should_fail(self, operation: str, path: Path) -> bool:
        return (
            not self.failed and operation == self.operation and path.name == self.filename
        )

    def replace(self, source: Path, destination: Path) -> None:
        if self._should_fail("replace", destination):
            self.failed = True
            if self.after:
                super().replace(source, destination)
            raise OSError(f"injected replace failure for {self.filename}")
        super().replace(source, destination)

    def append_bytes(self, path: Path, data: bytes) -> None:
        if self._should_fail("append", path):
            self.failed = True
            raise OSError(f"injected append failure for {self.filename}")
        super().append_bytes(path, data)

    def unlink(self, path: Path) -> None:
        if self._should_fail("unlink", path):
            self.failed = True
            raise OSError(f"injected unlink failure for {self.filename}")
        super().unlink(path)


class EventUnavailableFilesystem(LocalFilesystem):
    """Make every events.jsonl append and replacement fail."""

    def append_bytes(self, path: Path, data: bytes) -> None:
        if path.name == "events.jsonl":
            raise OSError("injected event append failure")
        super().append_bytes(path, data)

    def replace(self, source: Path, destination: Path) -> None:
        if destination.name == "events.jsonl":
            raise OSError("injected event replacement failure")
        super().replace(source, destination)


class CaptureTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workspace_root = self.root / "workspace"
        self.workspace_root.mkdir()
        self.cache = make_cache(self.root)
        self.clock = FakeClock()
        self.scorer = SpyScorer()
        self.manager = WorkspaceManager(self.workspace_root, self.cache)
        self.service = LifecycleService(self.manager, self.clock, self.scorer)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def use_filesystem(self, filesystem: LocalFilesystem) -> None:
        persistence = Persistence(filesystem)
        self.manager.filesystem = filesystem
        self.manager.persistence = persistence
        self.service.persistence = persistence

    def attempt_path(self, attempt_id: str) -> Path:
        return self.workspace_root / "attempts" / attempt_id

    def start(self):
        state = self.service.start(FILE_STORAGE_METADATA)
        return state, self.attempt_path(state.attempt_id)

    def write_source(self, attempt: Path, content: str) -> None:
        (attempt / "simulation.py").write_text(content, encoding="utf-8")

    def review_of(self, attempt: Path) -> ReviewRecord:
        review = Persistence().read_review(attempt)
        assert review is not None
        return review


class PinnedCaptureTests(CaptureTestCase):
    def test_submission_binds_the_exact_scored_bytes(self) -> None:
        state, attempt = self.start()
        self.write_source(attempt, EDITED_SOURCE)

        result = self.service.submit(state.attempt_id)

        review = self.review_of(attempt)
        self.assertEqual(review.source.content, EDITED_SOURCE)
        self.assertEqual(
            review.source.sha256,
            hashlib.sha256(EDITED_SOURCE.encode("utf-8")).hexdigest(),
        )
        self.assertEqual(review.content_identity, CONTENT_IDENTITY_PINNED)
        self.assertIsInstance(review.assessment, PinnedAssessment)
        self.assertEqual(review.assessment, state.assessment)
        self.assertEqual(review.score, result.score)
        self.assertEqual(review.state_revision, result.state.revision)
        self.assertEqual(result.state.review_digest, review_digest(review))
        self.assertEqual(
            (attempt / REVIEW_FILENAME).read_bytes(), canonical_review_bytes(review)
        )
        self.assertEqual(len(self.scorer.calls), 1)

    def test_source_changed_during_scoring_commits_nothing(self) -> None:
        state, attempt = self.start()
        self.write_source(attempt, EDITED_SOURCE)
        racing = SpyScorer(edit_to="def simulate():\n    return 'raced'\n")
        self.service.scorer = racing
        before = tree_snapshot(attempt)

        with self.assertRaisesRegex(ScoredSourceChangedError, "changed while scoring"):
            self.service.submit(state.attempt_id)

        # The racing write is the only difference; no state, event, review or WAL.
        after = tree_snapshot(attempt)
        self.assertEqual(
            {path for path, value in after.items() if before.get(path) != value},
            {"simulation.py"},
        )
        self.assertFalse((attempt / REVIEW_FILENAME).exists())
        self.assertFalse((attempt / SUBMISSION_RECOVERY_FILENAME).exists())
        self.assertEqual(self.service.status(state.attempt_id).status, "active")

    def test_unreadable_source_still_finalizes_and_records_absence(self) -> None:
        state, attempt = self.start()
        (attempt / "simulation.py").unlink()

        result = self.service.submit(state.attempt_id)

        review = self.review_of(attempt)
        self.assertEqual(result.state.status, SUBMITTED)
        self.assertIsNone(review.source)
        self.assertFalse(review.source_captured)
        self.assertEqual(result.state.review_digest, review_digest(review))

    def test_repeat_submit_returns_the_committed_result_without_rescoring(self) -> None:
        state, attempt = self.start()
        self.write_source(attempt, EDITED_SOURCE)
        first = self.service.submit(state.attempt_id)
        published = (attempt / REVIEW_FILENAME).read_bytes()
        # A later out-of-band edit must not change what was submitted.
        self.write_source(attempt, "def simulate():\n    return 'after'\n")

        repeated = self.service.submit(state.attempt_id)

        self.assertEqual(repeated.state, first.state)
        self.assertFalse(repeated.newly_submitted)
        self.assertEqual((attempt / REVIEW_FILENAME).read_bytes(), published)
        self.assertEqual(len(self.scorer.calls), 1)

    def test_legacy_submission_captures_source_without_content_identity(self) -> None:
        legacy = session(str(uuid4()))
        attempt = self.manager.create_attempt(legacy)
        self.write_source(attempt, EDITED_SOURCE)

        result = self.service.submit(legacy.attempt_id)

        review = self.review_of(attempt)
        self.assertEqual(review.content_identity, CONTENT_IDENTITY_UNAVAILABLE)
        self.assertEqual(review.assessment, FILE_STORAGE_METADATA)
        self.assertNotIsInstance(review.assessment, PinnedAssessment)
        self.assertEqual(review.source.content, EDITED_SOURCE)
        self.assertFalse(hasattr(result.state, "review_digest"))
        self.assertEqual(
            json.loads((attempt / "session.json").read_text("utf-8"))["schema_version"],
            "session/v1",
        )


class RecoveryTests(CaptureTestCase):
    def test_recovery_publishes_the_recorded_review_at_every_boundary(self) -> None:
        boundaries = {
            "review write failed": lambda: FailOnceFilesystem("replace", REVIEW_FILENAME),
            "review published then reported failure": lambda: FailOnceFilesystem(
                "replace", REVIEW_FILENAME, after=True
            ),
            "session replacement failed": lambda: FailOnceFilesystem(
                "replace", "session.json"
            ),
            "event unavailable": EventUnavailableFilesystem,
            "recovery cleanup failed": lambda: FailOnceFilesystem(
                "unlink", SUBMISSION_RECOVERY_FILENAME
            ),
        }
        for label, build in boundaries.items():
            with self.subTest(boundary=label):
                self.use_filesystem(LocalFilesystem())
                state, attempt = self.start()
                self.write_source(attempt, EDITED_SOURCE)
                calls_before = len(self.scorer.calls)
                self.use_filesystem(build())

                with self.assertRaises(Exception) as failure:
                    self.service.submit(state.attempt_id)
                self.assertNotIsInstance(failure.exception, AssertionError)

                pending = json.loads(
                    (attempt / SUBMISSION_RECOVERY_FILENAME).read_text("utf-8")
                )
                expected = ReviewRecord.from_dict(pending["review"])
                self.use_filesystem(LocalFilesystem())
                self.scorer.forbidden = True
                recovered = self.service.status(state.attempt_id)
                self.scorer.forbidden = False

                self.assertEqual(recovered.status, SUBMITTED)
                self.assertEqual(self.review_of(attempt), expected)
                self.assertEqual(expected.source.content, EDITED_SOURCE)
                self.assertEqual(recovered.review_digest, review_digest(expected))
                self.assertEqual(
                    (attempt / REVIEW_FILENAME).read_bytes(),
                    canonical_review_bytes(expected),
                )
                self.assertEqual(len(self.scorer.calls), calls_before + 1)
                self.assertFalse((attempt / SUBMISSION_RECOVERY_FILENAME).exists())

    def test_recovery_fails_closed_when_a_published_review_differs(self) -> None:
        state, attempt = self.start()
        self.write_source(attempt, EDITED_SOURCE)
        self.use_filesystem(FailOnceFilesystem("replace", "session.json"))
        with self.assertRaises(OSError):
            self.service.submit(state.attempt_id)
        published = (attempt / REVIEW_FILENAME).read_bytes()
        (attempt / REVIEW_FILENAME).write_bytes(published.replace(b"edited", b"tamper"))
        self.use_filesystem(LocalFilesystem())
        self.scorer.forbidden = True

        with self.assertRaisesRegex(SessionCorruptError, "published review"):
            self.service.status(state.attempt_id)

        self.assertEqual(
            json.loads((attempt / "session.json").read_text("utf-8"))["status"], "active"
        )
        self.assertTrue((attempt / SUBMISSION_RECOVERY_FILENAME).is_file())

    def test_review_reader_rejects_unsafe_and_oversized_members(self) -> None:
        state, attempt = self.start()
        self.service.submit(state.attempt_id)
        persistence = Persistence()
        review = (attempt / REVIEW_FILENAME)

        review.write_bytes(b"{" + b" " * (2 * 1024 * 1024) + b"}")
        with self.assertRaisesRegex(SessionCorruptError, "size limit"):
            persistence.read_review(attempt)

        review.unlink()
        review.symlink_to(attempt / "session.json")
        with self.assertRaisesRegex(SessionCorruptError, "unsafe"):
            persistence.read_review(attempt)

        review.unlink()
        self.assertIsNone(persistence.read_review(attempt))


class PayloadContractTests(unittest.TestCase):
    """The application boundary shared by the CLI and the browser."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workspace_root = self.root / "workspace"
        self.workspace_root.mkdir()
        self.clock = FakeClock()
        self.scorer = SpyScorer()
        self.application = RuntimeApplication(
            self.workspace_root,
            clock=self.clock,
            cache=make_cache(self.root),
            scorer_factory=lambda _definition: self.scorer,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def start(self):
        state = self.application.start(
            assessment="file_storage", mode="full", drill_duration_seconds=None
        )
        return state, self.workspace_root / "attempts" / state.attempt_id

    def saved_source(self, attempt_id: str) -> str:
        return self.application.source(attempt_id=attempt_id).content

    def test_active_payload_is_saved_then_captured(self) -> None:
        state, attempt = self.start()
        current = self.application.source(attempt_id=state.attempt_id)

        result = self.application.submit(
            attempt_id=state.attempt_id,
            source_content=EDITED_SOURCE,
            if_match=current.etag,
        )

        review = Persistence().read_review(attempt)
        self.assertEqual(result.state.status, SUBMITTED)
        self.assertEqual(review.source.content, EDITED_SOURCE)
        self.assertEqual(self.saved_source(state.attempt_id), EDITED_SOURCE)

    def test_expired_payload_that_would_change_source_is_refused(self) -> None:
        state, attempt = self.start()
        current = self.application.source(attempt_id=state.attempt_id)
        self.clock.value = state.deadline_at
        before = tree_snapshot(attempt)

        with self.assertRaisesRegex(CandidateDocumentReadOnlyError, "read-only"):
            self.application.submit(
                attempt_id=state.attempt_id,
                source_content=EDITED_SOURCE,
                if_match=current.etag,
            )

        # Expiry itself is persisted by the status observation; nothing else is.
        self.assertEqual(self.application.status(attempt_id=state.attempt_id).status, EXPIRED)
        self.assertEqual(self.saved_source(state.attempt_id), current.content)
        self.assertFalse((attempt / REVIEW_FILENAME).exists())
        self.assertEqual(self.scorer.calls, [])
        self.assertEqual(
            json.loads((attempt / "session.json").read_text("utf-8"))["status"], EXPIRED
        )
        self.assertNotEqual(before, tree_snapshot(attempt))

    def test_expired_payload_equal_to_saved_source_still_finalizes_once(self) -> None:
        state, attempt = self.start()
        current = self.application.source(attempt_id=state.attempt_id)
        self.clock.value = state.deadline_at

        result = self.application.submit(
            attempt_id=state.attempt_id,
            source_content=current.content,
            if_match=current.etag,
        )

        review = Persistence().read_review(attempt)
        self.assertTrue(result.newly_submitted)
        self.assertEqual(result.state.status, SUBMITTED)
        self.assertEqual(review.source.content, current.content)
        self.assertEqual(len(self.scorer.calls), 1)

    def test_a_concurrent_finalization_returns_the_committed_result(self) -> None:
        """A submit that finalizes underneath must not become a read-only error."""
        state, attempt = self.start()
        current = self.application.source(attempt_id=state.attempt_id)
        self.clock.value = state.deadline_at
        expired = self.application.status(attempt_id=state.attempt_id)
        self.assertEqual(expired.status, EXPIRED)

        committed = self.application.submit(
            attempt_id=state.attempt_id, source_content=None, if_match=None
        )
        # The caller still believes the attempt is expired and retries with the
        # buffer it had; the attempt is already final.
        repeated = self.application.submit(
            attempt_id=state.attempt_id,
            source_content=EDITED_SOURCE,
            if_match=current.etag,
        )

        self.assertEqual(repeated.state, committed.state)
        self.assertFalse(repeated.newly_submitted)
        self.assertEqual(len(self.scorer.calls), 1)

    def test_submitted_repeat_ignores_any_payload_and_never_rescores(self) -> None:
        state, attempt = self.start()
        current = self.application.source(attempt_id=state.attempt_id)
        first = self.application.submit(
            attempt_id=state.attempt_id,
            source_content=EDITED_SOURCE,
            if_match=current.etag,
        )
        published = (attempt / REVIEW_FILENAME).read_bytes()

        repeated = self.application.submit(
            attempt_id=state.attempt_id,
            source_content="def simulate():\n    return 'ignored'\n",
            if_match=f"sha256:{'f' * 64}",
        )

        self.assertEqual(repeated.state, first.state)
        self.assertFalse(repeated.newly_submitted)
        self.assertEqual((attempt / REVIEW_FILENAME).read_bytes(), published)
        self.assertEqual(self.saved_source(state.attempt_id), EDITED_SOURCE)
        self.assertEqual(
            etag_for(self.saved_source(state.attempt_id)),
            f"sha256:{Persistence().read_review(attempt).source.sha256}",
        )
        self.assertEqual(len(self.scorer.calls), 1)


if __name__ == "__main__":
    unittest.main()
