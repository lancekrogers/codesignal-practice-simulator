"""Application services for deterministic, locked attempt lifecycle changes.

This module owns lifecycle policy.  Command adapters can select a workspace,
call one service method, and render the returned typed data without reading or
writing runtime files themselves.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal
from uuid import uuid4

from .clock import Clock
from .errors import IllegalLifecycleError, InvalidInputError
from .models import (
    ACTIVE,
    ACTIVE_POINTER_SCHEMA_VERSION,
    DRILL_DEFAULT_DURATION_SECONDS,
    DRILL_MODE,
    DRILL_PROFILE,
    EVENT_SCHEMA_VERSION,
    EXPIRED,
    FULL_DURATION_SECONDS,
    FULL_MODE,
    FULL_PROFILE,
    SESSION_SCHEMA_VERSION,
    SUBMITTED,
    ActivePointer,
    AssessmentMetadata,
    EventRecord,
    ModeProfile,
    ScoreSummary,
    SessionState,
)
from .workspace import WorkspaceManager


Scorer = Callable[[Path], ScoreSummary]


@dataclass(frozen=True, slots=True)
class TimeObservation:
    """A state snapshot and clock values from one locked observation."""

    state: SessionState
    observed_at: datetime
    elapsed_seconds: int
    remaining_seconds: int


@dataclass(frozen=True, slots=True)
class SubmissionResult:
    """The durable final result returned by both first and repeat submissions."""

    state: SessionState
    score: ScoreSummary


class LifecycleService:
    """Apply lifecycle rules to isolated attempts using injected dependencies."""

    def __init__(
        self,
        workspace: WorkspaceManager,
        clock: Clock,
        scorer: Scorer | None = None,
    ) -> None:
        self.workspace = workspace
        self.clock = clock
        self.scorer = scorer
        self.persistence = workspace.persistence

    def start(
        self,
        assessment: AssessmentMetadata,
        *,
        mode: Literal["full", "drill"] = FULL_MODE,
        drill_duration_seconds: int | None = None,
    ) -> SessionState:
        """Create and select one active attempt with an effective profile."""
        if not isinstance(assessment, AssessmentMetadata):
            raise InvalidInputError("assessment is invalid")
        profile = self._profile(mode, drill_duration_seconds)
        started_at = self._now()
        state = SessionState(
            schema_version=SESSION_SCHEMA_VERSION,
            attempt_id=str(uuid4()),
            assessment=assessment,
            profile=profile,
            started_at=started_at,
            deadline_at=started_at + timedelta(seconds=profile.duration_seconds),
            status=ACTIVE,
            revision=0,
        )
        self.workspace.create_attempt(state)
        return state

    def select_attempt(self, attempt_id: str | None = None) -> Path:
        """Resolve an explicit attempt before the validated active selection."""
        return self.workspace.resolve_attempt(attempt_id)

    def resume(self, attempt_id: str | None = None) -> SessionState:
        """Resume an active attempt and select an explicitly named attempt."""
        attempt = self.select_attempt(attempt_id)
        with self.persistence.attempt_lock(attempt):
            state = self.persistence.read_session(attempt)
            if state.status != ACTIVE:
                raise IllegalLifecycleError(
                    f"cannot resume an attempt in {state.status} state"
                )
            self._recover_missing_event_locked(attempt, state)
            state, _observed_at = self._expire_if_overdue_locked(attempt, state)
            if state.status != ACTIVE:
                raise IllegalLifecycleError(
                    f"cannot resume an attempt in {state.status} state"
                )
            if attempt_id is not None:
                self.persistence.write_active_pointer(
                    self.workspace.attempts_directory,
                    self._pointer_for(state),
                )
            return state

    def status(self, attempt_id: str | None = None) -> SessionState:
        """Observe expiry if needed, then return the authoritative state."""
        attempt = self.select_attempt(attempt_id)
        with self.persistence.attempt_lock(attempt):
            state = self.persistence.read_session(attempt)
            self._recover_missing_event_locked(attempt, state)
            state, _observed_at = self._expire_if_overdue_locked(attempt, state)
            return state

    def time(self, attempt_id: str | None = None) -> TimeObservation:
        """Observe expiry if needed and return an elapsed/remaining-time view."""
        attempt = self.select_attempt(attempt_id)
        with self.persistence.attempt_lock(attempt):
            state = self.persistence.read_session(attempt)
            self._recover_missing_event_locked(attempt, state)
            state, observed_at = self._expire_if_overdue_locked(attempt, state)
            elapsed_seconds = int((observed_at - state.started_at).total_seconds())
            remaining_seconds = max(
                0, int((state.deadline_at - observed_at).total_seconds())
            )
            return TimeObservation(
                state=state,
                observed_at=observed_at,
                elapsed_seconds=elapsed_seconds,
                remaining_seconds=remaining_seconds,
            )

    def test(self, attempt_id: str | None = None) -> SessionState:
        """Score an active attempt and persist its latest complete score."""
        attempt = self.select_attempt(attempt_id)
        with self.persistence.attempt_lock(attempt):
            state = self.persistence.read_session(attempt)
            if state.status != ACTIVE:
                raise IllegalLifecycleError(
                    f"cannot test an attempt in {state.status} state"
                )
            self._recover_missing_event_locked(attempt, state)
            state, _observed_at = self._expire_if_overdue_locked(attempt, state)
            if state.status != ACTIVE:
                raise IllegalLifecycleError(
                    f"cannot test an attempt in {state.status} state"
                )
            scorer = self._require_scorer()
            return self._record_test_result_locked(attempt, state, scorer(attempt))

    def record_test_result(
        self, score: ScoreSummary, attempt_id: str | None = None
    ) -> SessionState:
        """Persist a scorer-provided result for an active attempt.

        The later isolated scoring service may call this method after producing
        its four-level result without gaining direct persistence access.
        """
        if not isinstance(score, ScoreSummary):
            raise InvalidInputError("score is invalid")
        attempt = self.select_attempt(attempt_id)
        with self.persistence.attempt_lock(attempt):
            state = self.persistence.read_session(attempt)
            if state.status != ACTIVE:
                raise IllegalLifecycleError(
                    f"cannot test an attempt in {state.status} state"
                )
            self._recover_missing_event_locked(attempt, state)
            state, _observed_at = self._expire_if_overdue_locked(attempt, state)
            if state.status != ACTIVE:
                raise IllegalLifecycleError(
                    f"cannot test an attempt in {state.status} state"
                )
            return self._record_test_result_locked(attempt, state, score)

    def submit(self, attempt_id: str | None = None) -> SubmissionResult:
        """Finalize an active or expired attempt exactly once."""
        attempt = self.select_attempt(attempt_id)
        with self.persistence.attempt_lock(attempt):
            state = self.persistence.read_session(attempt)
            if state.status == SUBMITTED:
                assert state.score is not None
                return SubmissionResult(state=state, score=state.score)
            if state.status not in (ACTIVE, EXPIRED):
                raise IllegalLifecycleError(
                    f"cannot submit an attempt in {state.status} state"
                )
            self._recover_missing_event_locked(attempt, state)
            state, _observed_at = self._expire_if_overdue_locked(attempt, state)
            scorer = self._require_scorer()
            score = scorer(attempt)
            if not isinstance(score, ScoreSummary):
                raise InvalidInputError("scorer returned an invalid score")
            submitted = replace(
                state,
                status=SUBMITTED,
                revision=state.revision + 1,
                score=score,
                submitted_at=self._now(),
            )
            self._persist_transition_locked(attempt, submitted, "submitted")
            return SubmissionResult(state=submitted, score=score)

    def _record_test_result_locked(
        self, attempt: Path, state: SessionState, score: ScoreSummary
    ) -> SessionState:
        if not isinstance(score, ScoreSummary):
            raise InvalidInputError("score is invalid")
        recorded = replace(state, revision=state.revision + 1, score=score)
        self._persist_transition_locked(attempt, recorded, "tested")
        return recorded

    def _expire_if_overdue_locked(
        self, attempt: Path, state: SessionState
    ) -> tuple[SessionState, datetime]:
        observed_at = self._now()
        if state.status == ACTIVE and observed_at >= state.deadline_at:
            expired = replace(state, status=EXPIRED, revision=state.revision + 1)
            self._persist_transition_locked(attempt, expired, "expired", observed_at)
            return expired, observed_at
        return state, observed_at

    def _persist_transition_locked(
        self,
        attempt: Path,
        state: SessionState,
        name: str,
        occurred_at: datetime | None = None,
    ) -> None:
        self.persistence.write_session_locked(attempt, state)
        self.persistence.append_event_locked(
            attempt,
            EventRecord(
                schema_version=EVENT_SCHEMA_VERSION,
                event_id=str(uuid4()),
                attempt_id=state.attempt_id,
                revision=state.revision,
                occurred_at=occurred_at or self._now(),
                name=name,
                outcome="succeeded",
                arguments={},
            ),
        )

    def _recover_missing_event_locked(self, attempt: Path, state: SessionState) -> None:
        """Repair an allowed interrupted state write while holding the attempt lock."""
        self.persistence.recover_missing_state_event_locked(attempt, state, self.clock)

    def _now(self) -> datetime:
        now = self.clock.now()
        if (
            not isinstance(now, datetime)
            or now.tzinfo is None
            or now.utcoffset() != timedelta(0)
        ):
            raise InvalidInputError("clock must return a timezone-aware UTC timestamp")
        return now

    def _require_scorer(self) -> Scorer:
        if self.scorer is None:
            raise InvalidInputError("a scorer is required for test or submit")
        return self.scorer

    @staticmethod
    def _profile(
        mode: Literal["full", "drill"], drill_duration_seconds: int | None
    ) -> ModeProfile:
        if mode == FULL_MODE:
            if drill_duration_seconds is not None:
                raise InvalidInputError("full mode does not accept a drill duration")
            return ModeProfile(FULL_MODE, FULL_PROFILE, FULL_DURATION_SECONDS)
        if mode == DRILL_MODE:
            return ModeProfile(
                DRILL_MODE,
                DRILL_PROFILE,
                DRILL_DEFAULT_DURATION_SECONDS
                if drill_duration_seconds is None
                else drill_duration_seconds,
            )
        raise InvalidInputError("mode must be full or drill")

    @staticmethod
    def _pointer_for(state: SessionState) -> ActivePointer:
        return ActivePointer(ACTIVE_POINTER_SCHEMA_VERSION, state.attempt_id)


__all__ = [
    "LifecycleService",
    "Scorer",
    "SubmissionResult",
    "TimeObservation",
]
