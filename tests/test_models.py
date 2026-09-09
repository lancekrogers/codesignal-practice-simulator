"""Pure validation and serialization tests for durable runtime models."""

from __future__ import annotations

import copy
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from codesignal_practice_simulator.clock import Clock, UTCClock
from codesignal_practice_simulator.errors import (
    CandidateFailureError,
    ExitCode,
    IllegalLifecycleError,
    InvalidInputError,
    LockUnavailableError,
    SessionCorruptError,
    SessionUnavailableError,
)
from codesignal_practice_simulator.models import (
    ACTIVE,
    ACTIVE_POINTER_SCHEMA_VERSION,
    DRILL_MODE,
    DRILL_PROFILE,
    EVENT_SCHEMA_VERSION,
    EXPIRED,
    FULL_DURATION_SECONDS,
    FULL_MODE,
    FULL_PROFILE,
    SESSION_SCHEMA_VERSION,
    SUBMITTED,
    ActivePointer,
    AssessmentMetadata,
    EventRecord,
    LevelResult,
    ModeProfile,
    ScoreSummary,
    SessionState,
)


ATTEMPT_ID = "123e4567-e89b-12d3-a456-426614174000"
EVENT_ID = "123e4567-e89b-12d3-a456-426614174001"
STARTED_AT = datetime(2026, 9, 8, 19, 0, tzinfo=timezone.utc)


def assessment() -> AssessmentMetadata:
    return AssessmentMetadata("file_storage", "File Storage")


def full_profile() -> ModeProfile:
    return ModeProfile(FULL_MODE, FULL_PROFILE, FULL_DURATION_SECONDS)


def score() -> ScoreSummary:
    return ScoreSummary(
        (
            LevelResult(1, "passed"),
            LevelResult(2, "failed"),
            LevelResult(3, "error"),
            LevelResult(4, "passed"),
        )
    )


def session(
    *,
    status: str = ACTIVE,
    session_score: ScoreSummary | None = None,
    submitted_at: datetime | None = None,
) -> SessionState:
    return SessionState(
        schema_version=SESSION_SCHEMA_VERSION,
        attempt_id=ATTEMPT_ID,
        assessment=assessment(),
        profile=full_profile(),
        started_at=STARTED_AT,
        deadline_at=STARTED_AT + timedelta(seconds=FULL_DURATION_SECONDS),
        status=status,  # type: ignore[arg-type]
        revision=2,
        score=session_score,
        submitted_at=submitted_at,
    )


def invalid_session(**changes: object) -> dict[str, object]:
    value = copy.deepcopy(session().to_dict())
    value.update(changes)
    return value


class ModelRoundTripTests(unittest.TestCase):
    def test_assessment_profile_score_session_and_pointer_round_trip(self) -> None:
        original_session = session(
            status=SUBMITTED,
            session_score=score(),
            submitted_at=STARTED_AT + timedelta(seconds=13),
        )
        original_pointer = ActivePointer(ACTIVE_POINTER_SCHEMA_VERSION, ATTEMPT_ID)

        self.assertEqual(
            AssessmentMetadata.from_dict(assessment().to_dict()),
            assessment(),
        )
        self.assertEqual(ModeProfile.from_dict(full_profile().to_dict()), full_profile())
        self.assertEqual(ScoreSummary.from_dict(score().to_dict()), score())
        self.assertEqual(SessionState.from_dict(original_session.to_dict()), original_session)
        self.assertEqual(
            ActivePointer.from_dict(original_pointer.to_dict()), original_pointer
        )

    def test_drill_profile_persists_an_explicit_duration_override(self) -> None:
        profile = ModeProfile(DRILL_MODE, DRILL_PROFILE, 12 * 60)

        self.assertEqual(ModeProfile.from_dict(profile.to_dict()), profile)

    def test_event_round_trip_and_arguments_are_immutable(self) -> None:
        arguments = {"groups": [1, 2], "options": {"json": True}, "duration": None}
        event = EventRecord(
            schema_version=EVENT_SCHEMA_VERSION,
            event_id=EVENT_ID,
            attempt_id=ATTEMPT_ID,
            revision=2,
            occurred_at=STARTED_AT,
            name="tested",
            outcome="succeeded",
            arguments=arguments,
        )
        arguments["groups"].append(3)

        self.assertEqual(event.to_dict()["arguments"]["groups"], [1, 2])  # type: ignore[index]
        self.assertEqual(EventRecord.from_dict(event.to_dict()), event)
        with self.assertRaises(TypeError):
            event.arguments["json"] = True

    def test_score_summary_derives_counts_from_independent_results(self) -> None:
        summary = score()

        self.assertEqual(summary.passed_levels, 2)
        self.assertEqual(summary.highest_contiguous_level, 1)


