"""Validated, immutable JSON models for the session runtime.

This module is the sole owner of durable session, event, and active-pointer
schemas. Persistence code reads and writes only these model dictionaries.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from types import MappingProxyType
from typing import Any, Literal, Mapping
from uuid import UUID

from .candidate_document_models import MAX_DOCUMENT_BYTES
from .errors import InvalidInputError, UnsupportedSchemaVersionError


SESSION_SCHEMA_VERSION = "session/v1"
SESSION_SCHEMA_VERSION_V2 = "session/v2"
EVENT_SCHEMA_VERSION = "event/v1"
EVENT_SCHEMA_VERSION_V2 = "event/v2"
REVIEW_SCHEMA_VERSION = "review/v1"
# One 256 KiB source plus metadata, with room for worst-case JSON escaping.
MAX_REVIEW_BYTES = 2 * 1024 * 1024
CONTENT_IDENTITY_PINNED = "pinned"
CONTENT_IDENTITY_UNAVAILABLE = "unavailable"
ACTIVE_POINTER_SCHEMA_VERSION = "active-pointer/v1"
SUBMISSION_RECOVERY_SCHEMA_VERSION = "submission-recovery/v1"
SUBMISSION_RECOVERY_SCHEMA_VERSION_V2 = "submission-recovery/v2"

FULL_MODE = "full"
DRILL_MODE = "drill"
FULL_PROFILE = "full-90m"
DRILL_PROFILE = "drill-30m"
FULL_DURATION_SECONDS = 90 * 60
DRILL_DEFAULT_DURATION_SECONDS = 30 * 60

ACTIVE = "active"
EXPIRED = "expired"
SUBMITTED = "submitted"
ABANDONED = "abandoned"

PASSED = "passed"
FAILED = "failed"
ERROR = "error"

_IDENTIFIER = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
_SLUG = re.compile(r"[a-z][a-z0-9-]{0,63}\Z")
_OUTCOMES = frozenset((PASSED, FAILED, ERROR))
_EVENT_OUTCOMES = frozenset(("succeeded", "rejected", "recovered"))
_CONTENT_IDENTITY = frozenset((CONTENT_IDENTITY_PINNED, CONTENT_IDENTITY_UNAVAILABLE))
_STATUSES = frozenset((ACTIVE, EXPIRED, SUBMITTED))
_STATUSES_V2 = frozenset((ACTIVE, EXPIRED, SUBMITTED, ABANDONED))
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def _invalid(message: str) -> None:
    raise InvalidInputError(message)


def _require_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        _invalid(f"{label} must be an object")
    if not all(isinstance(key, str) for key in value):
        _invalid(f"{label} keys must be strings")
    return value


def _require_keys(
    value: Mapping[str, object], expected: frozenset[str], label: str
) -> None:
    actual = set(value)
    missing = expected - actual
    unexpected = actual - expected
    if missing or unexpected:
        _invalid(f"{label} has an invalid field set")


def _require_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        _invalid(f"{label} must be a non-empty string")
    return value


def _require_identifier(value: object, label: str) -> str:
    identifier = _require_string(value, label)
    if not _IDENTIFIER.fullmatch(identifier):
        _invalid(f"{label} must be a lowercase identifier")
    return identifier


def _require_slug(value: object, label: str) -> str:
    slug = _require_string(value, label)
    if not _SLUG.fullmatch(slug):
        _invalid(f"{label} must be a lowercase slug")
    return slug


def _require_digest(value: object, label: str) -> str:
    digest = _require_string(value, label)
    if not _DIGEST.fullmatch(digest):
        _invalid(f"{label} must be a lowercase SHA-256 digest")
    return digest


def _require_schema_version(value: object, label: str) -> str:
    data = _require_mapping(value, label)
    if "schema_version" not in data:
        _invalid(f"{label} must include schema_version")
    return _require_string(data["schema_version"], "schema_version")


def _require_uuid(value: object, label: str) -> str:
    identifier = _require_string(value, label)
    try:
        parsed = UUID(identifier)
    except ValueError:
        _invalid(f"{label} must be a canonical UUID")
    if str(parsed) != identifier:
        _invalid(f"{label} must be a canonical UUID")
    return identifier


def _require_nonnegative_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _invalid(f"{label} must be a non-negative integer")
    return value


def _require_positive_integer(value: object, label: str) -> int:
    number = _require_nonnegative_integer(value, label)
    if number == 0:
        _invalid(f"{label} must be a positive integer")
    return number


def _require_utc_datetime(value: object, label: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        _invalid(f"{label} must be a timezone-aware UTC timestamp")
    if value.utcoffset() != timedelta(0):
        _invalid(f"{label} must be a UTC timestamp")
    return value.astimezone(timezone.utc)


def _parse_utc_timestamp(value: object, label: str) -> datetime:
    text = _require_string(value, label)
    if "T" not in text:
        _invalid(f"{label} must be an ISO-8601 timestamp")
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        timestamp = datetime.fromisoformat(text)
    except ValueError:
        _invalid(f"{label} must be an ISO-8601 timestamp")
    return _require_utc_datetime(timestamp, label)


def _timestamp(value: datetime, label: str) -> str:
    return _require_utc_datetime(value, label).isoformat()


def _freeze_json(value: object, label: str) -> object:
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            _invalid(f"{label} must contain only JSON values")
        return value
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            _invalid(f"{label} keys must be strings")
        return MappingProxyType(
            {key: _freeze_json(item, f"{label}.{key}") for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item, label) for item in value)
    _invalid(f"{label} must contain only JSON values")


def _thaw_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class AssessmentMetadata:
    """Stable metadata for a four-level registered assessment."""

    assessment_id: str
    display_name: str
    level_count: int = 4

    def __post_init__(self) -> None:
        _require_identifier(self.assessment_id, "assessment_id")
        _require_string(self.display_name, "display_name")
        if (
            isinstance(self.level_count, bool)
            or not isinstance(self.level_count, int)
            or self.level_count != 4
        ):
            _invalid("level_count must be 4")

    def to_dict(self) -> dict[str, object]:
        return {
            "assessment_id": self.assessment_id,
            "display_name": self.display_name,
            "level_count": self.level_count,
        }

    @classmethod
    def from_dict(cls, value: object) -> AssessmentMetadata:
        data = _require_mapping(value, "assessment")
        _require_keys(
            data,
            frozenset(("assessment_id", "display_name", "level_count")),
            "assessment",
        )
        return cls(
            assessment_id=_require_identifier(data["assessment_id"], "assessment_id"),
            display_name=_require_string(data["display_name"], "display_name"),
            level_count=_require_nonnegative_integer(data["level_count"], "level_count"),
        )


@dataclass(frozen=True, slots=True)
class ModeProfile:
    """The named session mode and its persisted effective duration."""

    mode: Literal["full", "drill"]
    profile_id: str
    duration_seconds: int

    def __post_init__(self) -> None:
        if self.mode not in (FULL_MODE, DRILL_MODE):
            _invalid("mode must be full or drill")
        _require_slug(self.profile_id, "profile_id")
        _require_positive_integer(self.duration_seconds, "duration_seconds")
        if self.mode == FULL_MODE and (
            self.profile_id != FULL_PROFILE
            or self.duration_seconds != FULL_DURATION_SECONDS
        ):
            _invalid("full mode requires the full-90m profile and 5400 seconds")
        if self.mode == DRILL_MODE and self.profile_id != DRILL_PROFILE:
            _invalid("drill mode requires the drill-30m profile")

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "profile_id": self.profile_id,
            "duration_seconds": self.duration_seconds,
        }

    @classmethod
    def from_dict(cls, value: object) -> ModeProfile:
        data = _require_mapping(value, "profile")
        _require_keys(
            data,
            frozenset(("mode", "profile_id", "duration_seconds")),
            "profile",
        )
        mode = _require_string(data["mode"], "mode")
        return cls(
            mode=mode,  # type: ignore[arg-type]
            profile_id=_require_string(data["profile_id"], "profile_id"),
            duration_seconds=_require_positive_integer(
                data["duration_seconds"], "duration_seconds"
            ),
        )


@dataclass(frozen=True, slots=True)
class LevelResult:
    """Outcome of one independently executed assessment level."""

    level: int
    outcome: Literal["passed", "failed", "error"]

    def __post_init__(self) -> None:
        _require_positive_integer(self.level, "level")
        if self.level not in (1, 2, 3, 4):
            _invalid("level must be between 1 and 4")
        if self.outcome not in _OUTCOMES:
            _invalid("level outcome is invalid")

    def to_dict(self) -> dict[str, object]:
        return {"level": self.level, "outcome": self.outcome}

    @classmethod
    def from_dict(cls, value: object) -> LevelResult:
        data = _require_mapping(value, "level result")
        _require_keys(data, frozenset(("level", "outcome")), "level result")
        outcome = _require_string(data["outcome"], "level outcome")
        return cls(
            level=_require_positive_integer(data["level"], "level"),
            outcome=outcome,  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class ScoreSummary:
    """A complete, internally consistent summary of all four level groups."""

    levels: tuple[LevelResult, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.levels, tuple) or len(self.levels) != 4:
            _invalid("score must contain exactly four level results")
        if any(not isinstance(result, LevelResult) for result in self.levels):
            _invalid("score level results are invalid")
        if tuple(result.level for result in self.levels) != (1, 2, 3, 4):
            _invalid("score levels must be ordered from 1 through 4")

    @property
    def passed_levels(self) -> int:
        return sum(result.outcome == PASSED for result in self.levels)

    @property
    def highest_contiguous_level(self) -> int:
        highest = 0
        for result in self.levels:
            if result.outcome != PASSED:
                break
            highest = result.level
        return highest

    def to_dict(self) -> dict[str, object]:
        return {
            "levels": [result.to_dict() for result in self.levels],
            "passed_levels": self.passed_levels,
            "highest_contiguous_level": self.highest_contiguous_level,
        }

    @classmethod
    def from_dict(cls, value: object) -> ScoreSummary:
        data = _require_mapping(value, "score")
        _require_keys(
            data,
            frozenset(("levels", "passed_levels", "highest_contiguous_level")),
            "score",
        )
        raw_levels = data["levels"]
        if not isinstance(raw_levels, list):
            _invalid("score levels must be an array")
        summary = cls(tuple(LevelResult.from_dict(item) for item in raw_levels))
        if _require_nonnegative_integer(data["passed_levels"], "passed_levels") != (
            summary.passed_levels
        ):
            _invalid("passed_levels does not match level results")
        if _require_nonnegative_integer(
            data["highest_contiguous_level"], "highest_contiguous_level"
        ) != summary.highest_contiguous_level:
            _invalid("highest_contiguous_level does not match level results")
        return summary


# Schema families (CP0002):
# - parse_session_record and parse_event_record dispatch v1 and v2 reads.
# - New attempts are session/v2 with a PinnedAssessment computed from verified
#   inputs at creation; their events are event/v2 (see session_event()).
# - Existing session/v1 attempts stay v1, keep event/v1 writes, and never gain a
#   fabricated content identity; use adapt_session_record() for shared reads.


@dataclass(frozen=True, slots=True)
class PinnedAssessment:
    """Assessment metadata pinned to one installed content version and digest."""

    assessment_id: str
    display_name: str
    content_version: str
    content_digest: str
    level_count: int = 4

    def __post_init__(self) -> None:
        _require_identifier(self.assessment_id, "assessment_id")
        _require_string(self.display_name, "display_name")
        _require_slug(self.content_version, "content_version")
        _require_digest(self.content_digest, "content_digest")
        if (
            isinstance(self.level_count, bool)
            or not isinstance(self.level_count, int)
            or self.level_count != 4
        ):
            _invalid("level_count must be 4")

    def to_dict(self) -> dict[str, object]:
        return {
            "assessment_id": self.assessment_id,
            "display_name": self.display_name,
            "level_count": self.level_count,
            "content_version": self.content_version,
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, value: object) -> PinnedAssessment:
        data = _require_mapping(value, "assessment")
        _require_keys(
            data,
            frozenset(
                (
                    "assessment_id",
                    "display_name",
                    "level_count",
                    "content_version",
                    "content_digest",
                )
            ),
            "assessment",
        )
        return cls(
            assessment_id=_require_identifier(data["assessment_id"], "assessment_id"),
            display_name=_require_string(data["display_name"], "display_name"),
            content_version=_require_slug(data["content_version"], "content_version"),
            content_digest=_require_digest(data["content_digest"], "content_digest"),
            level_count=_require_nonnegative_integer(data["level_count"], "level_count"),
        )


@dataclass(frozen=True, slots=True)
class AbandonmentMetadata:
    """Explicit terminal abandonment metadata with optional practice-only score."""

    ended_at: datetime
    reason: str
    practice_score: ScoreSummary | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "ended_at", _require_utc_datetime(self.ended_at, "ended_at")
        )
        _require_identifier(self.reason, "abandonment reason")
        if self.practice_score is not None and not isinstance(
            self.practice_score, ScoreSummary
        ):
            _invalid("practice_score is invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "ended_at": _timestamp(self.ended_at, "ended_at"),
            "reason": self.reason,
            "practice_score": (
                None
                if self.practice_score is None
                else self.practice_score.to_dict()
            ),
        }

    @classmethod
    def from_dict(cls, value: object) -> AbandonmentMetadata:
        data = _require_mapping(value, "abandonment")
        _require_keys(
            data,
            frozenset(("ended_at", "reason", "practice_score")),
            "abandonment",
        )
        raw_practice_score = data["practice_score"]
        return cls(
            ended_at=_parse_utc_timestamp(data["ended_at"], "ended_at"),
            reason=_require_identifier(data["reason"], "abandonment reason"),
            practice_score=(
                None
                if raw_practice_score is None
                else ScoreSummary.from_dict(raw_practice_score)
            ),
        )


@dataclass(frozen=True, slots=True)
class AdaptedSessionRecord:
    """In-memory normalization of v1 or v2 session records for shared read paths."""

    record: "SessionRecord"
    schema_version: str
    attempt_id: str
    assessment_id: str
    display_name: str
    profile: ModeProfile
    started_at: datetime
    deadline_at: datetime
    status: str
    revision: int
    score: ScoreSummary | None
    submitted_at: datetime | None
    content_version: str | None
    content_digest: str | None
    content_identity_available: bool
    abandonment: AbandonmentMetadata | None
    practice_score: ScoreSummary | None


@dataclass(frozen=True, slots=True)
class SessionStateV2:
    """The authoritative versioned lifecycle state for one v2 attempt."""

    schema_version: str
    attempt_id: str
    assessment: PinnedAssessment
    profile: ModeProfile
    started_at: datetime
    deadline_at: datetime
    status: Literal["active", "expired", "submitted", "abandoned"]
    revision: int
    score: ScoreSummary | None = None
    submitted_at: datetime | None = None
    abandonment: AbandonmentMetadata | None = None
    review_digest: str | None = None

    def __post_init__(self) -> None:
        if self.schema_version != SESSION_SCHEMA_VERSION_V2:
            _invalid("unsupported session schema version")
        _require_uuid(self.attempt_id, "attempt_id")
        if not isinstance(self.assessment, PinnedAssessment):
            _invalid("assessment is invalid")
        if not isinstance(self.profile, ModeProfile):
            _invalid("profile is invalid")
        started_at = _require_utc_datetime(self.started_at, "started_at")
        deadline_at = _require_utc_datetime(self.deadline_at, "deadline_at")
        if deadline_at <= started_at:
            _invalid("deadline_at must be after started_at")
        if deadline_at - started_at != timedelta(seconds=self.profile.duration_seconds):
            _invalid("deadline_at must match the effective profile duration")
        if self.status not in _STATUSES_V2:
            _invalid("session status is invalid")
        _require_nonnegative_integer(self.revision, "revision")
        if self.score is not None and not isinstance(self.score, ScoreSummary):
            _invalid("score is invalid")
        if self.abandonment is not None and not isinstance(
            self.abandonment, AbandonmentMetadata
        ):
            _invalid("abandonment is invalid")
        if self.status == SUBMITTED:
            if self.score is None or self.submitted_at is None:
                _invalid("submitted sessions require score and submitted_at")
            if self.abandonment is not None:
                _invalid("submitted sessions must not contain abandonment")
            submitted_at = _require_utc_datetime(self.submitted_at, "submitted_at")
            if submitted_at < started_at:
                _invalid("submitted_at must not precede started_at")
            # A submitted v2 state must identify the immutable review it published.
            _require_digest(self.review_digest, "review_digest")
        elif self.status == ABANDONED:
            if self.abandonment is None:
                _invalid("abandoned sessions require abandonment metadata")
            if self.submitted_at is not None or self.score is not None:
                _invalid("abandoned sessions must not contain submitted score")
            if self.abandonment.ended_at < started_at:
                _invalid("abandonment ended_at must not precede started_at")
        else:
            if self.submitted_at is not None:
                _invalid("only submitted sessions may contain submitted_at")
            if self.abandonment is not None:
                _invalid("only abandoned sessions may contain abandonment")
        if self.status != SUBMITTED and self.review_digest is not None:
            _invalid("only submitted sessions may contain review_digest")
        object.__setattr__(self, "started_at", started_at)
        object.__setattr__(self, "deadline_at", deadline_at)
        if self.submitted_at is not None:
            object.__setattr__(
                self,
                "submitted_at",
                _require_utc_datetime(self.submitted_at, "submitted_at"),
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "attempt_id": self.attempt_id,
            "assessment": self.assessment.to_dict(),
            "profile": self.profile.to_dict(),
            "started_at": _timestamp(self.started_at, "started_at"),
            "deadline_at": _timestamp(self.deadline_at, "deadline_at"),
            "status": self.status,
            "revision": self.revision,
            "score": None if self.score is None else self.score.to_dict(),
            "submitted_at": (
                None
                if self.submitted_at is None
                else _timestamp(self.submitted_at, "submitted_at")
            ),
            "abandonment": (
                None if self.abandonment is None else self.abandonment.to_dict()
            ),
            "review_digest": self.review_digest,
        }

    @classmethod
    def from_dict(cls, value: object) -> SessionStateV2:
        data = _require_mapping(value, "session")
        _require_keys(
            data,
            frozenset(
                (
                    "schema_version",
                    "attempt_id",
                    "assessment",
                    "profile",
                    "started_at",
                    "deadline_at",
                    "status",
                    "revision",
                    "score",
                    "submitted_at",
                    "abandonment",
                    "review_digest",
                )
            ),
            "session",
        )
        raw_score = data["score"]
        raw_submitted_at = data["submitted_at"]
        raw_abandonment = data["abandonment"]
        raw_review_digest = data["review_digest"]
        status = _require_string(data["status"], "status")
        if _require_string(data["schema_version"], "schema_version") != (
            SESSION_SCHEMA_VERSION_V2
        ):
            _invalid("unsupported session schema version")
        return cls(
            schema_version=SESSION_SCHEMA_VERSION_V2,
            attempt_id=_require_uuid(data["attempt_id"], "attempt_id"),
            assessment=PinnedAssessment.from_dict(data["assessment"]),
            profile=ModeProfile.from_dict(data["profile"]),
            started_at=_parse_utc_timestamp(data["started_at"], "started_at"),
            deadline_at=_parse_utc_timestamp(data["deadline_at"], "deadline_at"),
            status=status,  # type: ignore[arg-type]
            revision=_require_nonnegative_integer(data["revision"], "revision"),
            score=None if raw_score is None else ScoreSummary.from_dict(raw_score),
            submitted_at=(
                None
                if raw_submitted_at is None
                else _parse_utc_timestamp(raw_submitted_at, "submitted_at")
            ),
            abandonment=(
                None
                if raw_abandonment is None
                else AbandonmentMetadata.from_dict(raw_abandonment)
            ),
            review_digest=(
                None
                if raw_review_digest is None
                else _require_digest(raw_review_digest, "review_digest")
            ),
        )


@dataclass(frozen=True, slots=True)
class SessionState:
    """The authoritative versioned lifecycle state for one attempt."""

    schema_version: str
    attempt_id: str
    assessment: AssessmentMetadata
    profile: ModeProfile
    started_at: datetime
    deadline_at: datetime
    status: Literal["active", "expired", "submitted"]
    revision: int
    score: ScoreSummary | None = None
    submitted_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.schema_version != SESSION_SCHEMA_VERSION:
            _invalid("unsupported session schema version")
        _require_uuid(self.attempt_id, "attempt_id")
        if not isinstance(self.assessment, AssessmentMetadata):
            _invalid("assessment is invalid")
        if not isinstance(self.profile, ModeProfile):
            _invalid("profile is invalid")
        started_at = _require_utc_datetime(self.started_at, "started_at")
        deadline_at = _require_utc_datetime(self.deadline_at, "deadline_at")
        if deadline_at <= started_at:
            _invalid("deadline_at must be after started_at")
        if deadline_at - started_at != timedelta(seconds=self.profile.duration_seconds):
            _invalid("deadline_at must match the effective profile duration")
        if self.status not in _STATUSES:
            _invalid("session status is invalid")
        _require_nonnegative_integer(self.revision, "revision")
        if self.score is not None and not isinstance(self.score, ScoreSummary):
            _invalid("score is invalid")
        if self.status == SUBMITTED:
            if self.score is None or self.submitted_at is None:
                _invalid("submitted sessions require score and submitted_at")
            submitted_at = _require_utc_datetime(self.submitted_at, "submitted_at")
            if submitted_at < started_at:
                _invalid("submitted_at must not precede started_at")
        elif self.submitted_at is not None:
            _invalid("only submitted sessions may contain submitted_at")
        object.__setattr__(self, "started_at", started_at)
        object.__setattr__(self, "deadline_at", deadline_at)
        if self.submitted_at is not None:
            object.__setattr__(
                self,
                "submitted_at",
                _require_utc_datetime(self.submitted_at, "submitted_at"),
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "attempt_id": self.attempt_id,
            "assessment": self.assessment.to_dict(),
            "profile": self.profile.to_dict(),
            "started_at": _timestamp(self.started_at, "started_at"),
            "deadline_at": _timestamp(self.deadline_at, "deadline_at"),
            "status": self.status,
            "revision": self.revision,
            "score": None if self.score is None else self.score.to_dict(),
            "submitted_at": (
                None
                if self.submitted_at is None
                else _timestamp(self.submitted_at, "submitted_at")
            ),
        }

    @classmethod
    def from_dict(cls, value: object) -> SessionState:
        data = _require_mapping(value, "session")
        if "schema_version" not in data:
            _invalid("session must include schema_version")
        version = _require_string(data["schema_version"], "schema_version")
        if version != SESSION_SCHEMA_VERSION:
            _invalid("unsupported session schema version")
        _require_keys(
            data,
            frozenset(
                (
                    "schema_version",
                    "attempt_id",
                    "assessment",
                    "profile",
                    "started_at",
                    "deadline_at",
                    "status",
                    "revision",
                    "score",
                    "submitted_at",
                )
            ),
            "session",
        )
        raw_score = data["score"]
        raw_submitted_at = data["submitted_at"]
        status = _require_string(data["status"], "status")
        return cls(
            schema_version=SESSION_SCHEMA_VERSION,
            attempt_id=_require_uuid(data["attempt_id"], "attempt_id"),
            assessment=AssessmentMetadata.from_dict(data["assessment"]),
            profile=ModeProfile.from_dict(data["profile"]),
            started_at=_parse_utc_timestamp(data["started_at"], "started_at"),
            deadline_at=_parse_utc_timestamp(data["deadline_at"], "deadline_at"),
            status=status,  # type: ignore[arg-type]
            revision=_require_nonnegative_integer(data["revision"], "revision"),
            score=None if raw_score is None else ScoreSummary.from_dict(raw_score),
            submitted_at=(
                None
                if raw_submitted_at is None
                else _parse_utc_timestamp(raw_submitted_at, "submitted_at")
            ),
        )


SessionRecord = SessionState | SessionStateV2


def parse_session_record(value: object) -> SessionRecord:
    """Dispatch on schema_version before interpreting any other session fields."""
    version = _require_schema_version(value, "session")
    if version == SESSION_SCHEMA_VERSION:
        return SessionState.from_dict(value)
    if version == SESSION_SCHEMA_VERSION_V2:
        return SessionStateV2.from_dict(value)
    raise UnsupportedSchemaVersionError(f"unsupported session schema version: {version}")


def adapt_session_record(record: SessionRecord) -> AdaptedSessionRecord:
    """Normalize v1 or v2 session records in memory without upgrading disk bytes."""
    if isinstance(record, SessionStateV2):
        return AdaptedSessionRecord(
            record=record,
            schema_version=record.schema_version,
            attempt_id=record.attempt_id,
            assessment_id=record.assessment.assessment_id,
            display_name=record.assessment.display_name,
            profile=record.profile,
            started_at=record.started_at,
            deadline_at=record.deadline_at,
            status=record.status,
            revision=record.revision,
            score=record.score,
            submitted_at=record.submitted_at,
            content_version=record.assessment.content_version,
            content_digest=record.assessment.content_digest,
            content_identity_available=True,
            abandonment=record.abandonment,
            practice_score=(
                None
                if record.abandonment is None
                else record.abandonment.practice_score
            ),
        )
    return AdaptedSessionRecord(
        record=record,
        schema_version=record.schema_version,
        attempt_id=record.attempt_id,
        assessment_id=record.assessment.assessment_id,
        display_name=record.assessment.display_name,
        profile=record.profile,
        started_at=record.started_at,
        deadline_at=record.deadline_at,
        status=record.status,
        revision=record.revision,
        score=record.score,
        submitted_at=record.submitted_at,
        content_version=None,
        content_digest=None,
        content_identity_available=False,
        abandonment=None,
        practice_score=None,
    )


@dataclass(frozen=True, slots=True)
class EventRecord:
    """An append-only, versioned record of one command outcome."""

    schema_version: str
    event_id: str
    attempt_id: str
    revision: int
    occurred_at: datetime
    name: str
    outcome: Literal["succeeded", "rejected", "recovered"]
    arguments: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.schema_version != EVENT_SCHEMA_VERSION:
            _invalid("unsupported event schema version")
        _require_uuid(self.event_id, "event_id")
        _require_uuid(self.attempt_id, "attempt_id")
        _require_nonnegative_integer(self.revision, "revision")
        object.__setattr__(
            self, "occurred_at", _require_utc_datetime(self.occurred_at, "occurred_at")
        )
        _require_identifier(self.name, "event name")
        if self.outcome not in _EVENT_OUTCOMES:
            _invalid("event outcome is invalid")
        arguments = _require_mapping(self.arguments, "event arguments")
        object.__setattr__(self, "arguments", _freeze_json(arguments, "event arguments"))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "attempt_id": self.attempt_id,
            "revision": self.revision,
            "occurred_at": _timestamp(self.occurred_at, "occurred_at"),
            "name": self.name,
            "outcome": self.outcome,
            "arguments": _thaw_json(self.arguments),
        }

    @classmethod
    def from_dict(cls, value: object) -> EventRecord:
        data = _require_mapping(value, "event")
        if "schema_version" not in data:
            _invalid("event must include schema_version")
        version = _require_string(data["schema_version"], "schema_version")
        if version != EVENT_SCHEMA_VERSION:
            _invalid("unsupported event schema version")
        _require_keys(
            data,
            frozenset(
                (
                    "schema_version",
                    "event_id",
                    "attempt_id",
                    "revision",
                    "occurred_at",
                    "name",
                    "outcome",
                    "arguments",
                )
            ),
            "event",
        )
        outcome = _require_string(data["outcome"], "event outcome")
        return cls(
            schema_version=EVENT_SCHEMA_VERSION,
            event_id=_require_uuid(data["event_id"], "event_id"),
            attempt_id=_require_uuid(data["attempt_id"], "attempt_id"),
            revision=_require_nonnegative_integer(data["revision"], "revision"),
            occurred_at=_parse_utc_timestamp(data["occurred_at"], "occurred_at"),
            name=_require_identifier(data["name"], "event name"),
            outcome=outcome,  # type: ignore[arg-type]
            arguments=_require_mapping(data["arguments"], "event arguments"),
        )


@dataclass(frozen=True, slots=True)
class EventRecordV2:
    """An append-only, versioned record of one command outcome (v2 schema)."""

    schema_version: str
    event_id: str
    attempt_id: str
    revision: int
    occurred_at: datetime
    name: str
    outcome: Literal["succeeded", "rejected", "recovered"]
    arguments: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.schema_version != EVENT_SCHEMA_VERSION_V2:
            _invalid("unsupported event schema version")
        _require_uuid(self.event_id, "event_id")
        _require_uuid(self.attempt_id, "attempt_id")
        _require_nonnegative_integer(self.revision, "revision")
        object.__setattr__(
            self, "occurred_at", _require_utc_datetime(self.occurred_at, "occurred_at")
        )
        _require_identifier(self.name, "event name")
        if self.outcome not in _EVENT_OUTCOMES:
            _invalid("event outcome is invalid")
        arguments = _require_mapping(self.arguments, "event arguments")
        object.__setattr__(self, "arguments", _freeze_json(arguments, "event arguments"))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "attempt_id": self.attempt_id,
            "revision": self.revision,
            "occurred_at": _timestamp(self.occurred_at, "occurred_at"),
            "name": self.name,
            "outcome": self.outcome,
            "arguments": _thaw_json(self.arguments),
        }

    @classmethod
    def from_dict(cls, value: object) -> EventRecordV2:
        data = _require_mapping(value, "event")
        _require_keys(
            data,
            frozenset(
                (
                    "schema_version",
                    "event_id",
                    "attempt_id",
                    "revision",
                    "occurred_at",
                    "name",
                    "outcome",
                    "arguments",
                )
            ),
            "event",
        )
        outcome = _require_string(data["outcome"], "event outcome")
        if _require_string(data["schema_version"], "schema_version") != (
            EVENT_SCHEMA_VERSION_V2
        ):
            _invalid("unsupported event schema version")
        return cls(
            schema_version=EVENT_SCHEMA_VERSION_V2,
            event_id=_require_uuid(data["event_id"], "event_id"),
            attempt_id=_require_uuid(data["attempt_id"], "attempt_id"),
            revision=_require_nonnegative_integer(data["revision"], "revision"),
            occurred_at=_parse_utc_timestamp(data["occurred_at"], "occurred_at"),
            name=_require_identifier(data["name"], "event name"),
            outcome=outcome,  # type: ignore[arg-type]
            arguments=_require_mapping(data["arguments"], "event arguments"),
        )


EventRecordUnion = EventRecord | EventRecordV2


def parse_event_record(value: object) -> EventRecordUnion:
    """Dispatch on schema_version before interpreting any other event fields."""
    version = _require_schema_version(value, "event")
    if version == EVENT_SCHEMA_VERSION:
        return EventRecord.from_dict(value)
    if version == EVENT_SCHEMA_VERSION_V2:
        return EventRecordV2.from_dict(value)
    raise UnsupportedSchemaVersionError(f"unsupported event schema version: {version}")


def session_event(
    state: SessionRecord,
    *,
    event_id: str,
    occurred_at: datetime,
    name: str,
    outcome: Literal["succeeded", "rejected", "recovered"],
    arguments: Mapping[str, object],
) -> EventRecordUnion:
    """Build the event for ``state.revision`` in the session's schema family."""
    if isinstance(state, SessionStateV2):
        return EventRecordV2(
            schema_version=EVENT_SCHEMA_VERSION_V2,
            event_id=event_id,
            attempt_id=state.attempt_id,
            revision=state.revision,
            occurred_at=occurred_at,
            name=name,
            outcome=outcome,
            arguments=arguments,
        )
    if isinstance(state, SessionState):
        return EventRecord(
            schema_version=EVENT_SCHEMA_VERSION,
            event_id=event_id,
            attempt_id=state.attempt_id,
            revision=state.revision,
            occurred_at=occurred_at,
            name=name,
            outcome=outcome,
            arguments=arguments,
        )
    _invalid("session is invalid")


