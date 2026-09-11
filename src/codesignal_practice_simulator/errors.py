"""Stable, safe domain errors for command adapters and services."""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    """Documented process exit codes for expected domain failures."""

    INVALID_INPUT = 2
    SESSION_UNAVAILABLE = 3
    ILLEGAL_LIFECYCLE = 4
    CANDIDATE_FAILURE = 5


class DomainError(Exception):
    """Expected error that can be rendered without a traceback."""

    exit_code: ExitCode

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidInputError(DomainError):
    """The command input or a value supplied to a model is invalid."""

    exit_code = ExitCode.INVALID_INPUT


class UnsupportedSchemaVersionError(InvalidInputError):
    """A persisted or supplied schema_version is not supported by this release."""


class SessionUnavailableError(DomainError):
    """The selected session is absent or cannot be read."""

    exit_code = ExitCode.SESSION_UNAVAILABLE


class SessionCorruptError(SessionUnavailableError):
    """Persisted session data is present but does not satisfy its schema."""


class FixtureSetupRequiredError(SessionUnavailableError):
    """The required immutable fixture cache is absent or invalid."""


class AssessmentVersionUnavailableError(SessionUnavailableError):
    """An attempt's pinned content version is not the installed definition."""


class ReviewPendingError(SessionUnavailableError):
    """A review read observed a changing or unfinished record; retry it."""


class IllegalLifecycleError(DomainError):
    """The requested command is not allowed in the session's lifecycle state."""

    exit_code = ExitCode.ILLEGAL_LIFECYCLE


class LockUnavailableError(IllegalLifecycleError):
    """A concurrent writer owns the required session or workspace lock."""


class ScoredSourceChangedError(IllegalLifecycleError):
    """Candidate source changed while it was being scored; nothing was committed."""


class CandidateFailureError(DomainError):
    """Candidate tests completed but at least one level group failed."""

    exit_code = ExitCode.CANDIDATE_FAILURE
