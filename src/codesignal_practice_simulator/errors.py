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
    """Expected error that can be rendered without a traceback.

    ``code`` is an optional stable machine-readable name more specific than the
    exit-code family; transports use it when present so a client can tell a
    stale revision from a busy lock without parsing the message.
    """

    exit_code: ExitCode
    code: str | None = None

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


class RestartRecoveryPendingError(SessionUnavailableError):
    """A restart passed its commit point but storage did not finish publishing it.

    The operation is durable and will roll forward on the next workspace
    mutation or explicit recovery; nothing is lost and no second replacement
    will be created.
    """

    code = "recovery_pending"


class IllegalLifecycleError(DomainError):
    """The requested command is not allowed in the session's lifecycle state."""

    exit_code = ExitCode.ILLEGAL_LIFECYCLE


class LockUnavailableError(IllegalLifecycleError):
    """A concurrent writer owns the required session or workspace lock."""


class ScoredSourceChangedError(IllegalLifecycleError):
    """Candidate source changed while it was being scored; nothing was committed."""


class RestartConflictError(IllegalLifecycleError):
    """A restart operation UUID was reused with different arguments."""

    code = "operation_conflict"


class StaleRevisionError(IllegalLifecycleError):
    """The caller's expected attempt revision is not the current one."""

    code = "stale_revision"


class LiveSelectionError(IllegalLifecycleError):
    """A different live attempt is selected; resolve it explicitly first."""

    code = "live_selection"


class CandidateFailureError(DomainError):
    """Candidate tests completed but at least one level group failed."""

    exit_code = ExitCode.CANDIDATE_FAILURE