@dataclass(frozen=True, slots=True)
class ReviewSource:
    """The exact submitted bytes, verified against their own digest."""

    filename: str
    sha256: str
    content: str

    def __post_init__(self) -> None:
        if self.filename != "simulation.py":
            _invalid("review source filename is invalid")
        _require_digest(self.sha256, "review source sha256")
        if not isinstance(self.content, str):
            _invalid("review source content must be a string")
        raw = self.content.encode("utf-8")
        if len(raw) > MAX_DOCUMENT_BYTES:
            _invalid("review source content exceeds the supported size limit")
        if hashlib.sha256(raw).hexdigest() != self.sha256:
            _invalid("review source content does not match its digest")

    def to_dict(self) -> dict[str, object]:
        return {
            "filename": self.filename,
            "sha256": self.sha256,
            "content": self.content,
        }

    @classmethod
    def from_dict(cls, value: object) -> ReviewSource:
        data = _require_mapping(value, "review source")
        _require_keys(data, frozenset(("filename", "sha256", "content")), "review source")
        return cls(
            filename=_require_string(data["filename"], "review source filename"),
            sha256=_require_digest(data["sha256"], "review source sha256"),
            content=data["content"],  # type: ignore[arg-type]
        )

    @classmethod
    def capture(cls, filename: str, content: str) -> ReviewSource:
        """Digest exactly the bytes handed in; never re-read the file."""
        if not isinstance(content, str):
            _invalid("review source content must be a string")
        return cls(
            filename=filename,
            sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            content=content,
        )