class SchemaValidationTests(unittest.TestCase):
    def assert_invalid(self, value: object, message: str) -> None:
        with self.assertRaisesRegex(InvalidInputError, message):
            SessionState.from_dict(value)

    def test_session_rejects_unsupported_schema_and_invalid_field_sets(self) -> None:
        self.assert_invalid(
            invalid_session(schema_version="session/v2"), "unsupported session schema"
        )
        missing = invalid_session()
        del missing["revision"]
        self.assert_invalid(missing, "invalid field set")
        self.assert_invalid(invalid_session(extra=True), "invalid field set")

    def test_session_rejects_malformed_ids_and_revisions(self) -> None:
        self.assert_invalid(invalid_session(attempt_id="not-a-uuid"), "canonical UUID")
        self.assert_invalid(invalid_session(revision=-1), "non-negative integer")
        self.assert_invalid(invalid_session(revision=True), "non-negative integer")

    def test_session_rejects_naive_non_utc_and_malformed_timestamps(self) -> None:
        self.assert_invalid(
            invalid_session(started_at="2026-09-08T19:00:00"), "timezone-aware"
        )
        self.assert_invalid(
            invalid_session(started_at="2026-09-08T19:00:00+01:00"), "UTC timestamp"
        )
        self.assert_invalid(invalid_session(started_at="not-a-date"), "ISO-8601")

    def test_session_rejects_deadline_order_and_duration_mismatch(self) -> None:
        self.assert_invalid(
            invalid_session(deadline_at="2026-09-08T19:00:00+00:00"),
            "deadline_at must be after",
        )
        self.assert_invalid(
            invalid_session(deadline_at="2026-09-08T20:00:00+00:00"),
            "effective profile duration",
        )

    def test_assessment_rejects_unknown_and_malformed_values(self) -> None:
        value = assessment().to_dict()
        value["assessment_id"] = "File Storage"
        with self.assertRaisesRegex(InvalidInputError, "lowercase identifier"):
            AssessmentMetadata.from_dict(value)
        value = assessment().to_dict()
        value["level_count"] = 3
        with self.assertRaisesRegex(InvalidInputError, "level_count must be 4"):
            AssessmentMetadata.from_dict(value)

    def test_profile_rejects_unknown_profile_mode_and_duration(self) -> None:
        with self.assertRaisesRegex(InvalidInputError, "mode must be full or drill"):
            ModeProfile.from_dict(
                {"mode": "practice", "profile_id": FULL_PROFILE, "duration_seconds": 1}
            )
        with self.assertRaisesRegex(InvalidInputError, "drill mode requires"):
            ModeProfile(DRILL_MODE, "other", 60)
        with self.assertRaisesRegex(InvalidInputError, "5400 seconds"):
            ModeProfile(FULL_MODE, FULL_PROFILE, 60)
        with self.assertRaisesRegex(InvalidInputError, "positive integer"):
            ModeProfile(DRILL_MODE, DRILL_PROFILE, 0)

    def test_score_rejects_every_invalid_four_level_shape(self) -> None:
        cases = (
            (
                {
                    "levels": [{"level": 1, "outcome": "passed"}],
                    "passed_levels": 1,
                    "highest_contiguous_level": 1,
                },
                "exactly four",
            ),
            (
                {
                    "levels": [
                        {"level": 2, "outcome": "passed"},
                        {"level": 1, "outcome": "passed"},
                        {"level": 3, "outcome": "passed"},
                        {"level": 4, "outcome": "passed"},
                    ],
                    "passed_levels": 4,
                    "highest_contiguous_level": 4,
                },
                "ordered",
            ),
            (
                {
                    "levels": [
                        {"level": 1, "outcome": "unknown"},
                        {"level": 2, "outcome": "passed"},
                        {"level": 3, "outcome": "passed"},
                        {"level": 4, "outcome": "passed"},
                    ],
                    "passed_levels": 3,
                    "highest_contiguous_level": 0,
                },
                "outcome",
            ),
            (
                {
                    "levels": [
                        {"level": 1, "outcome": "passed"},
                        {"level": 2, "outcome": "failed"},
                        {"level": 3, "outcome": "passed"},
                        {"level": 4, "outcome": "passed"},
                    ],
                    "passed_levels": 4,
                    "highest_contiguous_level": 1,
                },
                "passed_levels does not match",
            ),
            (
                {
                    "levels": [
                        {"level": 1, "outcome": "passed"},
                        {"level": 2, "outcome": "failed"},
                        {"level": 3, "outcome": "passed"},
                        {"level": 4, "outcome": "passed"},
                    ],
                    "passed_levels": 3,
                    "highest_contiguous_level": 4,
                },
                "highest_contiguous_level does not match",
            ),
        )
        for value, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(InvalidInputError, message):
                    ScoreSummary.from_dict(value)

    def test_session_rejects_malformed_score_object(self) -> None:
        self.assert_invalid(invalid_session(score=[]), "score must be an object")

    def test_session_rejects_illegal_submission_combinations(self) -> None:
        self.assert_invalid(
            invalid_session(status=ACTIVE, submitted_at="2026-09-08T19:00:01+00:00"),
            "only submitted",
        )
        self.assert_invalid(
            invalid_session(status=EXPIRED, submitted_at="2026-09-08T19:00:01+00:00"),
            "only submitted",
        )
        self.assert_invalid(
            invalid_session(status=SUBMITTED, score=None, submitted_at=None),
            "require score and submitted_at",
        )
        self.assert_invalid(
            invalid_session(
                status=SUBMITTED,
                score=score().to_dict(),
                submitted_at="2026-09-08T18:59:59+00:00",
            ),
            "must not precede",
        )

    def test_event_rejects_invalid_schema_ids_timestamps_and_arguments(self) -> None:
        valid = {
            "schema_version": EVENT_SCHEMA_VERSION,
            "event_id": EVENT_ID,
            "attempt_id": ATTEMPT_ID,
            "revision": 0,
            "occurred_at": "2026-09-08T19:00:00+00:00",
            "name": "started",
            "outcome": "succeeded",
            "arguments": {},
        }
        cases = (
            ({"schema_version": "event/v2"}, "unsupported event schema"),
            ({"event_id": "bad"}, "canonical UUID"),
            ({"occurred_at": "2026-09-08T19:00:00"}, "timezone-aware"),
            ({"outcome": "unknown"}, "event outcome"),
            ({"arguments": {"bad": {1, 2}}}, "JSON values"),
        )
        for change, message in cases:
            with self.subTest(message=message):
                value = {**valid, **change}
                with self.assertRaisesRegex(InvalidInputError, message):
                    EventRecord.from_dict(value)

    def test_active_pointer_rejects_unknown_schema_invalid_id_and_extra_field(self) -> None:
        with self.assertRaisesRegex(InvalidInputError, "unsupported active pointer"):
            ActivePointer.from_dict(
                {"schema_version": "active-pointer/v2", "attempt_id": ATTEMPT_ID}
            )
        with self.assertRaisesRegex(InvalidInputError, "canonical UUID"):
            ActivePointer.from_dict(
                {"schema_version": ACTIVE_POINTER_SCHEMA_VERSION, "attempt_id": "bad"}
            )
        with self.assertRaisesRegex(InvalidInputError, "invalid field set"):
            ActivePointer.from_dict(
                {
                    "schema_version": ACTIVE_POINTER_SCHEMA_VERSION,
                    "attempt_id": ATTEMPT_ID,
                    "extra": True,
                }
            )


