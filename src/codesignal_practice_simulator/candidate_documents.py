"""Locked, file-backed ownership of the candidate source document."""

from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Iterator
from uuid import uuid4

from .candidate_document_models import (
    CandidateConflictError, CandidateDocument, CandidateDocumentConflict,
    CandidateDocumentConflictError, CandidateDocumentCorruptError,
    CandidateDocumentError, CandidateDocumentReadOnlyError,
    CandidateDocumentTooLargeError, CandidateDocumentUnavailableError,
    ContentTooLargeError, DOCUMENT_SCHEMA_VERSION, HISTORY_DIRECTORY,
    HISTORY_LIMIT, HISTORY_ORDER_FILENAME, HistoryOrder, INITIAL_SOURCE_FILENAME,
    INITIAL_SOURCE_SCHEMA_VERSION, InvalidCandidateEncodingError,
    InvalidUTF8Error, MAX_DOCUMENT_BYTES, OversizedDocumentError,
    ReadOnlyAttemptError, SNAPSHOT_SCHEMA_VERSION, SourceHistory,
    SourceSnapshot, UnsafeCandidateDocument, UnsafeCandidateDocumentError,
    UnsafeDocumentError, etag_for, is_canonical_etag, is_canonical_uuid,
    validate_content,
)
from .clock import Clock, UTCClock
from .errors import SessionCorruptError, SessionUnavailableError
from .candidate_document_storage import (
    initial_record,
    parse_initial,
    read_source,
    safe_candidate_path,
    write_initial_source_baseline,
)

if TYPE_CHECKING:
    from .workspace import WorkspaceManager


