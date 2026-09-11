"""Atomic state, event-log, pointer, and advisory-lock primitives."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from .clock import Clock
from .errors import (
    LockUnavailableError,
    SessionCorruptError,
    SessionUnavailableError,
    UnsupportedSchemaVersionError,
)
from .filesystem import Filesystem, LocalFilesystem
from .models import (
    EVENT_SCHEMA_VERSION,
    EVENT_SCHEMA_VERSION_V2,
    MAX_REVIEW_BYTES,
    SESSION_SCHEMA_VERSION,
    SESSION_SCHEMA_VERSION_V2,
    ActivePointer,
    EventRecordUnion,
    ReviewRecord,
    SessionRecord,
    SubmissionRecovery,
    canonical_review_bytes,
    parse_event_record,
    parse_review_record,
    parse_session_record,
    session_event,
)

try:  # The supported local runtime is POSIX; keep the import failure explicit.
    import fcntl
except ImportError:  # pragma: no cover - exercised only on unsupported platforms.
    fcntl = None  # type: ignore[assignment]


SESSION_FILENAME = "session.json"
EVENTS_FILENAME = "events.jsonl"
ACTIVE_FILENAME = "active.json"
ATTEMPT_LOCK_FILENAME = ".session.lock"
WORKSPACE_LOCK_FILENAME = ".workspace.lock"
SUBMISSION_RECOVERY_FILENAME = ".submission-recovery.json"
REVIEW_FILENAME = "review.json"
MAX_SESSION_BYTES = 1024 * 1024

# Schema families (CP0002): readers dispatch on schema_version without upgrading
# disk. New attempts write session/v2 and event/v2; existing v1 attempts keep
# writing v1 records, and their submission-recovery/v1 replay is unchanged.
_SUPPORTED_SESSION_SCHEMA_VERSIONS = frozenset(
    (SESSION_SCHEMA_VERSION, SESSION_SCHEMA_VERSION_V2)
)
_SUPPORTED_EVENT_SCHEMA_VERSIONS = frozenset(
    (EVENT_SCHEMA_VERSION, EVENT_SCHEMA_VERSION_V2)
)

_PROCESS_LOCK = threading.Lock()
_HELD_LOCKS: set[Path] = set()
_EventLogTail = Literal["complete", "valid", "malformed"]


def _json_bytes(value: object, *, newline: bool = True) -> bytes:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (text + ("\n" if newline else "")).encode("utf-8")


class Persistence:
    """Own all durable state formats and their atomic filesystem discipline."""

    def __init__(self, filesystem: Filesystem | None = None) -> None:
        self.filesystem = LocalFilesystem() if filesystem is None else filesystem

    @contextmanager
    def attempt_lock(self, attempt_directory: Path) -> Iterator[None]:
        """Take the non-blocking lock that serializes one attempt's mutations."""
        with self._lock(attempt_directory / ATTEMPT_LOCK_FILENAME):
            yield

    @contextmanager
    def workspace_lock(self, attempts_directory: Path) -> Iterator[None]:
        """Take the non-blocking lock that serializes root-pointer mutations."""
        with self._lock(attempts_directory / WORKSPACE_LOCK_FILENAME):
            yield

    @contextmanager
    def _lock(self, path: Path) -> Iterator[None]:
        if fcntl is None:  # pragma: no cover - the project supports POSIX local use.
            raise LockUnavailableError("advisory file locks are unavailable on this platform")
        resolved = path.resolve()
        with _PROCESS_LOCK:
            if resolved in _HELD_LOCKS:
                raise LockUnavailableError(f"workspace is busy: {path}")
            _HELD_LOCKS.add(resolved)
        stream = None
        try:
            stream = self.filesystem.open_lock(path)
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                raise LockUnavailableError(f"workspace is busy: {path}") from error
            yield
        finally:
            if stream is not None:
                try:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
                finally:
                    stream.close()
            with _PROCESS_LOCK:
                _HELD_LOCKS.discard(resolved)

    def read_session(self, attempt_directory: Path) -> SessionRecord:
        """Read and schema-validate authoritative session state."""
        return self._read_model(
            attempt_directory / SESSION_FILENAME,
            parse_session_record,
            "session",
            max_bytes=MAX_SESSION_BYTES,
        )

    def write_session(self, attempt_directory: Path, state: SessionRecord) -> None:
        """Atomically replace session state while holding the attempt lock."""
        with self.attempt_lock(attempt_directory):
            self.write_session_locked(attempt_directory, state)

    def write_session_locked(self, attempt_directory: Path, state: SessionRecord) -> None:
        """Atomically replace session state; the caller already owns its lock."""
        self._reject_unsupported_session_schema(state.schema_version)
        raw = _json_bytes(state.to_dict())
        if len(raw) > MAX_SESSION_BYTES:
            raise SessionCorruptError("session exceeds the supported size limit")
        self._atomic_bytes(attempt_directory / SESSION_FILENAME, raw)

    def read_events(self, attempt_directory: Path) -> list[EventRecordUnion]:
        """Read strict JSONL, tolerating one syntactically incomplete final tail."""
        events, _tail = self._read_events(attempt_directory)
        return events

    def _read_events(
        self, attempt_directory: Path, *, missing_is_empty: bool = False
    ) -> tuple[list[EventRecordUnion], _EventLogTail]:
        """Read events and report a final tail that must be rewritten before append."""
        path = attempt_directory / EVENTS_FILENAME
        try:
            raw = self.filesystem.read_bytes(path)
        except FileNotFoundError:
            if missing_is_empty:
                return [], "complete"
            raise SessionUnavailableError(f"cannot read events: {path}") from None
        except OSError as error:
            raise SessionUnavailableError(f"cannot read events: {path}") from error
        if not raw:
            return [], "complete"

        records: list[EventRecordUnion] = []
        event_ids: set[str] = set()
        lines = raw.splitlines(keepends=True)
        for index, raw_line in enumerate(lines):
            complete = raw_line.endswith((b"\n", b"\r"))
            line = raw_line.rstrip(b"\r\n")
            if not line:
                raise SessionCorruptError(f"events contain an empty record: {path}")
            try:
                decoded = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                if index == len(lines) - 1 and not complete:
                    return records, "malformed"
                raise SessionCorruptError(f"events contain malformed JSONL: {path}") from error
            try:
                event = parse_event_record(decoded)
            except UnsupportedSchemaVersionError as error:
                raise SessionCorruptError(
                    f"events contain an unsupported schema version: {path}"
                ) from error
            except Exception as error:
                raise SessionCorruptError(f"events contain an invalid record: {path}") from error
            if event.event_id in event_ids:
                raise SessionCorruptError(f"events contain a duplicate event ID: {path}")
            event_ids.add(event.event_id)
            records.append(event)
        return records, "valid" if not raw.endswith((b"\n", b"\r")) else "complete"

    def append_event(self, attempt_directory: Path, event: EventRecordUnion) -> None:
        """Append one flushed, complete event record while holding the attempt lock."""
        with self.attempt_lock(attempt_directory):
            self.append_event_locked(attempt_directory, event)

    def append_event_locked(
        self, attempt_directory: Path, event: EventRecordUnion
    ) -> None:
        """Append one event; the caller already owns its lock."""
        self._reject_unsupported_event_schema(event.schema_version)
        path = attempt_directory / EVENTS_FILENAME
        events, tail = self._read_events(attempt_directory, missing_is_empty=True)
        if any(existing.event_id == event.event_id for existing in events):
            raise SessionCorruptError(f"events contain a duplicate event ID: {path}")
        if tail == "malformed":
            raise SessionCorruptError(
                f"events contain an incomplete malformed tail: {path}"
            )
        if tail == "valid":
            # A valid event without its JSONL delimiter must be made complete
            # before a direct append.  Otherwise the two objects concatenate
            # into an invalid record.
            self._write_events_locked(attempt_directory, events)
        try:
            self.filesystem.append_bytes(path, _json_bytes(event.to_dict()))
            self.filesystem.flush_file(path)
        except OSError as error:
            raise SessionUnavailableError(f"cannot append event: {path}") from error

    def persist_submission_locked(
        self,
        attempt_directory: Path,
        prior_state: SessionRecord,
        state: SessionRecord,
        event: EventRecordUnion,
        review: ReviewRecord | None = None,
    ) -> None:
        """Write ahead one scored submission, then complete its exact durable pair."""
        self.write_submission_recovery_locked(
            attempt_directory, prior_state, state, event, review
        )
        self.recover_submission_locked(attempt_directory)

    def write_submission_recovery_locked(
        self,
        attempt_directory: Path,
        prior_state: SessionRecord,
        state: SessionRecord,
        event: EventRecordUnion,
        review: ReviewRecord | None = None,
    ) -> None:
        """Durably record an incomplete submission; caller owns the attempt lock."""
        recovery = SubmissionRecovery.for_submission(prior_state, state, event, review)
        self._atomic_json(
            attempt_directory / SUBMISSION_RECOVERY_FILENAME, recovery.to_dict()
        )

    def recover_submission_locked(
        self, attempt_directory: Path
    ) -> SessionRecord | None:
        """Finish a write-ahead submission without ever rerunning its scorer."""
        recovery = self._read_submission_recovery_locked(attempt_directory)
        if recovery is None:
            return None
        current = self.read_session(attempt_directory)
        events, tail = self._read_events(attempt_directory)
        if current not in (recovery.prior_state, recovery.state):
            raise SessionCorruptError(
                f"submission recovery state does not match: {attempt_directory}"
            )
        self._validate_event_attempts(attempt_directory, events, recovery.state)
        # The review is published first: a submitted state never exists without
        # the immutable bytes it identifies.
        self._publish_review_locked(attempt_directory, recovery.review)
        expected = recovery.event
        has_expected_event = self._validate_submission_event_at_expected_revision(
            attempt_directory, events, expected
        )
        if current == recovery.prior_state:
            self.write_session_locked(attempt_directory, recovery.state)
        if has_expected_event:
            # A prior process may have died after append or after an uncertain fsync.
            # Replacing canonical complete records confirms a safe append boundary.
            self._write_events_locked(attempt_directory, events)
        else:
            if tail != "complete":
                self._write_events_locked(attempt_directory, [*events, expected])
            else:
                try:
                    self.append_event_locked(attempt_directory, expected)
                except SessionUnavailableError:
                    # An append may have reached the kernel before its flush reported
                    # failure. Rebuild the known complete log rather than retrying an
                    # unknown tail or accepting an unflushed event.
                    events, _tail = self._read_events(attempt_directory)
                    self._validate_event_attempts(
                        attempt_directory, events, recovery.state
                    )
                    has_expected_event = (
                        self._validate_submission_event_at_expected_revision(
                            attempt_directory, events, expected
                        )
                    )
                    if not has_expected_event:
                        events = [*events, expected]
                    self._write_events_locked(attempt_directory, events)

        try:
            self.filesystem.unlink(attempt_directory / SUBMISSION_RECOVERY_FILENAME)
            self.filesystem.flush_directory(attempt_directory)
        except OSError as error:
            raise SessionUnavailableError(
                f"cannot complete submission recovery: {attempt_directory}"
            ) from error
        return recovery.state

    def _publish_review_locked(
        self, attempt_directory: Path, review: ReviewRecord | None
    ) -> None:
        """Write the review exactly once and never rewrite a published one."""
        if review is None:
            return
        expected = canonical_review_bytes(review)
        published = self._read_review_bytes(attempt_directory)
        if published is None:
            self._atomic_bytes(attempt_directory / REVIEW_FILENAME, expected)
            return
        if published == expected:
            return
        if self._published_review_matches(attempt_directory, review):
            # Same record, different byte layout: republishing would rewrite a
            # published member, and failing would strand a recoverable attempt.
            return
        raise SessionCorruptError(
            "published review does not match its submission: "
            f"{attempt_directory.name}"
        )

    def _published_review_matches(
        self, attempt_directory: Path, review: ReviewRecord
    ) -> bool:
        """Compare the published record itself; unreadable bytes never match."""
        try:
            return self.read_review(attempt_directory) == review
        except SessionCorruptError:
            return False

    def read_review(self, attempt_directory: Path) -> ReviewRecord | None:
        """Read one bounded, validated review member without repairing anything."""
        raw = self._read_review_bytes(attempt_directory)
        if raw is None:
            return None
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise SessionCorruptError(
                f"cannot read valid review: {attempt_directory.name}"
            ) from error
        try:
            return parse_review_record(decoded)
        except SessionCorruptError:
            raise
        except Exception as error:
            raise SessionCorruptError(
                f"cannot read valid review: {attempt_directory.name}"
            ) from error

    def _read_review_bytes(self, attempt_directory: Path) -> bytes | None:
        path = attempt_directory / REVIEW_FILENAME
        identity = attempt_directory.name
        if path.is_symlink():
            raise SessionCorruptError(f"review is unsafe: {identity}")
        if not path.exists():
            return None
        if not path.is_file():
            raise SessionCorruptError(f"review is invalid: {identity}")
        try:
            raw = self.filesystem.read_bytes_limited(path, MAX_REVIEW_BYTES)
        except OSError as error:
            raise SessionUnavailableError(f"cannot read review: {identity}") from error
        if len(raw) > MAX_REVIEW_BYTES:
            raise SessionCorruptError("review exceeds the supported size limit")
        return raw

    def recover_missing_state_event(
        self, attempt_directory: Path, clock: Clock
    ) -> EventRecordUnion | None:
        """Append a recovery event if authoritative state lacks its revision event."""
        with self.attempt_lock(attempt_directory):
            state = self.read_session(attempt_directory)
            return self.recover_missing_state_event_locked(
                attempt_directory, state, clock
            )

    def recover_missing_state_event_locked(
        self, attempt_directory: Path, state: SessionRecord, clock: Clock
    ) -> EventRecordUnion | None:
        """Recover a missing state event while the caller owns the attempt lock."""
        self._reject_unsupported_session_schema(state.schema_version)
        events, tail = self._read_events(attempt_directory)
        self._validate_event_attempts(attempt_directory, events, state)
        if any(event.revision == state.revision for event in events):
            return None
        if state.status == "submitted":
            return None
        event = session_event(
            state,
            event_id=str(uuid4()),
            occurred_at=clock.now(),
            name="recovered",
            outcome="recovered",
            arguments={"reason": "missing_state_revision"},
        )
        if tail != "complete":
            self._write_events_locked(attempt_directory, [*events, event])
        else:
            self.append_event_locked(attempt_directory, event)
        return event

    def _read_submission_recovery_locked(
        self, attempt_directory: Path
    ) -> SubmissionRecovery | None:
        path = attempt_directory / SUBMISSION_RECOVERY_FILENAME
        if path.is_symlink():
            raise SessionCorruptError(f"submission recovery is unsafe: {path}")
        if not path.exists():
            return None
        if not path.is_file():
            raise SessionCorruptError(f"submission recovery is invalid: {path}")
        return self._read_model(
            path, SubmissionRecovery.from_dict, "submission recovery"
        )

    def _write_events_locked(
        self, attempt_directory: Path, events: list[EventRecordUnion]
    ) -> None:
        for event in events:
            self._reject_unsupported_event_schema(event.schema_version)
        self._atomic_bytes(
            attempt_directory / EVENTS_FILENAME,
            b"".join(_json_bytes(event.to_dict()) for event in events),
        )

    @staticmethod
    def _validate_event_attempts(
        attempt_directory: Path, events: list[EventRecordUnion], state: SessionRecord
    ) -> None:
        if any(event.attempt_id != state.attempt_id for event in events):
            raise SessionCorruptError(
                f"events belong to a different attempt: {attempt_directory}"
            )

    @staticmethod
    def _validate_submission_event_at_expected_revision(
        attempt_directory: Path,
        events: list[EventRecordUnion],
        expected: EventRecordUnion,
    ) -> bool:
        events_at_expected_revision = [
            event for event in events if event.revision == expected.revision
        ]
        if not events_at_expected_revision:
            return False
        if events_at_expected_revision == [expected]:
            return True
        raise SessionCorruptError(
            "submission recovery expected revision has an unexpected event: "
            f"{attempt_directory}"
        )

    def read_active_pointer(self, attempts_directory: Path) -> ActivePointer | None:
        """Read the versioned selection pointer, returning ``None`` when absent."""
        path = attempts_directory / ACTIVE_FILENAME
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise SessionCorruptError(f"active pointer is unsafe: {path}")
        if not path.exists():
            return None
        return self._read_model(path, ActivePointer.from_dict, "active pointer")

    def write_active_pointer(
        self, attempts_directory: Path, pointer: ActivePointer
    ) -> None:
        """Atomically publish a pointer while holding the workspace-root lock."""
        with self.workspace_lock(attempts_directory):
            self.write_active_pointer_locked(attempts_directory, pointer)

    def write_active_pointer_locked(
        self, attempts_directory: Path, pointer: ActivePointer
    ) -> None:
        """Atomically publish a pointer; the caller already owns its root lock."""
        self._atomic_json(attempts_directory / ACTIVE_FILENAME, pointer.to_dict())

    def atomic_json(self, path: Path, value: object) -> None:
        """Atomically write a JSON-safe value to a caller-owned path."""
        self._atomic_json(path, value)

    def _read_model(self, path: Path, parser, label: str, *, max_bytes: int | None = None):
        try:
            raw = (
                self.filesystem.read_bytes(path)
                if max_bytes is None
                else self.filesystem.read_bytes_limited(path, max_bytes)
            )
            if max_bytes is not None and len(raw) > max_bytes:
                raise SessionCorruptError(f"{label} exceeds the supported size limit")
            decoded = json.loads(raw.decode("utf-8"))
            return parser(decoded)
        except SessionCorruptError:
            raise
        except UnsupportedSchemaVersionError as error:
            raise SessionCorruptError(
                f"cannot read valid {label}: unsupported schema version"
            ) from error
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise SessionCorruptError(f"cannot read valid {label}: {path}") from error
        except Exception as error:
            raise SessionCorruptError(f"cannot read valid {label}: {path}") from error

    @staticmethod
    def _reject_unsupported_session_schema(schema_version: str) -> None:
        if schema_version not in _SUPPORTED_SESSION_SCHEMA_VERSIONS:
            raise UnsupportedSchemaVersionError(
                f"unsupported session schema version: {schema_version}"
            )

    @staticmethod
    def _reject_unsupported_event_schema(schema_version: str) -> None:
        if schema_version not in _SUPPORTED_EVENT_SCHEMA_VERSIONS:
            raise UnsupportedSchemaVersionError(
                f"unsupported event schema version: {schema_version}"
            )

    def _atomic_json(self, path: Path, value: object) -> None:
        self._atomic_bytes(path, _json_bytes(value))

    def _atomic_bytes(self, path: Path, data: bytes) -> None:
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            self.filesystem.write_bytes(temporary, data)
            self.filesystem.flush_file(temporary)
            self.filesystem.replace(temporary, path)
            self.filesystem.flush_directory(path.parent)
        except OSError:
            self._remove_owned_file(temporary)
            raise

    def _remove_owned_file(self, path: Path) -> None:
        try:
            if path.exists() or path.is_symlink():
                self.filesystem.unlink(path)
        except OSError:
            pass


def initial_event(state: SessionRecord) -> EventRecordUnion:
    """Return the initial event paired with a newly created session revision."""
    return session_event(
        state,
        event_id=str(uuid4()),
        occurred_at=state.started_at,
        name="started",
        outcome="succeeded",
        arguments={},
    )


__all__ = [
    "ACTIVE_FILENAME",
    "ATTEMPT_LOCK_FILENAME",
    "EVENTS_FILENAME",
    "REVIEW_FILENAME",
    "SESSION_FILENAME",
    "SUBMISSION_RECOVERY_FILENAME",
    "WORKSPACE_LOCK_FILENAME",
    "Persistence",
    "initial_event",
]
