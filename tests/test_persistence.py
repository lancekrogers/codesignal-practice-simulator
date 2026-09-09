"""Tests for atomic state, event-log recovery, pointers, and locks."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
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
    ActivePointer,
    AssessmentMetadata,
    EventRecord,
    ModeProfile,
    SessionState,
)
from codesignal_practice_simulator.persistence import Persistence, initial_event


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