class CandidateDocumentService:
    """The sole mutable owner of one attempt's registered candidate source."""

    _gates_guard = threading.Lock()
    _attempt_gates: dict[str, threading.Lock] = {}

    def __init__(self, workspace: WorkspaceManager, clock: Clock | None = None) -> None:
        self.workspace = workspace
        self.persistence = workspace.persistence
        self.clock = UTCClock() if clock is None else clock

    def read(self, attempt_id: str | None = None) -> CandidateDocument:
        with self._locked_attempt(attempt_id) as attempt:
            filename, source = self._source_locked(attempt)
            self._ensure_initial_locked(attempt, source, filename)
            return self._read_document_locked(attempt, source, filename)

    def save(
        self, attempt_id: str | None, content: str, if_match: str
    ) -> CandidateDocument:
        with self._locked_attempt(attempt_id) as attempt:
            filename, source = self._source_locked(attempt)
            self._require_mutable_locked(attempt)
            self._ensure_initial_locked(attempt, source, filename)
            current = self._read_document_locked(attempt, source, filename)
            self._require_match(current, if_match)
            return self._replace_locked(attempt, source, filename, current, content, "save")

    def list_history(self, attempt_id: str | None = None) -> SourceHistory:
        with self._locked_attempt(attempt_id) as attempt:
            filename, source = self._source_locked(attempt)
            self._ensure_initial_locked(attempt, source, filename)
            current = self._read_document_locked(attempt, source, filename)
            return SourceHistory(current, self._history_locked(attempt, current))

    def preview_history(
        self, attempt_id: str | None, snapshot_id: str
    ) -> SourceSnapshot:
        with self._locked_attempt(attempt_id) as attempt:
            filename, source = self._source_locked(attempt)
            self._ensure_initial_locked(attempt, source, filename)
            current = self._read_document_locked(attempt, source, filename)
            return self._snapshot_locked(attempt, current, snapshot_id)

    def restore(
        self, attempt_id: str | None, snapshot_id: str, if_match: str
    ) -> CandidateDocument:
        with self._locked_attempt(attempt_id) as attempt:
            filename, source = self._source_locked(attempt)
            self._require_mutable_locked(attempt)
            self._ensure_initial_locked(attempt, source, filename)
            current = self._read_document_locked(attempt, source, filename)
            self._require_match(current, if_match)
            snapshot = self._snapshot_locked(attempt, current, snapshot_id)
            return self._replace_locked(
                attempt, source, filename, current, snapshot.content, "restore"
            )

    def reset(self, attempt_id: str | None, if_match: str) -> CandidateDocument:
        with self._locked_attempt(attempt_id) as attempt:
            filename, source = self._source_locked(attempt)
            self._require_mutable_locked(attempt)
            baseline = self._ensure_initial_locked(attempt, source, filename)
            current = self._read_document_locked(attempt, source, filename)
            self._require_match(current, if_match)
            return self._replace_locked(
                attempt, source, filename, current, baseline, "reset"
            )

    @contextmanager
    def _locked_attempt(self, attempt_id: str | None) -> Iterator[Path]:
        key = f"{self.workspace.workspace_root}:{attempt_id or '<active>'}"
        with self._gates_guard:
            gate = self._attempt_gates.setdefault(key, threading.Lock())
        with gate:
            with self._selected_attempt(attempt_id) as attempt:
                yield attempt

    @contextmanager
    def _selected_attempt(self, attempt_id: str | None) -> Iterator[Path]:
        try:
            with self.workspace.selected_attempt(attempt_id) as attempt:
                yield attempt
        except SessionCorruptError as error:
            raise CandidateDocumentCorruptError(
                "candidate attempt metadata is corrupt"
            ) from error
        except SessionUnavailableError as error:
            raise CandidateDocumentUnavailableError(
                "candidate attempt is unavailable"
            ) from error

    def _source_locked(self, attempt: Path) -> tuple[str, Path]:
        state = self.persistence.read_session(attempt)
        definition = self.workspace.definition_for_persisted_session(state)
        if state.attempt_id != attempt.name:
            raise CandidateDocumentCorruptError("candidate attempt metadata is invalid")
        filename = definition.candidate_filename
        return filename, safe_candidate_path(attempt, filename)

    def _read_document_locked(
        self, attempt: Path, source: Path, filename: str
    ) -> CandidateDocument:
        content = read_source(self.workspace.filesystem, source)
        etag = etag_for(content)
        return CandidateDocument(attempt.name, filename, content, etag, etag)

    def _require_mutable_locked(self, attempt: Path) -> None:
        state = self.persistence.read_session(attempt)
        now = self._now()
        if state.status != "active" or now >= state.deadline_at:
            raise CandidateDocumentReadOnlyError(
                "candidate source is read-only after expiry or submission"
            )

    def _require_match(self, current: CandidateDocument, if_match: str) -> None:
        if not is_canonical_etag(if_match):
            raise CandidateDocumentError("If-Match must be a canonical candidate ETag")
        if if_match != current.etag:
            raise CandidateDocumentConflictError(current)

    def _replace_locked(
        self,
        attempt: Path,
        source: Path,
        filename: str,
        current: CandidateDocument,
        content: str,
        operation: str,
    ) -> CandidateDocument:
        validate_content(content)
        new_etag = etag_for(content)
        snapshot = SourceSnapshot(
            snapshot_id=str(uuid4()),
            attempt_id=current.attempt_id,
            filename=filename,
            created_at=self._now(),
            operation=operation,
            prior_hash=current.etag,
            new_hash=new_etag,
            content=current.content,
            operation_order=self._reserve_operation_order_locked(attempt, current),
        )
        snapshot_path = self._write_snapshot_locked(attempt, snapshot)
        try:
            self._atomic_replace_source(source, content)
        except CandidateDocumentUnavailableError:
            if not self._published_source_matches(source, new_etag):
                self._remove_snapshot_best_effort(attempt, snapshot_path)
            raise
        result = CandidateDocument(
            current.attempt_id, filename, content, new_etag, new_etag
        )
        self._prune_history_best_effort(attempt, result)
        return result

    def _write_snapshot_locked(self, attempt: Path, snapshot: SourceSnapshot) -> Path:
        history = attempt / HISTORY_DIRECTORY
        if history.is_symlink() or (history.exists() and not history.is_dir()):
            raise UnsafeCandidateDocumentError("candidate history is unsafe")
        if not history.exists():
            try:
                self.workspace.filesystem.mkdir(history)
                self.workspace.filesystem.flush_directory(attempt)
            except OSError as error:
                raise CandidateDocumentUnavailableError(
                    "candidate history could not be created"
                ) from error
        path = history / f"{snapshot.snapshot_id}.json"
        try:
            self.persistence.atomic_json(path, snapshot.to_dict())
        except OSError as error:
            self._remove_snapshot_best_effort(attempt, path)
            raise CandidateDocumentUnavailableError(
                "candidate history could not be saved"
            ) from error
        return path

    def _atomic_replace_source(self, source: Path, content: str) -> None:
        temporary = source.with_name(f".{source.name}.{uuid4().hex}.tmp")
        try:
            self.workspace.filesystem.write_bytes(temporary, content.encode("utf-8"))
            self.workspace.filesystem.flush_file(temporary)
            self.workspace.filesystem.replace(temporary, source)
            self.workspace.filesystem.flush_directory(source.parent)
        except OSError:
            try:
                if temporary.exists() or temporary.is_symlink():
                    self.workspace.filesystem.unlink(temporary)
            except OSError:
                pass
            raise CandidateDocumentUnavailableError(
                "candidate source could not be replaced"
            ) from None

    def _published_source_matches(self, source: Path, expected: str) -> bool:
        try:
            return not source.is_symlink() and source.is_file() and etag_for(
                self.workspace.filesystem.read_bytes(source).decode("utf-8")
            ) == expected
        except (OSError, UnicodeDecodeError, CandidateDocumentError):
            return False

    def _remove_snapshot_best_effort(self, attempt: Path, path: Path) -> None:
        try:
            self.workspace.filesystem.unlink(path)
            self.workspace.filesystem.flush_directory(attempt / HISTORY_DIRECTORY)
        except OSError:
            pass

    def _ensure_initial_locked(
        self, attempt: Path, source: Path, filename: str
    ) -> str:
        path = attempt / INITIAL_SOURCE_FILENAME
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise UnsafeCandidateDocumentError("initial candidate baseline is unsafe")
        if path.exists():
            try:
                value = json.loads(self.workspace.filesystem.read_bytes(path).decode("utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                raise CandidateDocumentCorruptError(
                    "initial candidate baseline is corrupt"
                ) from error
            return parse_initial(value, filename)
        content = read_source(self.workspace.filesystem, source)
        try:
            self.persistence.atomic_json(path, initial_record(content, filename))
        except OSError as error:
            raise CandidateDocumentUnavailableError(
                "initial candidate baseline could not be created"
            ) from error
        return content

    def _history_locked(
        self, attempt: Path, current: CandidateDocument
    ) -> tuple[SourceSnapshot, ...]:
        records = self._read_history_records_locked(attempt, current)
        self._read_history_order_locked(attempt, records)
        ordered = sorted(
            records,
            key=lambda item: item.operation_order,
            reverse=True,
        )
        snapshots: list[SourceSnapshot] = []
        next_hash = current.etag
        for snapshot in ordered:
            if snapshot.new_hash != next_hash:
                continue
            next_hash = snapshot.prior_hash
            if snapshot.prior_hash == snapshot.new_hash:
                continue
            snapshots.append(snapshot)
            if len(snapshots) == HISTORY_LIMIT:
                break
        return tuple(snapshots)

    def _reserve_operation_order_locked(
        self, attempt: Path, current: CandidateDocument
    ) -> int:
        records = self._read_history_records_locked(attempt, current)
        sequence = self._read_history_order_locked(attempt, records)
        order = sequence.next_order
        try:
            self.persistence.atomic_json(
                attempt / HISTORY_ORDER_FILENAME,
                HistoryOrder(order + 1).to_dict(),
            )
        except OSError as error:
            raise CandidateDocumentUnavailableError(
                "history order could not be advanced"
            ) from error
        return order

    def _read_history_order_locked(
        self, attempt: Path, records: list[SourceSnapshot]
    ) -> HistoryOrder:
        path = attempt / HISTORY_ORDER_FILENAME
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise UnsafeCandidateDocumentError("history order is unsafe")
        if not path.exists():
            sequence = HistoryOrder(
                max((s.operation_order for s in records), default=0) + 1
            )
            try:
                self.persistence.atomic_json(path, sequence.to_dict())
            except OSError as error:
                raise CandidateDocumentUnavailableError(
                    "history order could not be created"
                ) from error
            return sequence
        try:
            value = json.loads(self.workspace.filesystem.read_bytes(path).decode("utf-8"))
            sequence = HistoryOrder.from_dict(value)
        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            CandidateDocumentError,
        ) as error:
            raise CandidateDocumentCorruptError("history order is corrupt") from error
        maximum = max((s.operation_order for s in records), default=0)
        if sequence.next_order <= maximum:
            raise CandidateDocumentCorruptError("history order is stale")
        return sequence

    def _read_history_records_locked(
        self, attempt: Path, current: CandidateDocument
    ) -> list[SourceSnapshot]:
        history = attempt / HISTORY_DIRECTORY
        if history.is_symlink():
            raise UnsafeCandidateDocumentError("candidate history is unsafe")
        if not history.exists():
            return []
        if not history.is_dir():
            raise UnsafeCandidateDocumentError("candidate history is unsafe")
        try:
            entries = tuple(history.iterdir())
        except OSError as error:
            raise CandidateDocumentUnavailableError(
                "candidate history could not be listed"
            ) from error
        snapshots: list[SourceSnapshot] = []
        for path in entries:
            if path.suffix != ".json":
                continue
            if path.is_symlink() or not path.is_file():
                raise UnsafeCandidateDocumentError(
                    "candidate history contains an unsafe record"
                )
            if path.name.startswith("."):
                continue
            snapshot = self._read_snapshot(path)
            if (
                snapshot.attempt_id != current.attempt_id
                or snapshot.filename != current.filename
                or snapshot.snapshot_id != path.stem
            ):
                raise CandidateDocumentCorruptError("candidate history ownership is invalid")
            snapshots.append(snapshot)
        orders = [snapshot.operation_order for snapshot in snapshots]
        if len(orders) != len(set(orders)):
            raise CandidateDocumentCorruptError(
                "candidate history contains duplicate operation orders"
            )
        return snapshots

    def _snapshot_locked(
        self, attempt: Path, current: CandidateDocument, snapshot_id: str
    ) -> SourceSnapshot:
        if not is_canonical_uuid(snapshot_id):
            raise CandidateDocumentError("snapshot ID is invalid")
        valid = self._history_locked(attempt, current)
        for snapshot in valid:
            if snapshot.snapshot_id == snapshot_id:
                return snapshot
        history = attempt / HISTORY_DIRECTORY
        path = history / f"{snapshot_id}.json"
        if path.is_symlink():
            raise UnsafeCandidateDocumentError("candidate history record is unsafe")
        if path.exists() and not path.is_file():
            raise UnsafeCandidateDocumentError("candidate history record is unsafe")
        if path.exists():
            raise CandidateDocumentUnavailableError("snapshot is unavailable")
        raise CandidateDocumentUnavailableError("snapshot is missing")

    def _read_snapshot(self, path: Path) -> SourceSnapshot:
        try:
            value = json.loads(self.workspace.filesystem.read_bytes(path).decode("utf-8"))
            return SourceSnapshot.from_dict(value)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, CandidateDocumentError) as error:
            raise CandidateDocumentCorruptError("candidate history record is corrupt") from error

    def _prune_history_best_effort(
        self, attempt: Path, current: CandidateDocument
    ) -> None:
        try:
            history = attempt / HISTORY_DIRECTORY
            if history.is_symlink() or not history.is_dir():
                return
            valid = {snapshot.snapshot_id for snapshot in self._history_locked(attempt, current)}
            for path in history.iterdir():
                if (
                    path.suffix == ".json"
                    and path.is_file()
                    and not path.is_symlink()
                    and path.stem not in valid
                ):
                    self.workspace.filesystem.unlink(path)
            self.workspace.filesystem.flush_directory(history)
        except (OSError, CandidateDocumentError):
            return

    def _now(self) -> datetime:
        now = self.clock.now()
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise CandidateDocumentError("clock must return a UTC timestamp")
        if now.utcoffset() != timedelta(0):
            raise CandidateDocumentError("clock must return a UTC timestamp")
        return now.astimezone(timezone.utc)


