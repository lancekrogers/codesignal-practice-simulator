"""Bounded, read-only metadata listing of stored attempts (D004).

This module is the history read boundary. It streams the attempts directory,
reads only each attempt's bounded ``session.json`` and the pending-marker
directory entries, and never opens source, review bytes, prompts or event
logs. It takes no lifecycle lock, never repairs a journal or marker, never
touches ``active.json`` and never consults the assessment registry. Pending
restarts and finalizations are reported, not completed.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import heapq
import json
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import UUID

from .clock import Clock, UTCClock
from .errors import InvalidInputError, SessionCorruptError, SessionUnavailableError
from .filesystem import Filesystem, LocalFilesystem
from .models import (
    ABANDONED,
    ACTIVE,
    CONTENT_IDENTITY_PINNED,
    CONTENT_IDENTITY_UNAVAILABLE,
    EXPIRED,
    SUBMITTED,
    ModeProfile,
    PinnedAssessment,
    ScoreSummary,
    adapt_session_record,
)
from .persistence import (
    RECOVERY_MARKER_FILENAMES,
    RESTART_JOURNAL_DIRECTORY,
    REVIEW_FILENAME,
    SESSION_FILENAME,
    Persistence,
)


DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100
HISTORY_CURSOR_SCHEMA_VERSION = "history-cursor/v1"

# Row-level safe issue codes.
RECORD_UNAVAILABLE = "record_unavailable"
RECORD_CORRUPT = "record_corrupt"
RESTART_PENDING = "restart_pending"
FINALIZATION_PENDING = "finalization_pending"
CONTENT_IDENTITY_UNAVAILABLE_ISSUE = "content_identity_unavailable"

# Aggregate warning codes.
UNSAFE_ENTRIES_SKIPPED = "unsafe_entries_skipped"
UNAVAILABLE_RECORDS_EXCLUDED_BY_FILTER = "unavailable_records_excluded_by_filter"
RESTART_JOURNALS_UNREADABLE = "restart_journals_unreadable"

_STATUSES = frozenset((ACTIVE, EXPIRED, SUBMITTED, ABANDONED))
_IDENTIFIER = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
_FILTER_KEYS = frozenset(("assessment_id", "status"))
_EPOCH = datetime.min.replace(tzinfo=timezone.utc)


def _canonical_uuid(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise InvalidInputError(f"{label} must be a canonical UUID")
    try:
        parsed = UUID(value)
    except ValueError as error:
        raise InvalidInputError(f"{label} must be a canonical UUID") from error
    if str(parsed) != value:
        raise InvalidInputError(f"{label} must be a canonical UUID")
    return value


@dataclass(frozen=True, slots=True)
class HistoryFilters:
    """Validated listing filters; unknown filters are rejected, not ignored."""

    assessment_id: str | None = None
    status: str | None = None

    def __post_init__(self) -> None:
        if self.assessment_id is not None and (
            not isinstance(self.assessment_id, str)
            or not _IDENTIFIER.fullmatch(self.assessment_id)
        ):
            raise InvalidInputError("assessment_id filter must be a lowercase identifier")
        if self.status is not None and self.status not in _STATUSES:
            raise InvalidInputError("status filter is not a known attempt status")

    @classmethod
    def from_mapping(cls, values: Mapping[str, object] | None) -> HistoryFilters:
        if values is None:
            return cls()
        unknown = set(values) - _FILTER_KEYS
        if unknown:
            raise InvalidInputError(
                "unknown history filter: " + ", ".join(sorted(map(str, unknown)))
            )
        return cls(
            assessment_id=values.get("assessment_id"),  # type: ignore[arg-type]
            status=values.get("status"),  # type: ignore[arg-type]
        )

    @property
    def active(self) -> bool:
        return self.assessment_id is not None or self.status is not None

    def to_dict(self) -> dict[str, object]:
        return {"assessment_id": self.assessment_id, "status": self.status}

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class HistoryCursor:
    """An ordering boundary bound to the filters it was issued for."""

    started_at: datetime | None
    attempt_id: str
    filters_fingerprint: str

    def encode(self) -> str:
        document = {
            "schema_version": HISTORY_CURSOR_SCHEMA_VERSION,
            "started_at": None if self.started_at is None else self.started_at.isoformat(),
            "attempt_id": self.attempt_id,
            "filters": self.filters_fingerprint,
        }
        raw = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    @classmethod
    def decode(cls, value: object, filters: HistoryFilters) -> HistoryCursor:
        invalid = InvalidInputError("history cursor is invalid")
        if not isinstance(value, str) or not value or len(value) > 512:
            raise invalid
        try:
            padded = value + "=" * (-len(value) % 4)
            document = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        except (ValueError, binascii.Error, UnicodeDecodeError):
            raise invalid from None
        if not isinstance(document, dict) or set(document) != {
            "schema_version",
            "started_at",
            "attempt_id",
            "filters",
        }:
            raise invalid
        if document["schema_version"] != HISTORY_CURSOR_SCHEMA_VERSION:
            raise invalid
        raw_started = document["started_at"]
        started_at: datetime | None = None
        if raw_started is not None:
            if not isinstance(raw_started, str):
                raise invalid
            try:
                started_at = datetime.fromisoformat(raw_started)
            except ValueError:
                raise invalid from None
            if started_at.tzinfo is None:
                raise invalid
            started_at = started_at.astimezone(timezone.utc)
        attempt_id = _canonical_uuid(document["attempt_id"], "cursor attempt ID")
        if document["filters"] != filters.fingerprint:
            raise InvalidInputError("history cursor does not match these filters")
        return cls(started_at, attempt_id, filters.fingerprint)


@dataclass(frozen=True, slots=True)
class HistoryAssessment:
    assessment_id: str
    display_name: str
    level_count: int
    content_identity: Literal["pinned", "unavailable"]
    content_version: str | None
    content_digest: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "assessment_id": self.assessment_id,
            "display_name": self.display_name,
            "level_count": self.level_count,
            "content_identity": self.content_identity,
            "content_version": self.content_version,
            "content_digest": self.content_digest,
        }


@dataclass(frozen=True, slots=True)
class HistoryItem:
    """One attempt's stored metadata. Never source, paths or tokens."""

    attempt_id: str
    available: bool
    issues: tuple[str, ...]
    schema_version: str | None = None
    status: str | None = None
    persisted_status: str | None = None
    assessment: HistoryAssessment | None = None
    profile: ModeProfile | None = None
    started_at: datetime | None = None
    deadline_at: datetime | None = None
    submitted_at: datetime | None = None
    ended_at: datetime | None = None
    revision: int | None = None
    score: ScoreSummary | None = None
    practice_score: ScoreSummary | None = None
    review_available: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "attempt_id": self.attempt_id,
            "available": self.available,
            "issues": list(self.issues),
            "schema_version": self.schema_version,
            "status": self.status,
            "persisted_status": self.persisted_status,
            "assessment": None if self.assessment is None else self.assessment.to_dict(),
            "profile": None if self.profile is None else self.profile.to_dict(),
            "started_at": _iso(self.started_at),
            "deadline_at": _iso(self.deadline_at),
            "submitted_at": _iso(self.submitted_at),
            "ended_at": _iso(self.ended_at),
            "revision": self.revision,
            "score": None if self.score is None else _score_summary(self.score),
            "practice_score": (
                None if self.practice_score is None else _score_summary(self.practice_score)
            ),
            "review_available": self.review_available,
        }