@dataclass(frozen=True, slots=True)
class ReviewRecord:
    """Immutable scored submission review bound to one attempt revision.

    ``content_identity`` is ``pinned`` only for attempts created with a verified
    content identity. A legacy v1 attempt submitted by this release records
    ``unavailable`` with its stored metadata: today's registry is never consulted
    to fill that gap. ``source`` is null when the submitted bytes could not be
    read, which is honest absence, not a failed verification.
    """

    schema_version: str
    attempt_id: str
    state_revision: int
    assessment: PinnedAssessment | AssessmentMetadata
    content_identity: Literal["pinned", "unavailable"]
    profile: ModeProfile
    started_at: datetime
    deadline_at: datetime
    submitted_at: datetime
    score: ScoreSummary
    source: ReviewSource | None = None

    def __post_init__(self) -> None:
        if self.schema_version != REVIEW_SCHEMA_VERSION:
            _invalid("unsupported review schema version")
        _require_uuid(self.attempt_id, "attempt_id")
        _require_positive_integer(self.state_revision, "state_revision")
        if self.content_identity not in _CONTENT_IDENTITY:
            _invalid("review content identity is invalid")
        pinned = self.content_identity == CONTENT_IDENTITY_PINNED
        if pinned != isinstance(self.assessment, PinnedAssessment) or not isinstance(
            self.assessment, (PinnedAssessment, AssessmentMetadata)
        ):
            _invalid("review assessment does not match its content identity")
        if not isinstance(self.profile, ModeProfile):
            _invalid("profile is invalid")
        started_at = _require_utc_datetime(self.started_at, "started_at")
        deadline_at = _require_utc_datetime(self.deadline_at, "deadline_at")
        submitted_at = _require_utc_datetime(self.submitted_at, "submitted_at")
        if deadline_at <= started_at:
            _invalid("deadline_at must be after started_at")
        if deadline_at - started_at != timedelta(seconds=self.profile.duration_seconds):
            _invalid("deadline_at must match the effective profile duration")
        if submitted_at < started_at:
            _invalid("submitted_at must not precede started_at")
        if not isinstance(self.score, ScoreSummary):
            _invalid("score is invalid")
        if self.source is not None and not isinstance(self.source, ReviewSource):
            _invalid("review source is invalid")
        object.__setattr__(self, "started_at", started_at)
        object.__setattr__(self, "deadline_at", deadline_at)
        object.__setattr__(self, "submitted_at", submitted_at)

    @property
    def source_captured(self) -> bool:
        return self.source is not None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "attempt_id": self.attempt_id,
            "state_revision": self.state_revision,
            "assessment": self.assessment.to_dict(),
            "content_identity": self.content_identity,
            "profile": self.profile.to_dict(),
            "started_at": _timestamp(self.started_at, "started_at"),
            "deadline_at": _timestamp(self.deadline_at, "deadline_at"),
            "submitted_at": _timestamp(self.submitted_at, "submitted_at"),
            "score": self.score.to_dict(),
            "source": None if self.source is None else self.source.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: object) -> ReviewRecord:
        data = _require_mapping(value, "review")
        _require_keys(
            data,
            frozenset(
                (
                    "schema_version",
                    "attempt_id",
                    "state_revision",
                    "assessment",
                    "content_identity",
                    "profile",
                    "started_at",
                    "deadline_at",
                    "submitted_at",
                    "score",
                    "source",
                )
            ),
            "review",
        )
        if _require_string(data["schema_version"], "schema_version") != (
            REVIEW_SCHEMA_VERSION
        ):
            _invalid("unsupported review schema version")
        identity = _require_string(data["content_identity"], "content_identity")
        if identity not in _CONTENT_IDENTITY:
            _invalid("review content identity is invalid")
        raw_source = data["source"]
        assessment = (
            PinnedAssessment.from_dict(data["assessment"])
            if identity == CONTENT_IDENTITY_PINNED
            else AssessmentMetadata.from_dict(data["assessment"])
        )
        return cls(
            schema_version=REVIEW_SCHEMA_VERSION,
            attempt_id=_require_uuid(data["attempt_id"], "attempt_id"),
            state_revision=_require_positive_integer(
                data["state_revision"], "state_revision"
            ),
            assessment=assessment,
            content_identity=identity,  # type: ignore[arg-type]
            profile=ModeProfile.from_dict(data["profile"]),
            started_at=_parse_utc_timestamp(data["started_at"], "started_at"),
            deadline_at=_parse_utc_timestamp(data["deadline_at"], "deadline_at"),
            submitted_at=_parse_utc_timestamp(data["submitted_at"], "submitted_at"),
            score=ScoreSummary.from_dict(data["score"]),
            source=None if raw_source is None else ReviewSource.from_dict(raw_source),
        )

    @classmethod
    def plan(
        cls,
        prior_state: SessionRecord,
        *,
        revision: int,
        submitted_at: datetime,
        score: ScoreSummary,
        source: ReviewSource | None,
    ) -> ReviewRecord:
        """Build the review for a submission before its state is constructed.

        A v2 submitted state stores this review's digest, so the review must
        exist first.
        """
        pinned = isinstance(prior_state, SessionStateV2)
        return cls(
            schema_version=REVIEW_SCHEMA_VERSION,
            attempt_id=prior_state.attempt_id,
            state_revision=revision,
            assessment=prior_state.assessment,
            content_identity=(
                CONTENT_IDENTITY_PINNED if pinned else CONTENT_IDENTITY_UNAVAILABLE
            ),
            profile=prior_state.profile,
            started_at=prior_state.started_at,
            deadline_at=prior_state.deadline_at,
            submitted_at=submitted_at,
            score=score,
            source=source,
        )


