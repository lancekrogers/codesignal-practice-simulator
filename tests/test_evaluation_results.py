from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from codesignal_practice_simulator.evaluation_results import (
    practice_result_from_score,
)
from codesignal_practice_simulator.models import LevelResult, ScoreSummary


def score(*outcomes: str) -> ScoreSummary:
    return ScoreSummary(tuple(
        LevelResult(level, outcome) for level, outcome in enumerate(outcomes, 1)
    ))


class EvaluationResultTests(unittest.TestCase):
    def test_failed_levels_use_fixed_safe_evidence(self) -> None:
        result = practice_result_from_score(
            score("failed", "failed", "failed", "failed"),
        )
        for level in result.levels:
            self.assertEqual(
                level.candidate_output,
                "The candidate solution did not pass this practice level.",
            )
            self.assertIsNone(level.candidate_error)

    def test_passed_levels_have_no_candidate_output(self) -> None:
        result = practice_result_from_score(score("failed", "passed", "passed", "passed"))
        self.assertIsNone(result.levels[1].candidate_output)
        self.assertIsNone(result.levels[1].candidate_error)

    def test_candidate_failure_and_internal_error_have_distinct_safe_shapes(self) -> None:
        result = practice_result_from_score(score("failed", "error", "passed", "passed"))
        self.assertEqual(
            result.levels[0].candidate_output,
            "The candidate solution did not pass this practice level.",
        )
        self.assertEqual(
            result.levels[1].candidate_error,
            "The local practice check could not be completed.",
        )
        self.assertIsNone(result.levels[1].candidate_output)
        self.assertIsNone(result.levels[2].candidate_output)
        self.assertIsNone(result.levels[2].candidate_error)


if __name__ == "__main__":
    unittest.main()