@dataclass(frozen=True, slots=True)
class HistoryWarning:
    code: str
    count: int

    def to_dict(self) -> dict[str, object]:
        return {"code": self.code, "count": self.count}


@dataclass(frozen=True, slots=True)
class HistoryPage:
    """One bounded page. Records may move between pages; refresh, no snapshot."""

    items: tuple[HistoryItem, ...]
    next_cursor: str | None
    warnings: tuple[HistoryWarning, ...]
    filters: HistoryFilters
    limit: int

    def to_dict(self) -> dict[str, object]:
        return {
            "items": [item.to_dict() for item in self.items],
            "next_cursor": self.next_cursor,
            "warnings": [warning.to_dict() for warning in self.warnings],
            "filters": self.filters.to_dict(),
            "limit": self.limit,
        }


@dataclass(frozen=True, slots=True)
class _Candidate:
    key: tuple[datetime, str]
    item: HistoryItem


class AttemptHistoryService:
    """List stored attempts from metadata alone, bounded and without side effects."""

    def __init__(
        self,
        attempts_directory: Path,
        *,
        persistence: Persistence | None = None,
        filesystem: Filesystem | None = None,
        clock: Clock | None = None,
    ) -> None:
        if persistence is not None and filesystem is None:
            filesystem = persistence.filesystem
        if filesystem is None:
            filesystem = LocalFilesystem()
        if persistence is None:
            persistence = Persistence(filesystem)
        elif persistence.filesystem is not filesystem:
            raise InvalidInputError(
                "filesystem and persistence must use the same filesystem"
            )
        self.attempts_directory = attempts_directory
        self.persistence = persistence
        self.filesystem = filesystem
        self.clock = UTCClock() if clock is None else clock

    def list_attempts(
        self,
        *,
        filters: HistoryFilters | Mapping[str, object] | None = None,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> HistoryPage:
        """Return one page, newest first (creation time, then UUID descending)."""
        selected = (
            filters
            if isinstance(filters, HistoryFilters)
            else HistoryFilters.from_mapping(filters)
        )
        page_size = _page_size(limit)
        boundary = None if cursor is None else HistoryCursor.decode(cursor, selected)
        now = self._now()
        attempts = self.attempts_directory
        if attempts.is_symlink() or (attempts.exists() and not attempts.is_dir()):
            raise SessionCorruptError("attempts directory is unsafe")
        if not attempts.exists():
            return HistoryPage((), None, (), selected, page_size)

        counters: dict[str, int] = {}
        pending = self._pending_restart_attempts(attempts, counters)
        boundary_key = None if boundary is None else _key(boundary.started_at, boundary.attempt_id)

        def candidates() -> Iterator[_Candidate]:
            for entry in self._entries(attempts, counters):
                item = self._item(entry, now, pending)
                if not item.available and selected.active:
                    _count(counters, UNAVAILABLE_RECORDS_EXCLUDED_BY_FILTER)
                    continue
                if not _matches(item, selected):
                    continue
                key = _key(item.started_at, item.attempt_id)
                if boundary_key is not None and key >= boundary_key:
                    continue
                yield _Candidate(key, item)

        # nlargest keeps at most page_size + 1 candidates in memory: the page
        # plus one witness that another page exists.
        top = heapq.nlargest(page_size + 1, candidates(), key=lambda candidate: candidate.key)
        items = tuple(candidate.item for candidate in top[:page_size])
        next_cursor = None
        if len(top) > page_size:
            last = items[-1]
            next_cursor = HistoryCursor(last.started_at, last.attempt_id, selected.fingerprint).encode()
        warnings = tuple(
            HistoryWarning(code, count) for code, count in sorted(counters.items())
        )
        return HistoryPage(items, next_cursor, warnings, selected, page_size)

    def _entries(self, attempts: Path, counters: dict[str, int]) -> Iterator[Path]:
        try:
            children = attempts.iterdir()
        except OSError as error:
            raise SessionUnavailableError("cannot inspect attempts directory") from error
        for child in children:
            name = child.name
            if name.startswith("."):
                # Locks, staging, journals and markers are workspace machinery.
                continue
            if child.is_symlink():
                _count(counters, UNSAFE_ENTRIES_SKIPPED)
                continue
            if not child.is_dir():
                # active.json and any stray file are not attempts.
                continue
            try:
                _canonical_uuid(name, "attempt ID")
            except InvalidInputError:
                _count(counters, UNSAFE_ENTRIES_SKIPPED)
                continue
            yield child

    def _pending_restart_attempts(self, attempts: Path, counters: dict[str, int]) -> frozenset[str]:
        """Attempt IDs a durable-but-unfinished restart still owns; never recovered here."""
        journal_directory = attempts / RESTART_JOURNAL_DIRECTORY
        if not journal_directory.exists() and not journal_directory.is_symlink():
            return frozenset()
        try:
            journals = self.persistence.read_restart_journals(attempts)
        except SessionUnavailableError:
            # Unreadable intent: the listing cannot name the rows, so it says so.
            _count(counters, RESTART_JOURNALS_UNREADABLE)
            return frozenset()
        affected: set[str] = set()
        for journal in journals:
            affected.add(journal.old_prior_state.attempt_id)
            affected.add(journal.replacement_state.attempt_id)
        return frozenset(affected)

    def _item(self, attempt: Path, now: datetime, pending: frozenset[str]) -> HistoryItem:
        attempt_id = attempt.name
        issues: list[str] = []
        if attempt_id in pending:
            issues.append(RESTART_PENDING)
        if any(self._marker_present(attempt / marker) for marker in RECOVERY_MARKER_FILENAMES):
            issues.append(FINALIZATION_PENDING)
        session_path = attempt / SESSION_FILENAME
        if not session_path.exists() and not session_path.is_symlink():
            # A directory with no record at all is absent, not malformed.
            issues.append(RECORD_UNAVAILABLE)
            return HistoryItem(attempt_id, False, tuple(issues))
        try:
            state = self.persistence.read_session(attempt)
        except SessionCorruptError:
            issues.append(RECORD_CORRUPT)
            return HistoryItem(attempt_id, False, tuple(issues))
        except SessionUnavailableError:
            issues.append(RECORD_UNAVAILABLE)
            return HistoryItem(attempt_id, False, tuple(issues))
        if state.attempt_id != attempt_id:
            issues.append(RECORD_CORRUPT)
            return HistoryItem(attempt_id, False, tuple(issues))
        adapted = adapt_session_record(state)
        if not adapted.content_identity_available:
            issues.append(CONTENT_IDENTITY_UNAVAILABLE_ISSUE)
        pinned = isinstance(state.assessment, PinnedAssessment)
        effective = adapted.status
        if effective == ACTIVE and now >= adapted.deadline_at:
            # Presentation only: the persisted record is not touched here.
            effective = EXPIRED
        available = RESTART_PENDING not in issues and FINALIZATION_PENDING not in issues
        return HistoryItem(
            attempt_id=attempt_id,
            available=available,
            issues=tuple(issues),
            schema_version=adapted.schema_version,
            status=effective,
            persisted_status=adapted.status,
            assessment=HistoryAssessment(
                assessment_id=adapted.assessment_id,
                display_name=adapted.display_name,
                level_count=state.assessment.level_count,
                content_identity=(
                    CONTENT_IDENTITY_PINNED if pinned else CONTENT_IDENTITY_UNAVAILABLE
                ),
                content_version=adapted.content_version,
                content_digest=adapted.content_digest,
            ),
            profile=adapted.profile,
            started_at=adapted.started_at,
            deadline_at=adapted.deadline_at,
            submitted_at=adapted.submitted_at,
            ended_at=None if adapted.abandonment is None else adapted.abandonment.ended_at,
            revision=adapted.revision,
            score=adapted.score,
            practice_score=adapted.practice_score,
            review_available=self._review_present(attempt / REVIEW_FILENAME),
        )

    @staticmethod
    def _marker_present(path: Path) -> bool:
        return path.is_symlink() or path.exists()

    @staticmethod
    def _review_present(path: Path) -> bool:
        return not path.is_symlink() and path.is_file()

    def _now(self) -> datetime:
        now = self.clock.now()
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise InvalidInputError("clock must return a timezone-aware UTC timestamp")
        return now.astimezone(timezone.utc)


def _page_size(limit: object) -> int:
    if limit is None:
        return DEFAULT_PAGE_SIZE
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise InvalidInputError(f"limit must be an integer between 1 and {MAX_PAGE_SIZE}")
    if limit < 1 or limit > MAX_PAGE_SIZE:
        raise InvalidInputError(f"limit must be an integer between 1 and {MAX_PAGE_SIZE}")
    return limit


def _key(started_at: datetime | None, attempt_id: str) -> tuple[datetime, str]:
    # Records without a readable creation time sort after every dated record.
    return (_EPOCH if started_at is None else started_at, attempt_id)


def _matches(item: HistoryItem, filters: HistoryFilters) -> bool:
    if filters.assessment_id is not None and (
        item.assessment is None or item.assessment.assessment_id != filters.assessment_id
    ):
        return False
    if filters.status is not None and item.status != filters.status:
        return False
    return True


def _count(counters: dict[str, int], code: str) -> None:
    counters[code] = counters.get(code, 0) + 1


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _score_summary(score: ScoreSummary) -> dict[str, object]:
    return {
        "passed_levels": score.passed_levels,
        "highest_contiguous_level": score.highest_contiguous_level,
        "levels": [result.to_dict() for result in score.levels],
    }


__all__ = [
    "CONTENT_IDENTITY_UNAVAILABLE_ISSUE",
    "DEFAULT_PAGE_SIZE",
    "FINALIZATION_PENDING",
    "HISTORY_CURSOR_SCHEMA_VERSION",
    "MAX_PAGE_SIZE",
    "RECORD_CORRUPT",
    "RECORD_UNAVAILABLE",
    "RESTART_JOURNALS_UNREADABLE",
    "RESTART_PENDING",
    "UNAVAILABLE_RECORDS_EXCLUDED_BY_FILTER",
    "UNSAFE_ENTRIES_SKIPPED",
    "AttemptHistoryService",
    "HistoryAssessment",
    "HistoryCursor",
    "HistoryFilters",
    "HistoryItem",
    "HistoryPage",
    "HistoryWarning",
]
