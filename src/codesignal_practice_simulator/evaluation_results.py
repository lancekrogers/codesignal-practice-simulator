"""Safe, bounded browser-facing evidence from local practice evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .models import ScoreSummary

FAILED_EVIDENCE = "The candidate solution did not pass this practice level."
ERROR_EVIDENCE = "The local practice check could not be completed."


@dataclass(frozen=True, slots=True)
class PracticeLevelResult:
    """Candidate-safe evidence for one local practice group."""

    level: int
    outcome: Literal["passed", "failed", "error"]
    candidate_output: str | None = None
    candidate_error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "level": self.level,
            "outcome": self.outcome,
            "candidate_output": self.candidate_output,
            "candidate_error": self.candidate_error,
        }


@dataclass(frozen=True, slots=True)
class PracticeResult:
    """A complete, bounded view of one local practice evaluation."""

    levels: tuple[PracticeLevelResult, ...]

    def to_dict(self) -> dict[str, object]:
        return {"levels": [level.to_dict() for level in self.levels]}


def practice_result_from_score(score: ScoreSummary) -> PracticeResult:
    """Build fixed, candidate-safe evidence from the score summary."""
    levels = tuple(_level_result(result.level, result.outcome) for result in score.levels)
    return PracticeResult(levels)


def _level_result(level: int, outcome: str) -> PracticeLevelResult:
    if outcome == "failed":
        return PracticeLevelResult(level, "failed", candidate_output=FAILED_EVIDENCE)
    if outcome == "error":
        return PracticeLevelResult(level, "error", candidate_error=ERROR_EVIDENCE)
    return PracticeLevelResult(level, "passed")


__all__ = [
    "ERROR_EVIDENCE",
    "FAILED_EVIDENCE",
    "PracticeLevelResult",
    "PracticeResult",
    "practice_result_from_score",
]