def canonical_review_bytes(review: ReviewRecord) -> bytes:
    """Return the exact published bytes a review digest is taken over."""
    if not isinstance(review, ReviewRecord):
        _invalid("review is invalid")
    text = json.dumps(
        review.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    raw = (text + "\n").encode("utf-8")
    if len(raw) > MAX_REVIEW_BYTES:
        _invalid("review exceeds the supported size limit")
    return raw


def review_digest(review: ReviewRecord) -> str:
    """Return the digest a submitted v2 state stores to identify its review."""
    return hashlib.sha256(canonical_review_bytes(review)).hexdigest()


def parse_review_record(value: object) -> ReviewRecord:
    """Dispatch on schema_version before interpreting any other review fields."""
    version = _require_schema_version(value, "review")
    if version == REVIEW_SCHEMA_VERSION:
        return ReviewRecord.from_dict(value)
    raise UnsupportedSchemaVersionError(f"unsupported review schema version: {version}")


_SUBMISSION_RECOVERY_FAMILIES: Mapping[str, tuple[type, type]] = MappingProxyType(
    {
        SUBMISSION_RECOVERY_SCHEMA_VERSION: (SessionState, EventRecord),
        SUBMISSION_RECOVERY_SCHEMA_VERSION_V2: (SessionStateV2, EventRecordV2),
    }
)


@dataclass(frozen=True, slots=True)
class SubmissionRecovery:
    """A write-ahead record for finishing one scored submission exactly once.

    submission-recovery/v1 carries only session/v1 and event/v1 records and is
    unchanged from earlier releases. submission-recovery/v2 carries only
    session/v2 and event/v2 records.
    """

    schema_version: str
    prior_state: SessionRecord
    state: SessionRecord
    event: EventRecordUnion
    review: ReviewRecord | None = None

    def __post_init__(self) -> None:
        family = _SUBMISSION_RECOVERY_FAMILIES.get(self.schema_version)
        if family is None:
            _invalid("unsupported submission recovery schema version")
        state_type, event_type = family
        if (
            type(self.prior_state) is not state_type
            or self.prior_state.status not in (ACTIVE, EXPIRED)
        ):
            _invalid("submission recovery requires an active or expired prior session")
        if type(self.state) is not state_type or self.state.status != SUBMITTED:
            _invalid("submission recovery requires a submitted session")
        if type(self.event) is not event_type:
            _invalid("submission recovery event is invalid")
        if (
            self.state.attempt_id != self.prior_state.attempt_id
            or self.state.assessment != self.prior_state.assessment
            or self.state.profile != self.prior_state.profile
            or self.state.started_at != self.prior_state.started_at
            or self.state.deadline_at != self.prior_state.deadline_at
            or self.state.revision != self.prior_state.revision + 1
            or self.event.attempt_id != self.state.attempt_id
            or self.event.revision != self.state.revision
            or self.event.occurred_at != self.state.submitted_at
            or self.event.name != "submitted"
            or self.event.outcome != "succeeded"
            or dict(self.event.arguments)
        ):
            _invalid("submission recovery does not match its submitted session")
        self._validate_review()

    def _validate_review(self) -> None:
        """Bind the recorded review to the exact submission it publishes.

        A submission-recovery/v1 file written before immutable capture existed
        has no review and still replays; a v2 submission always carries one.
        """
        if self.review is None:
            if isinstance(self.state, SessionStateV2):
                _invalid("submission recovery requires its review record")
            return
        if not isinstance(self.review, ReviewRecord):
            _invalid("submission recovery review is invalid")
        if (
            self.review.attempt_id != self.state.attempt_id
            or self.review.state_revision != self.state.revision
            or self.review.submitted_at != self.state.submitted_at
            or self.review.score != self.state.score
            or self.review.profile != self.state.profile
            or self.review.started_at != self.state.started_at
            or self.review.deadline_at != self.state.deadline_at
            or self.review.assessment != self.state.assessment
        ):
            _invalid("submission recovery review does not match its session")
        if isinstance(self.state, SessionStateV2) and (
            self.state.review_digest != review_digest(self.review)
        ):
            _invalid("submitted session does not identify its review record")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "prior_state": self.prior_state.to_dict(),
            "state": self.state.to_dict(),
            "event": self.event.to_dict(),
            "review": None if self.review is None else self.review.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: object) -> SubmissionRecovery:
        data = _require_mapping(value, "submission recovery")
        # A pre-capture submission-recovery/v1 file has no review key at all.
        expected = {"schema_version", "prior_state", "state", "event"}
        if "review" in data:
            expected.add("review")
        _require_keys(data, frozenset(expected), "submission recovery")
        raw_review = data.get("review")
        version = _require_string(data["schema_version"], "schema_version")
        family = _SUBMISSION_RECOVERY_FAMILIES.get(version)
        if family is None:
            raise UnsupportedSchemaVersionError(
                f"unsupported submission recovery schema version: {version}"
            )
        state_type, event_type = family
        return cls(
            schema_version=version,
            prior_state=state_type.from_dict(data["prior_state"]),
            state=state_type.from_dict(data["state"]),
            event=event_type.from_dict(data["event"]),
            review=None if raw_review is None else ReviewRecord.from_dict(raw_review),
        )

    @classmethod
    def for_submission(
        cls,
        prior_state: SessionRecord,
        state: SessionRecord,
        event: EventRecordUnion,
        review: ReviewRecord | None = None,
    ) -> SubmissionRecovery:
        """Choose the recovery schema that matches the session's family."""
        version = (
            SUBMISSION_RECOVERY_SCHEMA_VERSION_V2
            if isinstance(state, SessionStateV2)
            else SUBMISSION_RECOVERY_SCHEMA_VERSION
        )
        return cls(
            schema_version=version,
            prior_state=prior_state,
            state=state,
            event=event,
            review=review,
        )


