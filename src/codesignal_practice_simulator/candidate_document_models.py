"""Validated, JSON-safe models for candidate source documents."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from collections.abc import Mapping
from typing import Final
from uuid import UUID

from .errors import DomainError, ExitCode, IllegalLifecycleError


DOCUMENT_SCHEMA_VERSION: Final = "candidate-document/v1"
SNAPSHOT_SCHEMA_VERSION: Final = "candidate-snapshot/v2"
INITIAL_SOURCE_SCHEMA_VERSION: Final = "candidate-initial/v1"
HISTORY_ORDER_SCHEMA_VERSION: Final = "candidate-history-order/v1"
HISTORY_ORDER_FILENAME: Final = ".candidate-history-order.json"
MAX_DOCUMENT_BYTES: Final = 256 * 1024
HISTORY_LIMIT: Final = 50
INITIAL_SOURCE_FILENAME: Final = ".candidate-initial.json"
HISTORY_DIRECTORY: Final = ".candidate-history"
_ETAG = re.compile(r"sha256:[0-9a-f]{64}\Z")
_SNAPSHOT_OPERATIONS = frozenset(("save", "restore", "reset"))


class CandidateDocumentError(DomainError):
    """Base class for safe candidate-document failures."""

    exit_code = ExitCode.INVALID_INPUT


class CandidateDocumentConflictError(CandidateDocumentError):
    """The supplied ETag is no longer the current document version."""

    def __init__(self, current: CandidateDocument) -> None:
        self.current = current
        self.document = current
        self.current_etag = current.etag
        super().__init__("candidate source changed; reload before saving")


class UnsafeCandidateDocumentError(CandidateDocumentError):
    """The registered candidate source or its metadata is unsafe."""


class CandidateDocumentTooLargeError(CandidateDocumentError):
    """Candidate source content exceeds the byte limit."""


class InvalidCandidateEncodingError(CandidateDocumentError):
    """Candidate source content is not strict UTF-8 text."""


class CandidateDocumentReadOnlyError(IllegalLifecycleError):
    """A source mutation was attempted after expiry or submission."""


class CandidateDocumentUnavailableError(CandidateDocumentError):
    """The registered candidate source or requested history is missing."""

    exit_code = ExitCode.SESSION_UNAVAILABLE


class CandidateDocumentCorruptError(CandidateDocumentError):
    """Candidate metadata or history does not satisfy its schema."""

    exit_code = ExitCode.SESSION_UNAVAILABLE


CandidateConflictError = CandidateDocumentConflictError
CandidateDocumentConflict = CandidateDocumentConflictError
UnsafeDocumentError = UnsafeCandidateDocumentError
UnsafeCandidateDocument = UnsafeCandidateDocumentError
OversizedDocumentError = CandidateDocumentTooLargeError
ContentTooLargeError = CandidateDocumentTooLargeError
InvalidUTF8Error = InvalidCandidateEncodingError
ReadOnlyAttemptError = CandidateDocumentReadOnlyError


def validate_content(content: object) -> str:
    """Validate a candidate document as strict, UTF-8 encodable text."""
    if not isinstance(content, str):
        raise InvalidCandidateEncodingError("candidate source must be a string")
    try:
        raw = content.encode("utf-8")
    except UnicodeEncodeError as error:
        raise InvalidCandidateEncodingError("candidate source must be valid UTF-8") from error
    if len(raw) > MAX_DOCUMENT_BYTES:
        raise CandidateDocumentTooLargeError(
            f"candidate source exceeds {MAX_DOCUMENT_BYTES} bytes"
        )
    return content


def _require_content(value: object) -> str:
    try:
        return validate_content(value)
    except CandidateDocumentError as error:
        raise CandidateDocumentCorruptError("candidate content is invalid") from error


def etag_for(content: str) -> str:
    """Return the canonical content ETag for text."""
    raw = validate_content(content).encode("utf-8")
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def is_canonical_etag(value: object) -> bool:
    return isinstance(value, str) and _ETAG.fullmatch(value) is not None


def is_canonical_uuid(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return str(UUID(value)) == value
    except (TypeError, ValueError, AttributeError):
        return False


def _require_string(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise CandidateDocumentCorruptError(f"{label} is invalid")
    return value


def _require_uuid(value: object, label: str) -> str:
    if not is_canonical_uuid(value):
        raise CandidateDocumentCorruptError(f"{label} is invalid")
    return value  # type: ignore[return-value]


def _require_etag(value: object, label: str) -> str:
    if not is_canonical_etag(value):
        raise CandidateDocumentCorruptError(f"{label} is invalid")
    return value  # type: ignore[return-value]


def _require_positive_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise CandidateDocumentCorruptError(f"{label} is invalid")
    return value


def _require_filename(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value in (".", "..")
        or "/" in value
        or "\\" in value
    ):
        raise CandidateDocumentCorruptError("candidate filename is invalid")
    return value


def _timestamp(value: object, label: str) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise CandidateDocumentCorruptError(f"{label} is invalid")
    if value.utcoffset() != timedelta(0):
        raise CandidateDocumentCorruptError(f"{label} is invalid")
    return value.astimezone(timezone.utc).isoformat()


def _parse_timestamp(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        raise CandidateDocumentCorruptError(f"{label} is invalid")
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as error:
        raise CandidateDocumentCorruptError(f"{label} is invalid") from error
    if timestamp.tzinfo is None or timestamp.utcoffset() != timedelta(0):
        raise CandidateDocumentCorruptError(f"{label} is invalid")
    return timestamp.astimezone(timezone.utc)


def _require_object(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise CandidateDocumentCorruptError(f"{label} is invalid")
    return value


def _require_keys(value: Mapping[str, object], expected: frozenset[str], label: str) -> None:
    if set(value) != expected:
        raise CandidateDocumentCorruptError(f"{label} is invalid")


@dataclass(frozen=True, slots=True)
class CandidateDocument:
    """The current candidate source and its content-addressed revision."""

    attempt_id: str
    filename: str
    content: str
    revision: str
    etag: str

    def __post_init__(self) -> None:
        _require_uuid(self.attempt_id, "attempt ID")
        _require_filename(self.filename)
        validate_content(self.content)
        expected = etag_for(self.content)
        if not is_canonical_etag(self.etag) or self.etag != expected:
            raise CandidateDocumentCorruptError("candidate ETag does not match content")
        if self.revision != self.etag:
            raise CandidateDocumentCorruptError("candidate revision is invalid")

    @property
    def sha256(self) -> str:
        return self.etag.removeprefix("sha256:")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": DOCUMENT_SCHEMA_VERSION,
            "attempt_id": self.attempt_id,
            "filename": self.filename,
            "content": self.content,
            "revision": self.revision,
            "etag": self.etag,
        }

    @classmethod
    def from_dict(cls, value: object) -> CandidateDocument:
        data = _require_object(value, "candidate document")
        _require_keys(
            data,
            frozenset(("schema_version", "attempt_id", "filename", "content", "revision", "etag")),
            "candidate document",
        )
        if data["schema_version"] != DOCUMENT_SCHEMA_VERSION:
            raise CandidateDocumentCorruptError("candidate document schema is invalid")
        return cls(
            attempt_id=_require_uuid(data["attempt_id"], "attempt ID"),
            filename=_require_filename(data["filename"]),
            content=_require_content(data["content"]),
            revision=_require_etag(data["revision"], "candidate revision"),
            etag=_require_etag(data["etag"], "candidate ETag"),
        )


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    """An immutable predecessor source snapshot."""

    snapshot_id: str
    attempt_id: str
    filename: str
    created_at: datetime
    operation: str
    prior_hash: str
    new_hash: str
    content: str
    operation_order: int = 1

    def __post_init__(self) -> None:
        _require_uuid(self.snapshot_id, "snapshot ID")
        _require_uuid(self.attempt_id, "attempt ID")
        _require_filename(self.filename)
        _timestamp(self.created_at, "history timestamp")
        if not isinstance(self.operation, str) or self.operation not in _SNAPSHOT_OPERATIONS:
            raise CandidateDocumentCorruptError("snapshot operation is invalid")
        _require_positive_integer(self.operation_order, "snapshot operation order")
        _require_etag(self.prior_hash, "snapshot prior hash")
        _require_etag(self.new_hash, "snapshot new hash")
        validate_content(self.content)
        if etag_for(self.content) != self.prior_hash:
            raise CandidateDocumentCorruptError("snapshot content does not match its hash")

    @property
    def etag(self) -> str:
        return self.prior_hash

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "snapshot_id": self.snapshot_id,
            "attempt_id": self.attempt_id,
            "filename": self.filename,
            "created_at": _timestamp(self.created_at, "history timestamp"),
            "operation": self.operation,
            "prior_hash": self.prior_hash,
            "new_hash": self.new_hash,
            "content": self.content,
            "operation_order": self.operation_order,
        }

    @classmethod
    def from_dict(cls, value: object) -> SourceSnapshot:
        data = _require_object(value, "snapshot")
        _require_keys(
            data,
            frozenset(
                (
                    "schema_version",
                    "snapshot_id",
                    "attempt_id",
                    "filename",
                    "created_at",
                    "operation",
                    "prior_hash",
                    "new_hash",
                    "content",
                    "operation_order",
                )
            ),
            "snapshot",
        )
        if data["schema_version"] != SNAPSHOT_SCHEMA_VERSION:
            raise CandidateDocumentCorruptError("snapshot schema is invalid")
        return cls(
            snapshot_id=_require_uuid(data["snapshot_id"], "snapshot ID"),
            attempt_id=_require_uuid(data["attempt_id"], "attempt ID"),
            filename=_require_filename(data["filename"]),
            created_at=_parse_timestamp(data["created_at"], "history timestamp"),
            operation=_require_string(data["operation"], "snapshot operation"),
            prior_hash=_require_etag(data["prior_hash"], "snapshot prior hash"),
            new_hash=_require_etag(data["new_hash"], "snapshot new hash"),
            content=_require_content(data["content"]),
            operation_order=_require_positive_integer(
                data["operation_order"], "snapshot operation order"
            ),
        )


@dataclass(frozen=True, slots=True)
class HistoryOrder:
    """The next durable operation order for one attempt."""

    next_order: int

    def __post_init__(self) -> None:
        _require_positive_integer(self.next_order, "history next order")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": HISTORY_ORDER_SCHEMA_VERSION,
            "next_order": self.next_order,
        }

    @classmethod
    def from_dict(cls, value: object) -> HistoryOrder:
        data = _require_object(value, "history order")
        _require_keys(data, frozenset(("schema_version", "next_order")), "history order")
        if data["schema_version"] != HISTORY_ORDER_SCHEMA_VERSION:
            raise CandidateDocumentCorruptError("history order schema is invalid")
        return cls(_require_positive_integer(data["next_order"], "history next order"))


@dataclass(frozen=True, slots=True)
class SourceHistory:
    """Current source plus bounded, newest-first predecessor snapshots."""

    current: CandidateDocument
    snapshots: tuple[SourceSnapshot, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.current, CandidateDocument):
            raise CandidateDocumentCorruptError("current candidate document is invalid")
        if (
            not isinstance(self.snapshots, tuple)
            or len(self.snapshots) > HISTORY_LIMIT
            or any(not isinstance(snapshot, SourceSnapshot) for snapshot in self.snapshots)
        ):
            raise CandidateDocumentCorruptError("candidate history is invalid")
        if any(
            snapshot.attempt_id != self.current.attempt_id
            or snapshot.filename != self.current.filename
            for snapshot in self.snapshots
        ):
            raise CandidateDocumentCorruptError("candidate history ownership is invalid")

    def __iter__(self):
        yield self.current
        yield from self.snapshots

    def __len__(self) -> int:
        return len(self.snapshots) + 1

    def __getitem__(self, index: int):
        return (self.current, *self.snapshots)[index]

    def to_dict(self) -> dict[str, object]:
        return {
            "current": self.current.to_dict(),
            "snapshots": [snapshot.to_dict() for snapshot in self.snapshots],
        }

    @classmethod
    def from_dict(cls, value: object) -> SourceHistory:
        data = _require_object(value, "candidate history")
        _require_keys(data, frozenset(("current", "snapshots")), "candidate history")
        snapshots = data["snapshots"]
        if not isinstance(snapshots, list):
            raise CandidateDocumentCorruptError("candidate history snapshots are invalid")
        return cls(
            CandidateDocument.from_dict(data["current"]),
            tuple(SourceSnapshot.from_dict(item) for item in snapshots),
        )

    @property
    def attempt_id(self) -> str:
        return self.current.attempt_id

    @property
    def predecessors(self) -> tuple[SourceSnapshot, ...]:
        return self.snapshots


__all__ = [
    "CandidateConflictError",
    "CandidateDocument",
    "CandidateDocumentConflict",
    "CandidateDocumentConflictError",
    "CandidateDocumentCorruptError",
    "CandidateDocumentError",
    "CandidateDocumentReadOnlyError",
    "CandidateDocumentTooLargeError",
    "CandidateDocumentUnavailableError",
    "ContentTooLargeError",
    "DOCUMENT_SCHEMA_VERSION",
    "HISTORY_DIRECTORY",
    "HISTORY_LIMIT",
    "HISTORY_ORDER_SCHEMA_VERSION",
    "HISTORY_ORDER_FILENAME",
    "HistoryOrder",
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
    "UnsafeCandidateDocument",
    "UnsafeCandidateDocumentError",
    "UnsafeDocumentError",
    "etag_for",
    "is_canonical_etag",
    "is_canonical_uuid",
    "validate_content",
]