class ErrorAndClockTests(unittest.TestCase):
    def test_domain_errors_have_stable_exit_classes(self) -> None:
        cases = (
            (InvalidInputError("bad"), ExitCode.INVALID_INPUT),
            (SessionUnavailableError("missing"), ExitCode.SESSION_UNAVAILABLE),
            (SessionCorruptError("corrupt"), ExitCode.SESSION_UNAVAILABLE),
            (IllegalLifecycleError("expired"), ExitCode.ILLEGAL_LIFECYCLE),
            (LockUnavailableError("locked"), ExitCode.ILLEGAL_LIFECYCLE),
            (CandidateFailureError("failed"), ExitCode.CANDIDATE_FAILURE),
        )

        for error, expected in cases:
            with self.subTest(error=type(error).__name__):
                self.assertEqual(error.exit_code, expected)
                self.assertEqual(str(error), error.message)

    def test_clock_protocol_accepts_a_fake_clock_and_utc_clock_returns_utc(self) -> None:
        class FakeClock:
            def now(self) -> datetime:
                return STARTED_AT

        fake = FakeClock()
        self.assertIsInstance(fake, Clock)
        self.assertEqual(fake.now(), STARTED_AT)
        self.assertEqual(UTCClock().now().utcoffset(), timedelta(0))


if __name__ == "__main__":
    unittest.main()
