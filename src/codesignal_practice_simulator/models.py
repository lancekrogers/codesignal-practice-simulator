"""Validated, immutable JSON models for the session runtime.

This module is the sole owner of durable session, event, and active-pointer
schemas. Persistence code reads and writes only these model dictionaries.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from types import MappingProxyType
from typing import Any, Literal, Mapping
from uuid import UUID

from .errors import InvalidInputError


SESSION_SCHEMA_VERSION = "session/v1"
EVENT_SCHEMA_VERSION = "event/v1"
ACTIVE_POINTER_SCHEMA_VERSION = "active-pointer/v1"

FULL_MODE = "full"
DRILL_MODE = "drill"
FULL_PROFILE = "full-90m"
DRILL_PROFILE = "drill-30m"
FULL_DURATION_SECONDS = 90 * 60
DRILL_DEFAULT_DURATION_SECONDS = 30 * 60

ACTIVE = "active"
EXPIRED = "expired"
SUBMITTED = "submitted"

PASSED = "passed"
FAILED = "failed"
ERROR = "error"

_IDENTIFIER = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
_SLUG = re.compile(r"[a-z][a-z0-9-]{0,63}\Z")
_OUTCOMES = frozenset((PASSED, FAILED, ERROR))
_EVENT_OUTCOMES = frozenset(("succeeded", "rejected", "recovered"))
_STATUSES = frozenset((ACTIVE, EXPIRED, SUBMITTED))


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
            schema_version=_require_string(data["schema_version"], "schema_version"),
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
            schema_version=_require_string(data["schema_version"], "schema_version"),
            event_id=_require_uuid(data["event_id"], "event_id"),
            attempt_id=_require_uuid(data["attempt_id"], "attempt_id"),
            revision=_require_nonnegative_integer(data["revision"], "revision"),
            occurred_at=_parse_utc_timestamp(data["occurred_at"], "occurred_at"),
            name=_require_identifier(data["name"], "event name"),
            outcome=outcome,  # type: ignore[arg-type]
            arguments=_require_mapping(data["arguments"], "event arguments"),
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
    "ACTIVE_POINTER_SCHEMA_VERSION",
    "DRILL_DEFAULT_DURATION_SECONDS",
    "DRILL_MODE",
    "DRILL_PROFILE",
    "ERROR",
    "EVENT_SCHEMA_VERSION",
    "EXPIRED",
    "FAILED",
    "FULL_DURATION_SECONDS",
    "FULL_MODE",
    "FULL_PROFILE",
    "PASSED",
    "SESSION_SCHEMA_VERSION",
    "SUBMITTED",
    "ActivePointer",
    "AssessmentMetadata",
    "EventRecord",
    "LevelResult",
    "ModeProfile",
    "ScoreSummary",
    "SessionState",
]
