"""Focused tests for session/v2, event/v2, review models, and version dispatch."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from codesignal_practice_simulator.errors import (
    InvalidInputError,
    SessionCorruptError,
    UnsupportedSchemaVersionError,
)
from codesignal_practice_simulator.models import (
    ABANDONED,
    ACTIVE,
    EVENT_SCHEMA_VERSION,
    EVENT_SCHEMA_VERSION_V2,
    CONTENT_IDENTITY_PINNED,
    CONTENT_IDENTITY_UNAVAILABLE,
    REVIEW_SCHEMA_VERSION,
    SESSION_SCHEMA_VERSION,
    SESSION_SCHEMA_VERSION_V2,
    SUBMITTED,
    AbandonmentMetadata,
    AssessmentMetadata,
    EventRecord,
    EventRecordV2,
    LevelResult,
    ModeProfile,
    PinnedAssessment,
    ReviewRecord,
    ReviewSource,
    ScoreSummary,
    SessionState,
    SessionStateV2,
    adapt_session_record,
    parse_event_record,
    parse_review_record,
    parse_session_record,
    review_digest,
)
from codesignal_practice_simulator.persistence import MAX_SESSION_BYTES, Persistence


ATTEMPT_ID = "123e4567-e89b-12d3-a456-426614174000"
EVENT_ID = "123e4567-e89b-12d3-a456-426614174001"
STARTED_AT = datetime(2026, 9, 8, 19, 0, tzinfo=timezone.utc)
CONTENT_VERSION = "file-storage-2026-09-11"
CONTENT_DIGEST = "a" * 64
SOURCE_CONTENT = "def simulate():\n    return 1\n"


def full_profile() -> ModeProfile:
    return ModeProfile("full", "full-90m", 90 * 60)


def pinned_assessment() -> PinnedAssessment:
    return PinnedAssessment(
        "file_storage",
        "File Storage",
        CONTENT_VERSION,
        CONTENT_DIGEST,
    )


def pinned_review() -> ReviewRecord:
    return ReviewRecord(
        schema_version=REVIEW_SCHEMA_VERSION,
        attempt_id=ATTEMPT_ID,
        state_revision=1,
        assessment=pinned_assessment(),
        content_identity=CONTENT_IDENTITY_PINNED,
        profile=full_profile(),
        started_at=STARTED_AT,
        deadline_at=STARTED_AT + timedelta(seconds=90 * 60),
        submitted_at=STARTED_AT + timedelta(seconds=30),
        score=score(),
        source=ReviewSource.capture("simulation.py", SOURCE_CONTENT),
    )


def score() -> ScoreSummary:
    return ScoreSummary(
        (
            LevelResult(1, "passed"),
            LevelResult(2, "failed"),
            LevelResult(3, "error"),
            LevelResult(4, "passed"),
        )
    )


def v1_session(**changes: object) -> SessionState:
    session = SessionState(
        schema_version=SESSION_SCHEMA_VERSION,
        attempt_id=ATTEMPT_ID,
        assessment=AssessmentMetadata("file_storage", "File Storage"),
        profile=full_profile(),
        started_at=STARTED_AT,
        deadline_at=STARTED_AT + timedelta(seconds=90 * 60),
        status=ACTIVE,
        revision=0,
    )
    if changes:
        payload = copy.deepcopy(session.to_dict())
        payload.update(changes)
        return SessionState.from_dict(payload)
    return session


def v2_session(**changes: object) -> SessionStateV2:
    session = SessionStateV2(
        schema_version=SESSION_SCHEMA_VERSION_V2,
        attempt_id=ATTEMPT_ID,
        assessment=pinned_assessment(),
        profile=full_profile(),
        started_at=STARTED_AT,
        deadline_at=STARTED_AT + timedelta(seconds=90 * 60),
        status=ACTIVE,
        revision=0,
        score=None,
        submitted_at=None,
        abandonment=None,
    )
    if changes:
        payload = copy.deepcopy(session.to_dict())
        payload.update(changes)
        return SessionStateV2.from_dict(payload)
    return session


def abandoned_v2(**changes: object) -> SessionStateV2:
    return v2_session(
        status=ABANDONED,
        abandonment=AbandonmentMetadata(
            ended_at=STARTED_AT + timedelta(minutes=5),
            reason="user_restart",
            practice_score=score(),
        ).to_dict(),
        **changes,
    )


class VersionDispatchTests(unittest.TestCase):
    def test_parse_session_rejects_unknown_version_before_other_fields(self) -> None:
        with self.assertRaisesRegex(
            UnsupportedSchemaVersionError, "unsupported session schema version"
        ):
            parse_session_record(
                {
                    "schema_version": "session/v9",
                    "attempt_id": "not-a-uuid",
                    "status": "paused",
                }
            )

    def test_parse_event_rejects_unknown_version_before_other_fields(self) -> None:
        with self.assertRaisesRegex(
            UnsupportedSchemaVersionError, "unsupported event schema version"
        ):
            parse_event_record({"schema_version": "event/v9", "event_id": "bad"})

    def test_v1_reader_still_rejects_v2_when_called_directly(self) -> None:
        with self.assertRaisesRegex(InvalidInputError, "unsupported session schema"):
            SessionState.from_dict(v2_session().to_dict())

    def test_v1_event_reader_still_rejects_v2_when_called_directly(self) -> None:
        event = EventRecordV2(
            schema_version=EVENT_SCHEMA_VERSION_V2,
            event_id=EVENT_ID,
            attempt_id=ATTEMPT_ID,
            revision=0,
            occurred_at=STARTED_AT,
            name="started",
            outcome="succeeded",
            arguments={},
        )
        with self.assertRaisesRegex(InvalidInputError, "unsupported event schema"):
            EventRecord.from_dict(event.to_dict())


class SessionV2RoundTripTests(unittest.TestCase):
    def test_active_v2_round_trip(self) -> None:
        original = v2_session()
        restored = SessionStateV2.from_dict(original.to_dict())
        self.assertEqual(restored, original)
        self.assertEqual(parse_session_record(original.to_dict()), original)

    def test_submitted_v2_round_trip(self) -> None:
        review = pinned_review()
        original = v2_session(
            status=SUBMITTED,
            revision=1,
            score=score().to_dict(),
            submitted_at=(STARTED_AT + timedelta(seconds=30)).isoformat(),
            review_digest=review_digest(review),
        )
        restored = SessionStateV2.from_dict(original.to_dict())
        self.assertEqual(restored, original)
        self.assertEqual(restored.review_digest, review_digest(review))

        # A submitted v2 state must identify the review it published.
        unbound = original.to_dict()
        unbound["review_digest"] = None
        with self.assertRaisesRegex(InvalidInputError, "review_digest"):
            SessionStateV2.from_dict(unbound)
        active_with_digest = v2_session().to_dict()
        active_with_digest["review_digest"] = review_digest(review)
        with self.assertRaisesRegex(InvalidInputError, "review_digest"):
            SessionStateV2.from_dict(active_with_digest)

    def test_abandoned_v2_round_trip_with_practice_score(self) -> None:
        original = abandoned_v2(revision=2)
        restored = SessionStateV2.from_dict(original.to_dict())
        self.assertEqual(restored, original)
        self.assertIsNotNone(restored.abandonment)
        self.assertEqual(restored.abandonment.practice_score, score())

    def test_v1_adapter_reports_unavailable_content_identity(self) -> None:
        adapted = adapt_session_record(v1_session())
        self.assertFalse(adapted.content_identity_available)
        self.assertIsNone(adapted.content_version)
        self.assertIsNone(adapted.content_digest)
        self.assertIsNone(adapted.abandonment)

    def test_v2_adapter_exposes_pinned_content_identity(self) -> None:
        adapted = adapt_session_record(abandoned_v2())
        self.assertTrue(adapted.content_identity_available)
        self.assertEqual(adapted.content_version, CONTENT_VERSION)
        self.assertEqual(adapted.content_digest, CONTENT_DIGEST)
        self.assertEqual(adapted.practice_score, score())


def v2_session_dict(**changes: object) -> dict[str, object]:
    payload = copy.deepcopy(v2_session().to_dict())
    payload.update(changes)
    return payload


class SessionV2ValidationTests(unittest.TestCase):
    def assert_invalid_v2(self, payload: dict[str, object], message: str) -> None:
        with self.assertRaisesRegex(InvalidInputError, message):
            SessionStateV2.from_dict(payload)

    def test_missing_required_fields_reject(self) -> None:
        payload = v2_session().to_dict()
        del payload["assessment"]
        with self.assertRaisesRegex(InvalidInputError, "invalid field set"):
            SessionStateV2.from_dict(payload)

    def test_invalid_status_uuid_and_digest_reject(self) -> None:
        self.assert_invalid_v2(v2_session_dict(status="paused"), "session status is invalid")
        self.assert_invalid_v2(
            v2_session_dict(attempt_id="not-a-uuid"),
            "canonical UUID",
        )
        assessment = pinned_assessment().to_dict()
        assessment["content_digest"] = "UPPERCASE" + ("a" * 56)
        self.assert_invalid_v2(v2_session_dict(assessment=assessment), "SHA-256 digest")

    def test_abandonment_invariants_reject_illegal_combinations(self) -> None:
        self.assert_invalid_v2(
            v2_session_dict(status=ABANDONED, abandonment=None),
            "require abandonment metadata",
        )
        self.assert_invalid_v2(
            v2_session_dict(
                status=SUBMITTED,
                score=score().to_dict(),
                submitted_at=(STARTED_AT + timedelta(seconds=1)).isoformat(),
                abandonment=AbandonmentMetadata(
                    ended_at=STARTED_AT + timedelta(seconds=2),
                    reason="user_restart",
                ).to_dict(),
            ),
            "must not contain abandonment",
        )
        self.assert_invalid_v2(
            v2_session_dict(
                status=ABANDONED,
                score=score().to_dict(),
                abandonment=AbandonmentMetadata(
                    ended_at=STARTED_AT + timedelta(seconds=2),
                    reason="user_restart",
                ).to_dict(),
            ),
            "must not contain submitted score",
        )


class EventAndReviewV2Tests(unittest.TestCase):
    def test_event_v2_round_trip(self) -> None:
        event = EventRecordV2(
            schema_version=EVENT_SCHEMA_VERSION_V2,
            event_id=EVENT_ID,
            attempt_id=ATTEMPT_ID,
            revision=1,
            occurred_at=STARTED_AT,
            name="abandoned",
            outcome="succeeded",
            arguments={"reason": "user_restart"},
        )
        self.assertEqual(parse_event_record(event.to_dict()), event)

    def test_review_record_round_trip(self) -> None:
        review = pinned_review()
        self.assertEqual(parse_review_record(review.to_dict()), review)
        self.assertTrue(review.source_captured)
        self.assertEqual(review.source.content, SOURCE_CONTENT)

        inconsistent = review.to_dict()
        inconsistent["deadline_at"] = (STARTED_AT + timedelta(seconds=1)).isoformat()
        with self.assertRaisesRegex(InvalidInputError, "effective profile duration"):
            parse_review_record(inconsistent)

        tampered = review.to_dict()
        tampered["source"]["content"] = f"{SOURCE_CONTENT}# tampered\n"
        with self.assertRaisesRegex(InvalidInputError, "does not match its digest"):
            parse_review_record(tampered)

        # A legacy attempt records stored metadata with no content identity.
        legacy = ReviewRecord(
            schema_version=REVIEW_SCHEMA_VERSION,
            attempt_id=ATTEMPT_ID,
            state_revision=1,
            assessment=AssessmentMetadata("file_storage", "File Storage"),
            content_identity=CONTENT_IDENTITY_UNAVAILABLE,
            profile=full_profile(),
            started_at=STARTED_AT,
            deadline_at=STARTED_AT + timedelta(seconds=90 * 60),
            submitted_at=STARTED_AT + timedelta(seconds=30),
            score=score(),
            source=None,
        )
        self.assertEqual(parse_review_record(legacy.to_dict()), legacy)
        self.assertFalse(legacy.source_captured)

        mislabeled = legacy.to_dict()
        mislabeled["content_identity"] = CONTENT_IDENTITY_PINNED
        with self.assertRaises(InvalidInputError):
            parse_review_record(mislabeled)

    def test_review_rejects_unknown_schema_version(self) -> None:
        payload = pinned_review().to_dict()
        payload["schema_version"] = "review/v2"
        with self.assertRaisesRegex(
            UnsupportedSchemaVersionError, "unsupported review schema version"
        ):
            parse_review_record(payload)


class PersistenceVersionDispatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.attempt = Path(self.temporary_directory.name) / str(uuid4())
        self.attempt.mkdir()
        self.persistence = Persistence()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_oversized_session_is_rejected_without_mutation(self) -> None:
        path = self.attempt / "session.json"
        raw = b" " * (MAX_SESSION_BYTES + 1)
        path.write_bytes(raw)
        with self.assertRaisesRegex(SessionCorruptError, "size limit"):
            self.persistence.read_session(self.attempt)
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(list(self.attempt.iterdir()), [path])

    def test_malformed_session_is_rejected_without_mutation(self) -> None:
        path = self.attempt / "session.json"
        raw = b'{"schema_version":'
        path.write_bytes(raw)
        with self.assertRaises(SessionCorruptError):
            self.persistence.read_session(self.attempt)
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(list(self.attempt.iterdir()), [path])

    def test_writer_does_not_publish_a_session_its_reader_would_reject(self) -> None:
        original = v1_session()
        self.persistence.write_session(self.attempt, original)
        path = self.attempt / "session.json"
        before = path.read_bytes()
        oversized = replace(
            original,
            assessment=AssessmentMetadata("file_storage", "x" * MAX_SESSION_BYTES),
        )
        with self.assertRaisesRegex(SessionCorruptError, "size limit"):
            self.persistence.write_session(self.attempt, oversized)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.persistence.read_session(self.attempt), original)

    def test_v1_disk_bytes_remain_unchanged_after_read(self) -> None:
        session = v1_session()
        self.persistence.write_session(self.attempt, session)
        before = (self.attempt / "session.json").read_bytes()
        loaded = self.persistence.read_session(self.attempt)
        after = (self.attempt / "session.json").read_bytes()

        self.assertEqual(loaded, session)
        self.assertEqual(before, after)

    def test_v2_session_round_trip_through_persistence(self) -> None:
        session = abandoned_v2()
        self.persistence.write_session(self.attempt, session)
        self.assertEqual(self.persistence.read_session(self.attempt), session)

    def test_unknown_session_version_fails_closed_on_read(self) -> None:
        path = self.attempt / "session.json"
        path.write_bytes(
            json.dumps(
                {"schema_version": "session/v9", "attempt_id": ATTEMPT_ID},
                sort_keys=True,
            ).encode()
        )
        with self.assertRaisesRegex(SessionCorruptError, "unsupported schema version"):
            self.persistence.read_session(self.attempt)

    def test_unknown_event_version_fails_closed_on_read(self) -> None:
        path = self.attempt / "events.jsonl"
        path.write_bytes(
            json.dumps({"schema_version": "event/v9", "event_id": EVENT_ID}).encode()
            + b"\n"
        )
        with self.assertRaisesRegex(SessionCorruptError, "unsupported schema version"):
            self.persistence.read_events(self.attempt)

    def test_write_rejects_unsupported_session_schema_before_mutation(self) -> None:
        session = v2_session()
        object.__setattr__(session, "schema_version", "session/v9")
        with self.assertRaisesRegex(
            UnsupportedSchemaVersionError, "unsupported session schema version"
        ):
            self.persistence.write_session(self.attempt, session)
        self.assertFalse((self.attempt / "session.json").exists())

    def test_append_rejects_unsupported_event_schema_before_mutation(self) -> None:
        event = EventRecordV2(
            schema_version=EVENT_SCHEMA_VERSION_V2,
            event_id=EVENT_ID,
            attempt_id=ATTEMPT_ID,
            revision=0,
            occurred_at=STARTED_AT,
            name="started",
            outcome="succeeded",
            arguments={},
        )
        object.__setattr__(event, "schema_version", "event/v9")
        with self.assertRaisesRegex(
            UnsupportedSchemaVersionError, "unsupported event schema version"
        ):
            self.persistence.append_event(self.attempt, event)
        self.assertFalse((self.attempt / "events.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
