"""Read-only attempt review: honest axes, verified bytes, and no side effects."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from tests.workspace_test_support import (
    WorkspaceManager,
    make_cache,
    session,
    tree_snapshot,
)

from codesignal_practice_simulator.attempt_reviews import (
    CAPTURED,
    CONTENT_IDENTITY_UNAVAILABLE_ISSUE,
    LEGACY_BINDING_UNAVAILABLE,
    LEGACY_SOURCE_UNAVAILABLE,
    NOT_APPLICABLE,
    NOT_CAPTURED,
    SOURCE_UNREADABLE_AT_SUBMISSION,
    AttemptReviewService,
)
from codesignal_practice_simulator.errors import (
    InvalidInputError,
    ReviewPendingError,
    SessionCorruptError,
    SessionUnavailableError,
)
from codesignal_practice_simulator.lifecycle import LifecycleService
from codesignal_practice_simulator.models import (
    CONTENT_IDENTITY_PINNED,
    CONTENT_IDENTITY_UNAVAILABLE,
    SUBMITTED,
    AssessmentMetadata,
    LevelResult,
    ScoreSummary,
)
from codesignal_practice_simulator.persistence import (
    REVIEW_FILENAME,
    SUBMISSION_RECOVERY_FILENAME,
)


START = datetime(2026, 9, 8, 19, tzinfo=timezone.utc)
FILE_STORAGE_METADATA = AssessmentMetadata("file_storage", "File Storage")
SUBMITTED_SOURCE = "def simulate():\n    return 'submitted'\n"


class FakeClock:
    def __init__(self, value: datetime = START) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


class ForbiddenScorer:
    def __init__(self) -> None:
        self.calls: list[Path] = []
        self.allowed = True

    def __call__(self, attempt: Path) -> ScoreSummary:
        if not self.allowed:
            raise AssertionError("scorer ran during review")
        self.calls.append(attempt)
        return ScoreSummary(
            tuple(
                LevelResult(level, "passed" if level < 3 else "failed")
                for level in range(1, 5)
            )
        )


class AttemptReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workspace_root = self.root / "workspace"
        self.workspace_root.mkdir()
        self.clock = FakeClock()
        self.scorer = ForbiddenScorer()
        self.manager = WorkspaceManager(self.workspace_root, make_cache(self.root))
        self.service = LifecycleService(self.manager, self.clock, self.scorer)
        self.attempts = self.workspace_root / "attempts"
        self.reviews = AttemptReviewService(self.attempts)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def start(self, source: str | None = SUBMITTED_SOURCE):
        state = self.service.start(FILE_STORAGE_METADATA)
        attempt = self.attempts / state.attempt_id
        if source is not None:
            (attempt / "simulation.py").write_text(source, encoding="utf-8")
        return state, attempt

    def submit(self, source: str | None = SUBMITTED_SOURCE):
        state, attempt = self.start(source)
        result = self.service.submit(state.attempt_id)
        self.scorer.allowed = False
        return result.state, attempt

    def read_without_side_effects(self, attempt_id: str, attempt: Path):
        """Return the review and prove the whole attempt is byte-identical."""
        before = tree_snapshot(attempt)
        pointer = (self.attempts / "active.json").read_bytes()
        review = self.reviews.get_review(attempt_id)
        self.assertEqual(tree_snapshot(attempt), before)
        self.assertEqual((self.attempts / "active.json").read_bytes(), pointer)
        return review

    def test_pinned_submission_returns_verified_immutable_source(self) -> None:
        state, attempt = self.submit()

        review = self.read_without_side_effects(state.attempt_id, attempt)

        self.assertEqual(review.status, SUBMITTED)
        self.assertEqual(review.source_binding, CAPTURED)
        self.assertEqual(review.source.binding, CAPTURED)
        self.assertEqual(review.source.content, SUBMITTED_SOURCE)
        self.assertEqual(review.assessment.content_identity, CONTENT_IDENTITY_PINNED)
        self.assertEqual(review.assessment.content_version, state.assessment.content_version)
        self.assertEqual(review.assessment.content_digest, state.assessment.content_digest)
        self.assertEqual(review.score, state.score)
        self.assertEqual(review.submitted_at, state.submitted_at)
        self.assertEqual(review.issues, ())
        self.assertEqual(self.scorer.calls, [attempt.resolve()])

    def test_review_shows_stored_results_when_content_version_is_uninstalled(self) -> None:
        state, attempt = self.submit()
        # The review boundary never consults the registry, so an emptied one changes nothing.
        self.manager.registry = None

        review = self.read_without_side_effects(state.attempt_id, attempt)

        self.assertEqual(review.source_binding, CAPTURED)
        self.assertEqual(review.score, state.score)

    def test_unsubmitted_attempt_reports_binding_as_not_applicable(self) -> None:
        state, attempt = self.start()

        review = self.read_without_side_effects(state.attempt_id, attempt)

        self.assertEqual(review.status, "active")
        self.assertEqual(review.source_binding, NOT_APPLICABLE)
        self.assertIsNone(review.source)
        self.assertIsNone(review.score)

    def test_unreadable_source_at_submission_is_reported_as_not_captured(self) -> None:
        state, attempt = self.start()
        (attempt / "simulation.py").unlink()
        self.service.submit(state.attempt_id)
        self.scorer.allowed = False

        review = self.read_without_side_effects(state.attempt_id, attempt)

        self.assertEqual(review.source_binding, NOT_CAPTURED)
        self.assertIsNone(review.source)
        self.assertIn(SOURCE_UNREADABLE_AT_SUBMISSION, review.issues)

    def test_legacy_submission_labels_unbound_source_and_missing_identity(self) -> None:
        legacy = session(str(uuid4()))
        attempt = self.manager.create_attempt(legacy)
        (attempt / "simulation.py").write_text(SUBMITTED_SOURCE, encoding="utf-8")
        self.service.submit(legacy.attempt_id)
        # Drop the review member to model a submission by an older release.
        (attempt / REVIEW_FILENAME).unlink()
        self.scorer.allowed = False

        review = self.read_without_side_effects(legacy.attempt_id, attempt)

        self.assertEqual(review.source_binding, NOT_CAPTURED)
        self.assertEqual(review.assessment.content_identity, CONTENT_IDENTITY_UNAVAILABLE)
        self.assertIsNone(review.assessment.content_version)
        self.assertIn(LEGACY_BINDING_UNAVAILABLE, review.issues)
        self.assertIn(CONTENT_IDENTITY_UNAVAILABLE_ISSUE, review.issues)
        # The current file is offered only as explicitly unbound legacy source.
        self.assertEqual(review.source.binding, "legacy_unbound")
        self.assertEqual(review.source.content, SUBMITTED_SOURCE)
        self.assertNotEqual(review.source_binding, CAPTURED)

        (attempt / "simulation.py").unlink()
        without_source = self.reviews.get_review(legacy.attempt_id)
        self.assertIsNone(without_source.source)
        self.assertIn(LEGACY_SOURCE_UNAVAILABLE, without_source.issues)
        self.assertEqual(without_source.score, review.score)

    def test_source_can_be_left_out_of_a_metadata_only_read(self) -> None:
        state, attempt = self.submit()

        review = self.reviews.get_review(state.attempt_id, include_source=False)

        self.assertEqual(review.source_binding, CAPTURED)
        self.assertIsNone(review.source)
        self.assertEqual(review.score, state.score)

    def test_tampered_or_mismatched_review_fails_closed(self) -> None:
        state, attempt = self.submit()
        published = (attempt / REVIEW_FILENAME).read_bytes()

        record = json.loads(published.decode("utf-8"))
        record["score"]["levels"][0]["outcome"] = "failed"
        (attempt / REVIEW_FILENAME).write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaises(SessionCorruptError):
            self.reviews.get_review(state.attempt_id)

        record = json.loads(published.decode("utf-8"))
        record["source"]["content"] = "def simulate():\n    return 'tampered'\n"
        (attempt / REVIEW_FILENAME).write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaises(SessionCorruptError):
            self.reviews.get_review(state.attempt_id)

        # The digest binds the record's content, not the file's formatting, so a
        # reformatted member with identical fields is still the same review.
        record = json.loads(published.decode("utf-8"))
        (attempt / REVIEW_FILENAME).write_text(
            json.dumps(record, indent=2), encoding="utf-8"
        )
        reformatted = self.reviews.get_review(state.attempt_id)
        self.assertEqual(reformatted.source.content, SUBMITTED_SOURCE)
        self.assertEqual(reformatted.score, state.score)

        # A record for a different revision is not this submission.
        record = json.loads(published.decode("utf-8"))
        record["state_revision"] = record["state_revision"] + 1
        (attempt / REVIEW_FILENAME).write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaisesRegex(SessionCorruptError, "does not match"):
            self.reviews.get_review(state.attempt_id)

    def test_verified_review_outranks_an_edited_session_record(self) -> None:
        """A mutable session must not be able to restate a protected review."""
        state, attempt = self.submit()
        record = json.loads((attempt / "session.json").read_text("utf-8"))
        record["assessment"]["content_version"] = "upstream-9999999"
        record["assessment"]["content_digest"] = "c" * 64
        (attempt / "session.json").write_text(json.dumps(record), encoding="utf-8")

        with self.assertRaisesRegex(SessionCorruptError, "does not match"):
            self.reviews.get_review(state.attempt_id)

    def test_review_reports_the_recorded_profile_and_timing(self) -> None:
        state, attempt = self.submit()

        review = self.reviews.get_review(state.attempt_id)
        recorded = json.loads((attempt / REVIEW_FILENAME).read_text("utf-8"))

        self.assertEqual(review.profile.to_dict(), recorded["profile"])
        self.assertEqual(review.started_at.isoformat(), recorded["started_at"])
        self.assertEqual(review.deadline_at.isoformat(), recorded["deadline_at"])
        self.assertEqual(review.submitted_at.isoformat(), recorded["submitted_at"])
        self.assertEqual(
            review.assessment.content_digest, recorded["assessment"]["content_digest"]
        )

    def test_pending_finalization_is_retryable_not_repaired(self) -> None:
        state, attempt = self.start()
        marker = attempt / SUBMISSION_RECOVERY_FILENAME
        marker.write_text("{}", encoding="utf-8")
        before = tree_snapshot(attempt)

        with self.assertRaisesRegex(ReviewPendingError, "retry"):
            self.reviews.get_review(state.attempt_id)

        self.assertEqual(tree_snapshot(attempt), before)

    def test_unsafe_identifiers_and_paths_are_rejected_safely(self) -> None:
        state, attempt = self.submit()
        for identifier in ("../etc/passwd", "not-a-uuid", "", state.attempt_id.upper()):
            with self.subTest(identifier=identifier):
                with self.assertRaises(InvalidInputError):
                    self.reviews.get_review(identifier)

        missing = str(uuid4())
        with self.assertRaises(SessionUnavailableError) as unavailable:
            self.reviews.get_review(missing)
        self.assertNotIn(str(self.workspace_root), str(unavailable.exception))

        linked = self.attempts / str(uuid4())
        linked.symlink_to(attempt)
        with self.assertRaises(SessionUnavailableError):
            self.reviews.get_review(linked.name)

    def test_record_identity_must_match_its_directory(self) -> None:
        state, attempt = self.submit()
        other = self.attempts / str(uuid4())
        other.mkdir()
        (other / "session.json").write_bytes((attempt / "session.json").read_bytes())

        with self.assertRaisesRegex(SessionCorruptError, "identity"):
            self.reviews.get_review(other.name)

    def test_oversized_review_member_is_rejected(self) -> None:
        state, attempt = self.submit()
        (attempt / REVIEW_FILENAME).write_bytes(b"{" + b" " * (2 * 1024 * 1024) + b"}")

        with self.assertRaisesRegex(SessionCorruptError, "size limit"):
            self.reviews.get_review(state.attempt_id)

    def test_review_leaves_a_concurrent_active_attempt_untouched(self) -> None:
        submitted, submitted_attempt = self.submit()
        self.scorer.allowed = True
        live = self.service.start(FILE_STORAGE_METADATA)
        live_attempt = self.attempts / live.attempt_id
        before = tree_snapshot(live_attempt)
        pointer = (self.attempts / "active.json").read_bytes()

        review = self.reviews.get_review(submitted.attempt_id)

        self.assertEqual(review.attempt_id, submitted.attempt_id)
        self.assertEqual(tree_snapshot(live_attempt), before)
        self.assertEqual((self.attempts / "active.json").read_bytes(), pointer)
        self.assertEqual(
            self.service.status(live.attempt_id).deadline_at, live.deadline_at
        )

    def test_review_never_creates_a_source_baseline(self) -> None:
        legacy = session(str(uuid4()))
        attempt = self.manager.create_attempt(legacy)
        (attempt / "simulation.py").write_text(SUBMITTED_SOURCE, encoding="utf-8")
        self.service.submit(legacy.attempt_id)
        (attempt / REVIEW_FILENAME).unlink()
        (attempt / ".candidate-initial.json").unlink()
        (attempt / ".candidate-history-order.json").unlink()
        self.scorer.allowed = False
        before = tree_snapshot(attempt)

        review = self.reviews.get_review(legacy.attempt_id)

        self.assertEqual(review.source.binding, "legacy_unbound")
        self.assertEqual(tree_snapshot(attempt), before)
        self.assertFalse((attempt / ".candidate-initial.json").exists())


if __name__ == "__main__":
    unittest.main()
