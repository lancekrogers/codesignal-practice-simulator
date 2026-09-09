"""Atomic state, event-log, pointer, and advisory-lock primitives."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from .clock import Clock
from .errors import LockUnavailableError, SessionCorruptError, SessionUnavailableError
from .filesystem import Filesystem, LocalFilesystem
from .models import ActivePointer, EventRecord, SessionState

try:  # The supported local runtime is POSIX; keep the import failure explicit.
    import fcntl
except ImportError:  # pragma: no cover - exercised only on unsupported platforms.
    fcntl = None  # type: ignore[assignment]


SESSION_FILENAME = "session.json"
EVENTS_FILENAME = "events.jsonl"
ACTIVE_FILENAME = "active.json"
ATTEMPT_LOCK_FILENAME = ".session.lock"
WORKSPACE_LOCK_FILENAME = ".workspace.lock"

_PROCESS_LOCK = threading.Lock()
_HELD_LOCKS: set[Path] = set()


def _json_bytes(value: object, *, newline: bool = True) -> bytes:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (text + ("\n" if newline else "")).encode("utf-8")


class Persistence:
    """Own all durable state formats and their atomic filesystem discipline."""

    def __init__(self, filesystem: Filesystem | None = None) -> None:
        self.filesystem = filesystem or LocalFilesystem()

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

    def read_session(self, attempt_directory: Path) -> SessionState:
        """Read and schema-validate authoritative session state."""
        return self._read_model(
            attempt_directory / SESSION_FILENAME, SessionState.from_dict, "session"
        )

    def write_session(self, attempt_directory: Path, state: SessionState) -> None:
        """Atomically replace session state while holding the attempt lock."""
        with self.attempt_lock(attempt_directory):
            self.write_session_locked(attempt_directory, state)

    def write_session_locked(self, attempt_directory: Path, state: SessionState) -> None:
        """Atomically replace session state; the caller already owns its lock."""
        self._atomic_json(attempt_directory / SESSION_FILENAME, state.to_dict())

    def read_events(self, attempt_directory: Path) -> list[EventRecord]:
        """Read strict JSONL, tolerating one syntactically incomplete final tail."""
        path = attempt_directory / EVENTS_FILENAME
        try:
            raw = self.filesystem.read_bytes(path)
        except OSError as error:
            raise SessionUnavailableError(f"cannot read events: {path}") from error
        if not raw:
            return []

        records: list[EventRecord] = []
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
                    break
                raise SessionCorruptError(f"events contain malformed JSONL: {path}") from error
            try:
                event = EventRecord.from_dict(decoded)
            except Exception as error:
                raise SessionCorruptError(f"events contain an invalid record: {path}") from error
            records.append(event)
        return records

    def append_event(self, attempt_directory: Path, event: EventRecord) -> None:
        """Append one flushed, complete event record while holding the attempt lock."""
        with self.attempt_lock(attempt_directory):
            self.append_event_locked(attempt_directory, event)

    def append_event_locked(self, attempt_directory: Path, event: EventRecord) -> None:
        """Append one event; the caller already owns its lock."""
        path = attempt_directory / EVENTS_FILENAME
        try:
            self.filesystem.append_bytes(path, _json_bytes(event.to_dict()))
            self.filesystem.flush_file(path)
        except OSError as error:
            raise SessionUnavailableError(f"cannot append event: {path}") from error

    def recover_missing_state_event(
        self, attempt_directory: Path, clock: Clock
    ) -> EventRecord | None:
        """Append a recovery event if authoritative state lacks its revision event."""
        with self.attempt_lock(attempt_directory):
            state = self.read_session(attempt_directory)
            return self.recover_missing_state_event_locked(
                attempt_directory, state, clock
            )

    def recover_missing_state_event_locked(
        self, attempt_directory: Path, state: SessionState, clock: Clock
    ) -> EventRecord | None:
        """Recover a missing state event while the caller owns the attempt lock."""
        events = self.read_events(attempt_directory)
        if any(event.attempt_id != state.attempt_id for event in events):
            raise SessionCorruptError(
                f"events belong to a different attempt: {attempt_directory}"
            )
        if any(event.revision == state.revision for event in events):
            return None
        event = EventRecord(
            schema_version="event/v1",
            event_id=str(uuid4()),
            attempt_id=state.attempt_id,
            revision=state.revision,
            occurred_at=clock.now(),
            name="recovered",
            outcome="recovered",
            arguments={"reason": "missing_state_revision"},
        )
        self.append_event_locked(attempt_directory, event)
        return event

    def read_active_pointer(self, attempts_directory: Path) -> ActivePointer | None:
        """Read the versioned selection pointer, returning ``None`` when absent."""
        path = attempts_directory / ACTIVE_FILENAME
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

    def _read_model(self, path: Path, parser, label: str):
        try:
            decoded = json.loads(self.filesystem.read_bytes(path).decode("utf-8"))
            return parser(decoded)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise SessionCorruptError(f"cannot read valid {label}: {path}") from error
        except Exception as error:
            raise SessionCorruptError(f"cannot read valid {label}: {path}") from error

    def _atomic_json(self, path: Path, value: object) -> None:
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            self.filesystem.write_bytes(temporary, _json_bytes(value))
            self.filesystem.flush_file(temporary)
            self.filesystem.replace(temporary, path)
        except OSError:
            self._remove_owned_file(temporary)
            raise

    def _remove_owned_file(self, path: Path) -> None:
        try:
            if path.exists() or path.is_symlink():
                self.filesystem.unlink(path)
        except OSError:
            pass


def initial_event(state: SessionState) -> EventRecord:
    """Return the initial event paired with a newly created session revision."""
    return EventRecord(
        schema_version="event/v1",
        event_id=str(uuid4()),
        attempt_id=state.attempt_id,
        revision=state.revision,
        occurred_at=state.started_at,
        name="started",
        outcome="succeeded",
        arguments={},
    )


__all__ = [
    "ACTIVE_FILENAME",
    "ATTEMPT_LOCK_FILENAME",
    "EVENTS_FILENAME",
    "SESSION_FILENAME",
    "WORKSPACE_LOCK_FILENAME",
    "Persistence",
    "initial_event",
]
