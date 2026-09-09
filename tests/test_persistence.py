"""Tests for atomic state, event-log recovery, pointers, and locks."""

from __future__ import annotations

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

from codesignal_practice_simulator.clock import Clock
from codesignal_practice_simulator.errors import LockUnavailableError, SessionCorruptError
from codesignal_practice_simulator.filesystem import LocalFilesystem
from codesignal_practice_simulator.models import (
    ACTIVE,
    ACTIVE_POINTER_SCHEMA_VERSION,
    EVENT_SCHEMA_VERSION,
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
from codesignal_practice_simulator.persistence import (
    SUBMISSION_RECOVERY_FILENAME,
    Persistence,
    initial_event,
)


class FixedClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


class FailingFilesystem(LocalFilesystem):
    """Fails one requested operation while retaining normal filesystem behavior."""

    def __init__(self, operation: str) -> None:
        self.operation = operation
        self.calls = 0

    def _fail(self, operation: str) -> None:
        if operation == self.operation:
            self.calls += 1
            raise OSError(f"injected {operation} failure")

    def write_bytes(self, path: Path, data: bytes) -> None:
        self._fail("write")
        super().write_bytes(path, data)

    def flush_file(self, path: Path) -> None:
        self._fail("flush")
        super().flush_file(path)

    def replace(self, source: Path, destination: Path) -> None:
        self._fail("replace")
        super().replace(source, destination)


class FlushAfterAppendFilesystem(LocalFilesystem):
    """Report one event flush failure after its bytes have been written."""

    def __init__(self) -> None:
        self.after_event_append = False
        self.failed = False

    def append_bytes(self, path: Path, data: bytes) -> None:
        super().append_bytes(path, data)
        self.after_event_append = path.name == "events.jsonl"

    def flush_file(self, path: Path) -> None:
        super().flush_file(path)
        if self.after_event_append and path.name == "events.jsonl" and not self.failed:
            self.failed = True
            raise OSError("injected event flush failure after append")


class ReplaceAfterSessionWriteFilesystem(LocalFilesystem):
    """Report one failure only after atomically publishing the target session."""

    def __init__(self) -> None:
        self.failed = False

    def replace(self, source: Path, destination: Path) -> None:
        super().replace(source, destination)
        if destination.name == "session.json" and not self.failed:
            self.failed = True
            raise OSError("injected session replace failure after write")


def state(attempt_id: str, revision: int = 0) -> SessionState:
    started = datetime(2026, 9, 8, 19, tzinfo=timezone.utc)
    return SessionState(
        schema_version=SESSION_SCHEMA_VERSION,
        attempt_id=attempt_id,
        assessment=AssessmentMetadata("file_storage", "File Storage"),
        profile=ModeProfile(FULL_MODE, FULL_PROFILE, FULL_DURATION_SECONDS),
        started_at=started,
        deadline_at=started + timedelta(seconds=FULL_DURATION_SECONDS),
        status=ACTIVE,
        revision=revision,
    )


def submitted_state(session: SessionState) -> SessionState:
    return replace(
        session,
        status=SUBMITTED,
        revision=session.revision + 1,
        score=ScoreSummary(tuple(LevelResult(level, "passed") for level in range(1, 5))),
        submitted_at=session.started_at,
    )


def submitted_event(session: SessionState) -> EventRecord:
    return EventRecord(
        schema_version=EVENT_SCHEMA_VERSION,
        event_id=str(uuid4()),
        attempt_id=session.attempt_id,
        revision=session.revision,
        occurred_at=session.submitted_at,  # type: ignore[arg-type]
        name="submitted",
        outcome="succeeded",
        arguments={},
    )


class PersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.attempt = Path(self.temporary_directory.name) / str(uuid4())
        self.attempt.mkdir()
        self.persistence = Persistence()
        self.session = state(self.attempt.name)
        self.persistence.write_session(self.attempt, self.session)
        self.persistence.append_event(self.attempt, initial_event(self.session))

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_session_and_pointer_use_flushed_sibling_replacements(self) -> None:
        before = (self.attempt / "session.json").read_bytes()
        replacement = state(self.attempt.name, revision=1)
        self.persistence.write_session(self.attempt, replacement)

        self.assertNotEqual((self.attempt / "session.json").read_bytes(), before)
        self.assertEqual(self.persistence.read_session(self.attempt), replacement)
        temporary_root = Path(self.temporary_directory.name) / "attempts"
        temporary_root.mkdir()
        pointer = ActivePointer(ACTIVE_POINTER_SCHEMA_VERSION, self.attempt.name)
        self.persistence.write_active_pointer(temporary_root, pointer)
        self.assertEqual(self.persistence.read_active_pointer(temporary_root), pointer)
        self.assertFalse(list(temporary_root.glob("*.tmp*")))

    def test_state_write_faults_preserve_previous_session_bytes(self) -> None:
        original = (self.attempt / "session.json").read_bytes()
        for operation in ("write", "flush", "replace"):
            with self.subTest(operation=operation):
                persistence = Persistence(FailingFilesystem(operation))
                with self.assertRaisesRegex(OSError, f"injected {operation}"):
                    persistence.write_session(self.attempt, state(self.attempt.name, 1))
                self.assertEqual((self.attempt / "session.json").read_bytes(), original)
                self.assertFalse(list(self.attempt.glob(".session.json.*.tmp")))

    def test_pointer_write_faults_preserve_previous_pointer_bytes(self) -> None:
        attempts = Path(self.temporary_directory.name) / "pointers"
        attempts.mkdir()
        original = ActivePointer(ACTIVE_POINTER_SCHEMA_VERSION, self.attempt.name)
        self.persistence.write_active_pointer(attempts, original)
        before = (attempts / "active.json").read_bytes()
        replacement = ActivePointer(ACTIVE_POINTER_SCHEMA_VERSION, str(uuid4()))

        for operation in ("write", "flush", "replace"):
            with self.subTest(operation=operation):
                with self.assertRaises(OSError):
                    Persistence(FailingFilesystem(operation)).write_active_pointer(
                        attempts, replacement
                    )
                self.assertEqual((attempts / "active.json").read_bytes(), before)

    def test_jsonl_rejects_bad_nonfinal_records_and_only_ignores_one_tail(self) -> None:
        events = self.attempt / "events.jsonl"
        valid = json.dumps(initial_event(self.session).to_dict()).encode()
        events.write_bytes(valid + b"\n{not json}\n")
        with self.assertRaisesRegex(SessionCorruptError, "malformed JSONL"):
            self.persistence.read_events(self.attempt)
        events.write_bytes(valid + b"\n{not json}")
        self.assertEqual(len(self.persistence.read_events(self.attempt)), 1)

        events.write_bytes(valid + b"\n{not json}\ntrailing")
        with self.assertRaisesRegex(SessionCorruptError, "malformed JSONL"):
            self.persistence.read_events(self.attempt)

    def test_events_reject_duplicate_event_ids(self) -> None:
        event = initial_event(self.session)
        (self.attempt / "events.jsonl").write_bytes(
            json.dumps(event.to_dict()).encode("utf-8")
            + b"\n"
            + json.dumps(event.to_dict()).encode("utf-8")
            + b"\n"
        )

        with self.assertRaisesRegex(SessionCorruptError, "duplicate event ID"):
            self.persistence.read_events(self.attempt)

    def test_locked_append_rejects_an_incoming_duplicate_id_without_rewriting(self) -> None:
        existing = initial_event(self.session)
        incoming = replace(existing, name="tested")
        events = self.attempt / "events.jsonl"

        for delimiter in (b"\n", b""):
            with self.subTest(unterminated=not delimiter):
                before = json.dumps(existing.to_dict()).encode("utf-8") + delimiter
                events.write_bytes(before)

                with self.persistence.attempt_lock(self.attempt):
                    with self.assertRaisesRegex(SessionCorruptError, "duplicate event ID"):
                        self.persistence.append_event_locked(self.attempt, incoming)

                self.assertEqual(events.read_bytes(), before)

    def test_recovery_appends_one_event_for_a_missing_authoritative_revision(self) -> None:
        revised = state(self.attempt.name, revision=1)
        self.persistence.write_session(self.attempt, revised)
        clock: Clock = FixedClock(datetime(2026, 9, 8, 20, tzinfo=timezone.utc))

        recovered = self.persistence.recover_missing_state_event(self.attempt, clock)

        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.revision, 1)  # type: ignore[union-attr]
        self.assertEqual(recovered.outcome, "recovered")  # type: ignore[union-attr]
        before = (self.attempt / "events.jsonl").read_bytes()
        self.assertIsNone(self.persistence.recover_missing_state_event(self.attempt, clock))
        self.assertEqual((self.attempt / "events.jsonl").read_bytes(), before)

    def test_recovery_rewrites_a_valid_unterminated_event_before_appending(self) -> None:
        revised = state(self.attempt.name, revision=1)
        self.persistence.write_session(self.attempt, revised)
        (self.attempt / "events.jsonl").write_bytes(
            json.dumps(initial_event(self.session).to_dict()).encode("utf-8")
        )
        clock: Clock = FixedClock(datetime(2026, 9, 8, 20, tzinfo=timezone.utc))

        recovered = self.persistence.recover_missing_state_event(self.attempt, clock)

        self.assertIsNotNone(recovered)
        self.assertEqual(
            [(event.name, event.revision) for event in self.persistence.read_events(self.attempt)],
            [("started", 0), ("recovered", 1)],
        )
        self.assertTrue((self.attempt / "events.jsonl").read_bytes().endswith(b"\n"))

    def test_ordinary_append_rejects_a_malformed_incomplete_tail_without_rewriting_it(self) -> None:
        events = self.attempt / "events.jsonl"
        before = events.read_bytes() + b'{"unrelated":'
        events.write_bytes(before)

        with self.assertRaisesRegex(SessionCorruptError, "incomplete malformed tail"):
            self.persistence.append_event(self.attempt, initial_event(self.session))

        self.assertEqual(events.read_bytes(), before)
        self.assertEqual(len(self.persistence.read_events(self.attempt)), 1)

    def test_locked_recovery_does_not_reacquire_the_attempt_lock(self) -> None:
        revised = state(self.attempt.name, revision=1)
        self.persistence.write_session(self.attempt, revised)
        clock: Clock = FixedClock(datetime(2026, 9, 8, 20, tzinfo=timezone.utc))

        with self.persistence.attempt_lock(self.attempt):
            recovered = self.persistence.recover_missing_state_event_locked(
                self.attempt, revised, clock
            )

        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.revision, revised.revision)  # type: ignore[union-attr]

    def test_submission_recovery_rewrites_an_event_whose_flush_failed_after_append(self) -> None:
        submitted = submitted_state(self.session)
        event = submitted_event(submitted)
        failing = Persistence(FlushAfterAppendFilesystem())

        with failing.attempt_lock(self.attempt):
            failing.write_submission_recovery_locked(
                self.attempt, self.session, submitted, event
            )
            recovered = failing.recover_submission_locked(self.attempt)

        self.assertEqual(recovered, submitted)
        self.assertEqual(failing.read_session(self.attempt), submitted)
        events = failing.read_events(self.attempt)
        self.assertEqual([record for record in events if record.name == "submitted"], [event])
        self.assertFalse((self.attempt / SUBMISSION_RECOVERY_FILENAME).exists())

    def test_submission_recovery_survives_a_reported_session_publish_failure(self) -> None:
        submitted = submitted_state(self.session)
        event = submitted_event(submitted)
        with self.persistence.attempt_lock(self.attempt):
            self.persistence.write_submission_recovery_locked(
                self.attempt, self.session, submitted, event
            )

        failing = Persistence(ReplaceAfterSessionWriteFilesystem())
        with failing.attempt_lock(self.attempt):
            with self.assertRaisesRegex(OSError, "session replace failure"):
                failing.recover_submission_locked(self.attempt)

        self.assertEqual(failing.read_session(self.attempt), submitted)
        self.assertEqual(
            [record for record in failing.read_events(self.attempt) if record.name == "submitted"],
            [],
        )
        self.assertTrue((self.attempt / SUBMISSION_RECOVERY_FILENAME).exists())
        with self.persistence.attempt_lock(self.attempt):
            self.assertEqual(self.persistence.recover_submission_locked(self.attempt), submitted)
        self.assertEqual(
            [record for record in self.persistence.read_events(self.attempt) if record.name == "submitted"],
            [event],
        )
        self.assertFalse((self.attempt / SUBMISSION_RECOVERY_FILENAME).exists())

    def test_submission_recovery_rejects_a_session_other_than_its_exact_endpoints(self) -> None:
        submitted = submitted_state(self.session)
        event = submitted_event(submitted)
        unexpected = replace(self.session, revision=1)
        with self.persistence.attempt_lock(self.attempt):
            self.persistence.write_submission_recovery_locked(
                self.attempt, self.session, submitted, event
            )
            self.persistence.write_session_locked(self.attempt, unexpected)
            with self.assertRaisesRegex(SessionCorruptError, "state does not match"):
                self.persistence.recover_submission_locked(self.attempt)

        self.assertTrue((self.attempt / SUBMISSION_RECOVERY_FILENAME).exists())
        self.assertEqual(self.persistence.read_session(self.attempt), unexpected)
        self.assertEqual(
            [record for record in self.persistence.read_events(self.attempt) if record.name == "submitted"],
            [],
        )

    def test_submission_recovery_rejects_a_conflicting_event_without_publishing_state(self) -> None:
        submitted = submitted_state(self.session)
        event = submitted_event(submitted)
        other_event = EventRecord(
            schema_version=EVENT_SCHEMA_VERSION,
            event_id=str(uuid4()),
            attempt_id=submitted.attempt_id,
            revision=submitted.revision,
            occurred_at=submitted.submitted_at,  # type: ignore[arg-type]
            name="tested",
            outcome="succeeded",
            arguments={},
        )
        with self.persistence.attempt_lock(self.attempt):
            self.persistence.write_submission_recovery_locked(
                self.attempt, self.session, submitted, event
            )
            self.persistence.append_event_locked(self.attempt, other_event)

            marker_before = (
                self.attempt / SUBMISSION_RECOVERY_FILENAME
            ).read_bytes()
            events_before = (self.attempt / "events.jsonl").read_bytes()
            session_before = (self.attempt / "session.json").read_bytes()
            with self.assertRaisesRegex(
                SessionCorruptError, "expected revision has an unexpected event"
            ):
                self.persistence.recover_submission_locked(self.attempt)

        self.assertEqual(
            (self.attempt / SUBMISSION_RECOVERY_FILENAME).read_bytes(), marker_before
        )
        self.assertEqual((self.attempt / "events.jsonl").read_bytes(), events_before)
        self.assertEqual((self.attempt / "session.json").read_bytes(), session_before)
        events = self.persistence.read_events(self.attempt)
        self.assertEqual(
            [record.revision for record in events],
            [self.session.revision, submitted.revision],
        )
        self.assertEqual(events[-1], other_event)
        self.assertFalse(
            any(record.name == "submitted" for record in events)
        )

    def test_recovery_rejects_event_records_owned_by_another_attempt(self) -> None:
        foreign = EventRecord(
            schema_version=EVENT_SCHEMA_VERSION,
            event_id=str(uuid4()),
            attempt_id=str(uuid4()),
            revision=0,
            occurred_at=self.session.started_at,
            name="started",
            outcome="succeeded",
            arguments={},
        )
        (self.attempt / "events.jsonl").write_text(
            json.dumps(foreign.to_dict()) + "\n", encoding="utf-8"
        )

        with self.assertRaisesRegex(SessionCorruptError, "different attempt"):
            self.persistence.recover_missing_state_event(
                self.attempt,
                FixedClock(datetime(2026, 9, 8, 20, tzinfo=timezone.utc)),
            )

    def test_invalid_pointer_is_a_corruption_error(self) -> None:
        attempts = Path(self.temporary_directory.name) / "pointers"
        attempts.mkdir()
        (attempts / "active.json").write_text("{bad", encoding="utf-8")

        with self.assertRaisesRegex(SessionCorruptError, "active pointer"):
            self.persistence.read_active_pointer(attempts)

    def test_attempt_and_workspace_locks_reject_contention(self) -> None:
        attempts = Path(self.temporary_directory.name) / "attempts"
        attempts.mkdir()
        with self.persistence.attempt_lock(self.attempt):
            with self.assertRaises(LockUnavailableError):
                self.persistence.write_session(self.attempt, state(self.attempt.name, 1))
        with self.persistence.workspace_lock(attempts):
            with self.assertRaises(LockUnavailableError):
                self.persistence.write_active_pointer(
                    attempts,
                    ActivePointer(ACTIVE_POINTER_SCHEMA_VERSION, self.attempt.name),
                )

    def test_event_schema_corruption_is_not_an_incomplete_tail(self) -> None:
        invalid = {
            "schema_version": EVENT_SCHEMA_VERSION,
            "event_id": str(uuid4()),
            "attempt_id": self.attempt.name,
            "revision": 0,
            "occurred_at": "2026-09-08T19:00:00+00:00",
            "name": "started",
            "outcome": "wrong",
            "arguments": {},
        }
        (self.attempt / "events.jsonl").write_text(json.dumps(invalid), encoding="utf-8")

        with self.assertRaisesRegex(SessionCorruptError, "invalid record"):
            self.persistence.read_events(self.attempt)


if __name__ == "__main__":
    unittest.main()