@dataclass(frozen=True, slots=True)
class ActivePointer:
    """The validated workspace-root selection, never session authority."""

    schema_version: str
    attempt_id: str

    def __post_init__(self) -> None:
        if self.schema_version != ACTIVE_POINTER_SCHEMA_VERSION:
            _invalid("unsupported active pointer schema version")
        _require_uuid(self.attempt_id, "attempt_id")

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": self.schema_version, "attempt_id": self.attempt_id}

    @classmethod
    def from_dict(cls, value: object) -> ActivePointer:
        data = _require_mapping(value, "active pointer")
        _require_keys(
            data, frozenset(("schema_version", "attempt_id")), "active pointer"
        )
        return cls(
            schema_version=_require_string(data["schema_version"], "schema_version"),
            attempt_id=_require_uuid(data["attempt_id"], "attempt_id"),
        )


__all__ = [
    "ACTIVE",
    "ABANDONED",
    "ACTIVE_POINTER_SCHEMA_VERSION",
    "AdaptedSessionRecord",
    "AbandonmentMetadata",
    "DRILL_DEFAULT_DURATION_SECONDS",
    "DRILL_MODE",
    "DRILL_PROFILE",
    "ERROR",
    "EVENT_SCHEMA_VERSION",
    "EVENT_SCHEMA_VERSION_V2",
    "EXPIRED",
    "EventRecord",
    "EventRecordUnion",
    "EventRecordV2",
    "FAILED",
    "FULL_DURATION_SECONDS",
    "FULL_MODE",
    "FULL_PROFILE",
    "PASSED",
    "PinnedAssessment",
    "CONTENT_IDENTITY_PINNED",
    "CONTENT_IDENTITY_UNAVAILABLE",
    "MAX_REVIEW_BYTES",
    "REVIEW_SCHEMA_VERSION",
    "ReviewRecord",
    "ReviewSource",
    "SESSION_SCHEMA_VERSION",
    "SESSION_SCHEMA_VERSION_V2",
    "SUBMITTED",
    "ActivePointer",
    "AssessmentMetadata",
    "LevelResult",
    "ModeProfile",
    "ScoreSummary",
    "SessionRecord",
    "SessionState",
    "SessionStateV2",
    "SUBMISSION_RECOVERY_SCHEMA_VERSION",
    "SUBMISSION_RECOVERY_SCHEMA_VERSION_V2",
    "SubmissionRecovery",
    "adapt_session_record",
    "canonical_review_bytes",
    "parse_event_record",
    "parse_review_record",
    "parse_session_record",
    "review_digest",
    "session_event",
]
