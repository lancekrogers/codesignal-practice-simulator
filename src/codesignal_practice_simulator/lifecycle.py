"""Application services for deterministic, locked attempt lifecycle changes.

This module owns lifecycle policy.  Command adapters can select a workspace,
call one service method, and render the returned typed data without reading or
writing runtime files themselves.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal
from uuid import uuid4

from .candidate_document_models import CandidateDocumentError
from .candidate_document_storage import read_source, safe_candidate_path
from .clock import Clock
from .errors import (
    IllegalLifecycleError,
    InvalidInputError,
    LiveSelectionError,
    ScoredSourceChangedError,
    SessionCorruptError,
    SessionUnavailableError,
    StaleRevisionError,
)
from .models import (
    ABANDONED,
    ACTIVE,
    ACTIVE_POINTER_SCHEMA_VERSION,
    DRILL_DEFAULT_DURATION_SECONDS,
    DRILL_MODE,
    DRILL_PROFILE,
    END_REASON,
    EXPIRED,
    FULL_DURATION_SECONDS,
    FULL_MODE,
    FULL_PROFILE,
    RESTART_REASON,
    SESSION_SCHEMA_VERSION_V2,
    SUBMITTED,
    ActivePointer,
    AssessmentMetadata,
    ModeProfile,
    PinnedAssessment,
    RestartRequest,
    ReviewRecord,
    ReviewSource,
    ScoreSummary,
    SessionRecord,
    SessionStateV2,
    abandoned_record,
    review_digest,
    session_event,
)
from .workspace import RestartResult, WorkspaceManager


Scorer = Callable[[Path], ScoreSummary]


@dataclass(frozen=True, slots=True)
class TimeObservation:
    """A state snapshot and clock values from one locked observation."""

    state: SessionRecord
    observed_at: datetime
    elapsed_seconds: int
    remaining_seconds: int


@dataclass(frozen=True, slots=True)
class SubmissionResult:
    """The durable final result returned by both first and repeat submissions."""

    state: SessionRecord
    score: ScoreSummary
    newly_submitted: bool = field(default=False, compare=False, repr=False)


@dataclass(frozen=True, slots=True)
class AbandonResult:
    """The durable abandoned record returned by first and repeat abandonments."""

    state: SessionStateV2
    newly_abandoned: bool = field(default=False, compare=False, repr=False)

    def to_dict(self) -> dict[str, object]:
        return {"session": self.state.to_dict(), "newly_abandoned": self.newly_abandoned}


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
    ) -> SessionRecord:
        """Create and select one active attempt with an effective profile."""
        return self._start(assessment, mode, drill_duration_seconds)

    def start_exclusive(
        self,
        assessment: AssessmentMetadata,
        *,
        mode: Literal["full", "drill"] = FULL_MODE,
        drill_duration_seconds: int | None = None,
    ) -> SessionRecord:
        """Create an attempt only when no live attempt is selected (D001).

        This is the plain ``start`` every transport exposes: a selected attempt
        that is still active is never replaced silently. The user resumes it,
        ends it, or restarts it. ``start`` remains the unguarded primitive.
        """
        return self._start(
            assessment,
            mode,
            drill_duration_seconds,
            before_publish=self._reject_live_selection,
        )

    # Kept for callers that predate the shared policy; identical behavior.
    start_web = start_exclusive

    def _start(
        self,
        assessment: AssessmentMetadata,
        mode: Literal["full", "drill"],
        drill_duration_seconds: int | None,
        *,
        before_publish: Callable[[Path, ActivePointer | None], None] | None = None,
    ) -> SessionRecord:
        if not isinstance(assessment, AssessmentMetadata):
            raise InvalidInputError("assessment is invalid")
        profile = self._profile(mode, drill_duration_seconds)
        # A manifest without a pinned version must fail before any mutation.
        pinned = self.workspace.pinned_assessment(assessment)
        started_at = self._now()
        state = SessionStateV2(
            schema_version=SESSION_SCHEMA_VERSION_V2,
            attempt_id=str(uuid4()),
            assessment=pinned,
            profile=profile,
            started_at=started_at,
            deadline_at=started_at + timedelta(seconds=profile.duration_seconds),
            status=ACTIVE,
            revision=0,
        )
        self.workspace.create_attempt(state, before_publish=before_publish)
        return state

    def _reject_live_selection(
        self, attempts: Path, pointer: ActivePointer | None
    ) -> None:
        """Refuse to displace a selected attempt that is still live.

        Only stored status and deadline decide liveness. The selected attempt's
        content version may no longer be installed; that must not make it
        impossible to start anything else, and it must not make an unfinished
        attempt disappear either. The message names the explicit resolutions.
        """
        if pointer is None:
            return
        attempt = attempts / pointer.attempt_id
        if not attempt.is_dir() or attempt.is_symlink():
            raise SessionUnavailableError("selected attempt is unavailable")
        with self.persistence.attempt_lock(attempt):
            state, _recovered = self._read_recovered_session_locked(
                attempt, validate=False
            )
            state, _observed_at = self._expire_if_overdue_locked(attempt, state)
            if state.status == ACTIVE:
                raise LiveSelectionError(
                    "an active attempt is already selected; resume it, or end or "
                    f"restart it first: {state.attempt_id}"
                )

    def select_attempt(self, attempt_id: str | None = None) -> Path:
        """Resolve an explicit attempt before the validated active selection."""
        return self.workspace.resolve_attempt(attempt_id)

    def resume(self, attempt_id: str | None = None) -> SessionRecord:
        """Resume an active attempt and select an explicitly named attempt.

        Selecting a different attempt while the selected one is still live is a
        conflict the user resolves explicitly (end or restart it): legacy
        non-selected active attempts stay discoverable, but never displace live
        work by being named.
        """
        with self.workspace.selected_attempt(attempt_id) as attempt:
            state = self._read_validated_session_locked(attempt)
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
                attempts = self.workspace.attempts_directory
                self._reject_other_live_selection(attempts, state.attempt_id)
                self.persistence.write_active_pointer_locked(
                    attempts, self._pointer_for(state)
                )
            return state

    def _reject_other_live_selection(self, attempts: Path, attempt_id: str) -> None:
        try:
            pointer = self.persistence.read_active_pointer(attempts)
        except SessionCorruptError:
            # An unreadable selector selects nothing; the explicit resume
            # replaces it, which is the only way to repair it.
            return
        if pointer is None or pointer.attempt_id == attempt_id:
            return
        selected = attempts / pointer.attempt_id
        if not selected.is_dir() or selected.is_symlink():
            return
        self._reject_live_selection(attempts, pointer)

    def abandon(
        self,
        attempt_id: str | None = None,
        *,
        expected_revision: int,
        reason: str = END_REASON,
    ) -> AbandonResult:
        """End an active attempt explicitly, exactly once, at a known revision.

        The transition is written ahead and replayed like a submission, so an
        interrupted abandonment (including a session/v1 upgrade) completes on
        the next access. A repeat at the same expected revision returns the
        durable record; a different revision is a stale-state conflict.
        """
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
            raise InvalidInputError("expected revision must be a non-negative integer")
        if expected_revision < 0:
            raise InvalidInputError("expected revision must be a non-negative integer")
        with self.workspace.selected_attempt(attempt_id) as attempt:
            state = self._read_abandonable_session_locked(attempt)
            if state.status == ABANDONED:
                if state.revision != expected_revision + 1:
                    raise StaleRevisionError(
                        "attempt changed since it was read; refresh and retry "
                        f"(expected revision {expected_revision}, current {state.revision})"
                    )
                assert isinstance(state, SessionStateV2)
                return AbandonResult(state=state, newly_abandoned=False)
            if state.status == ACTIVE:
                self._recover_missing_event_locked(attempt, state)
                state, now = self._expire_if_overdue_locked(attempt, state)
            else:
                now = self._now()
            # A terminal state is the more actionable answer than a revision
            # mismatch: refreshing cannot make an expired attempt abandonable.
            if state.status != ACTIVE:
                raise IllegalLifecycleError(
                    f"cannot abandon an attempt in {state.status} state"
                )
            if state.revision != expected_revision:
                raise StaleRevisionError(
                    "attempt changed since it was read; refresh and retry "
                    f"(expected revision {expected_revision}, current {state.revision})"
                )
            abandoned = abandoned_record(state, ended_at=now, reason=reason)
            event = session_event(
                abandoned,
                event_id=str(uuid4()),
                occurred_at=now,
                name="abandoned",
                outcome="succeeded",
                arguments={"reason": reason},
            )
            self.persistence.persist_abandonment_locked(attempt, state, abandoned, event)
            return AbandonResult(state=abandoned, newly_abandoned=True)

    def restart(
        self,
        attempt_id: str | None = None,
        *,
        operation_id: str,
        expected_revision: int,
        assessment: AssessmentMetadata | None = None,
        mode: Literal["full", "drill"] | None = None,
        drill_duration_seconds: int | None = None,
    ) -> RestartResult:
        """Abandon the selected attempt and create its replacement (D001).

        Implicit selection is resolved once, under the workspace lock, and the
        explicit ID is what the journal records. An overdue attempt is expired
        first, so the workspace sees the state a user would. The target defaults
        to the old attempt's assessment and profile and is always pinned to the
        installed content, so a restart after a content update lands on the
        new content while the old record keeps its own identity.
        """
        if mode is None and drill_duration_seconds is not None:
            raise InvalidInputError("a drill duration requires drill mode")
        with self.workspace.selected_attempt(attempt_id) as attempt:
            state = self._read_abandonable_session_locked(attempt)
            if state.status == ACTIVE:
                self._recover_missing_event_locked(attempt, state)
                state, _observed_at = self._expire_if_overdue_locked(attempt, state)
            old_attempt_id = state.attempt_id
            profile = state.profile if mode is None else self._profile(mode, drill_duration_seconds)
            target = (
                self.workspace.registry.require(state.assessment.assessment_id).metadata
                if assessment is None
                else assessment
            )
        # The locks above are released on purpose. The workspace transaction
        # takes workspace -> old attempt -> staging itself; entering it while
        # still holding this attempt lock would invert the project lock order.
        # It re-validates revision and status under its own locks, so anything
        # that changed in between is a conflict, never a lost update.
        pinned = self.workspace.pinned_assessment(target)
        request = RestartRequest(
            operation_id=operation_id,
            old_attempt_id=old_attempt_id,
            expected_revision=expected_revision,
            assessment=pinned,
            profile=profile,
        )
        return self.workspace.restart_attempt(
            request, now=self._now(), reason=RESTART_REASON
        )

    def _read_abandonable_session_locked(self, attempt: Path) -> SessionRecord:
        """Read state for an abandonment; only a legacy record needs the registry.

        A pinned v2 record describes itself, and ending it scores nothing, so an
        uninstalled content version must not trap the user in a live attempt.
        A session/v1 record is interpretable only through today's registry; an
        unknown or changed definition blocks this mutation, never read-only
        history.
        """
        state = self.persistence.read_session(attempt)
        if not (
            isinstance(state, SessionStateV2)
            and isinstance(state.assessment, PinnedAssessment)
        ):
            self.workspace.definition_for_persisted_session(state)
        return state

    def status(self, attempt_id: str | None = None) -> SessionRecord:
        """Observe expiry if needed, then return the authoritative state."""
        with self.workspace.selected_attempt(attempt_id) as attempt:
            state = self._read_validated_session_locked(attempt)
            self._recover_missing_event_locked(attempt, state)
            state, _observed_at = self._expire_if_overdue_locked(attempt, state)
            return state

    def time(self, attempt_id: str | None = None) -> TimeObservation:
        """Observe expiry if needed and return an elapsed/remaining-time view."""
        with self.workspace.selected_attempt(attempt_id) as attempt:
            state = self._read_validated_session_locked(attempt)
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

    def test(self, attempt_id: str | None = None) -> SessionRecord:
        """Score an active attempt and persist its latest complete score."""
        attempt = self.select_attempt(attempt_id)
        with self.persistence.attempt_lock(attempt):
            state, _recovered_submission = self._read_recovered_session_locked(attempt)
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
    ) -> SessionRecord:
        """Persist a scorer-provided result for an active attempt.

        The later isolated scoring service may call this method after producing
        its four-level result without gaining direct persistence access.
        """
        if not isinstance(score, ScoreSummary):
            raise InvalidInputError("score is invalid")
        with self.workspace.selected_attempt(attempt_id) as attempt:
            state = self._read_validated_session_locked(attempt)
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
            state, recovered_submission = self._read_recovered_session_locked(attempt)
            if state.status == SUBMITTED:
                assert state.score is not None
                return SubmissionResult(
                    state=state,
                    score=state.score,
                    newly_submitted=recovered_submission,
                )
            if state.status not in (ACTIVE, EXPIRED):
                raise IllegalLifecycleError(
                    f"cannot submit an attempt in {state.status} state"
                )
            self._recover_missing_event_locked(attempt, state)
            state, _observed_at = self._expire_if_overdue_locked(attempt, state)
            scorer = self._require_scorer()
            # Capture, score, and verify the same bytes inside this attempt lock
            # so the published result is bound to the source it was produced from.
            captured = self._capture_source_locked(attempt, state)
            score = scorer(attempt)
            if not isinstance(score, ScoreSummary):
                raise InvalidInputError("scorer returned an invalid score")
            self._require_unchanged_source_locked(attempt, state, captured)
            submitted_at = self._now()
            revision = state.revision + 1
            review = ReviewRecord.plan(
                state,
                revision=revision,
                submitted_at=submitted_at,
                score=score,
                source=captured,
            )
            changes: dict[str, object] = {}
            if isinstance(state, SessionStateV2):
                changes["review_digest"] = review_digest(review)
            submitted = replace(
                state,
                status=SUBMITTED,
                revision=revision,
                score=score,
                submitted_at=submitted_at,
                **changes,
            )
            self._persist_submission_locked(attempt, state, submitted, review)
            return SubmissionResult(
                state=submitted,
                score=score,
                newly_submitted=True,
            )

    def _capture_source_locked(
        self, attempt: Path, state: SessionRecord
    ) -> ReviewSource | None:
        """Return the exact candidate bytes, or ``None`` when they cannot be read.

        A missing or unreadable source must not block finalization: the deadline
        is authoritative. Absence is recorded honestly instead of guessed at.
        """
        definition = self.workspace.definition_for_persisted_session(state)
        try:
            path = safe_candidate_path(attempt, definition.candidate_filename)
            content = read_source(self.workspace.filesystem, path)
        except CandidateDocumentError:
            return None
        return ReviewSource.capture(definition.candidate_filename, content)

    def _require_unchanged_source_locked(
        self, attempt: Path, state: SessionRecord, captured: ReviewSource | None
    ) -> None:
        """Reject a submission whose source changed while the scorer ran."""
        current = self._capture_source_locked(attempt, state)
        if (None if current is None else current.sha256) != (
            None if captured is None else captured.sha256
        ):
            raise ScoredSourceChangedError(
                "candidate source changed while scoring; submit again"
            )

    def _record_test_result_locked(
        self, attempt: Path, state: SessionRecord, score: ScoreSummary
    ) -> SessionRecord:
        if not isinstance(score, ScoreSummary):
            raise InvalidInputError("score is invalid")
        recorded = replace(state, revision=state.revision + 1, score=score)
        self._persist_transition_locked(attempt, recorded, "tested")
        return recorded

    def _expire_if_overdue_locked(
        self, attempt: Path, state: SessionRecord
    ) -> tuple[SessionRecord, datetime]:
        observed_at = self._now()
        if state.status == ACTIVE and observed_at >= state.deadline_at:
            expired = replace(state, status=EXPIRED, revision=state.revision + 1)
            self._persist_transition_locked(attempt, expired, "expired", observed_at)
            return expired, observed_at
        return state, observed_at

    def _persist_transition_locked(
        self,
        attempt: Path,
        state: SessionRecord,
        name: str,
        occurred_at: datetime | None = None,
    ) -> None:
        event = session_event(
            state,
            event_id=str(uuid4()),
            occurred_at=occurred_at or self._now(),
            name=name,
            outcome="succeeded",
            arguments={},
        )
        self.persistence.write_session_locked(attempt, state)
        self.persistence.append_event_locked(attempt, event)

    def _persist_submission_locked(
        self,
        attempt: Path,
        prior_state: SessionRecord,
        state: SessionRecord,
        review: ReviewRecord | None = None,
    ) -> None:
        """Write ahead the only final lifecycle transition before publishing it."""
        event = session_event(
            state,
            event_id=str(uuid4()),
            occurred_at=state.submitted_at or self._now(),
            name="submitted",
            outcome="succeeded",
            arguments={},
        )
        self.persistence.persist_submission_locked(
            attempt, prior_state, state, event, review
        )

    def _recover_missing_event_locked(
        self, attempt: Path, state: SessionRecord
    ) -> None:
        """Repair an allowed interrupted state write while holding the attempt lock."""
        self.persistence.recover_missing_state_event_locked(attempt, state, self.clock)

    def _read_validated_session_locked(self, attempt: Path) -> SessionRecord:
        """Read state and revalidate its registry reference while the lock is held."""
        state = self.persistence.read_session(attempt)
        self.workspace.definition_for_persisted_session(state)
        return state

    def _read_recovered_session_locked(
        self, attempt: Path, *, validate: bool = True
    ) -> tuple[SessionRecord, bool]:
        """Finish any write-ahead transition before applying command policy."""
        recovered = self.persistence.recover_attempt_locked(attempt)
        state = (
            self._read_validated_session_locked(attempt)
            if validate
            else self.persistence.read_session(attempt)
        )
        return state, recovered is not None

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
    def _pointer_for(state: SessionRecord) -> ActivePointer:
        return ActivePointer(ACTIVE_POINTER_SCHEMA_VERSION, state.attempt_id)


__all__ = [
    "AbandonResult",
    "LifecycleService",
    "RestartResult",
    "Scorer",
    "SubmissionResult",
    "TimeObservation",
]
