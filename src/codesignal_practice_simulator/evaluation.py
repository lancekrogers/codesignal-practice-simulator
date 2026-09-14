"""Typed application boundary for scoring and final submission commands."""

from __future__ import annotations

from .errors import CandidateFailureError
from .lifecycle import LifecycleService, SubmissionResult
from .models import SessionRecord


class EvaluationService:
    """Expose lifecycle scoring outcomes without giving CLI code persistence access."""

    def __init__(self, lifecycle: LifecycleService) -> None:
        self.lifecycle = lifecycle

    def test(self, attempt_id: str | None = None) -> SessionRecord:
        """Score one active attempt and return exit-five semantics for non-passes."""
        state = self.lifecycle.test(attempt_id)
        assert state.score is not None
        if state.score.passed_levels != len(state.score.levels):
            raise CandidateFailureError("one or more test groups did not pass")
        return state

    def submit(self, attempt_id: str | None = None) -> SubmissionResult:
        """Finalize one attempt, preserving lifecycle idempotency."""
        return self.lifecycle.submit(attempt_id)


__all__ = ["EvaluationService"]