__all__ = [
    "CandidateConflictError",
    "CandidateDocument",
    "CandidateDocumentConflict",
    "CandidateDocumentConflictError",
    "CandidateDocumentCorruptError",
    "CandidateDocumentError",
    "CandidateDocumentReadOnlyError",
    "CandidateDocumentService",
    "CandidateDocumentTooLargeError",
    "CandidateDocumentUnavailableError",
    "ContentTooLargeError",
    "DOCUMENT_SCHEMA_VERSION",
    "HISTORY_DIRECTORY",
    "HISTORY_LIMIT",
    "HISTORY_ORDER_FILENAME",
    "INITIAL_SOURCE_FILENAME",
    "INITIAL_SOURCE_SCHEMA_VERSION",
    "InvalidCandidateEncodingError",
    "InvalidUTF8Error",
    "MAX_DOCUMENT_BYTES",
    "OversizedDocumentError",
    "ReadOnlyAttemptError",
    "SNAPSHOT_SCHEMA_VERSION",
    "SourceHistory",
    "SourceSnapshot",
    "UnsafeCandidateDocumentError",
    "UnsafeCandidateDocument",
    "UnsafeDocumentError",
    "etag_for",
    "is_canonical_etag",
    "is_canonical_uuid",
    "validate_content",
    "write_initial_source_baseline",
]
