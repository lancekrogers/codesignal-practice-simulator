from __future__ import annotations

import json

try:
    from .web_server_test_support import WebServerTestCase
except ImportError:
    from web_server_test_support import WebServerTestCase

from codesignal_practice_simulator.scoring import IsolatedAttemptScorer


class TestWebServerEvaluation(WebServerTestCase):
    def test_isolated_scorer_candidate_failure_returns_fixed_web_evidence(self) -> None:
        attempt_id, etag = self._start_isolated_attempt()
        status, _headers, document = self.request(
            "POST",
            f"/api/test?attempt_id={attempt_id}",
            body={"content": _candidate_source("wrong")},
            origin=self.origin,
            headers={"If-Match": etag},
        )

        self.assertEqual(status, 200)
        practice = document["data"]["practice"]
        self.assertEqual(
            [level["outcome"] for level in practice["levels"]],
            ["passed", "failed", "passed", "passed"],
        )
        self.assertEqual(
            practice["levels"][1]["candidate_output"],
            "The candidate solution did not pass this practice level.",
        )
        self._assert_no_scoring_details(document)

    def test_isolated_scorer_execution_error_returns_fixed_web_evidence(self) -> None:
        attempt_id, etag = self._start_isolated_attempt()
        status, _headers, document = self.request(
            "POST",
            f"/api/test?attempt_id={attempt_id}",
            body={"content": _candidate_source("error")},
            origin=self.origin,
            headers={"If-Match": etag},
        )

        self.assertEqual(status, 200)
        practice = document["data"]["practice"]
        self.assertEqual(
            [level["outcome"] for level in practice["levels"]],
            ["passed", "passed", "error", "passed"],
        )
        self.assertEqual(
            practice["levels"][2]["candidate_error"],
            "The local practice check could not be completed.",
        )
        self._assert_no_scoring_details(document)

    def _start_isolated_attempt(self) -> tuple[str, str]:
        self.application.scorer_factory = (
            lambda definition: IsolatedAttemptScorer(definition).score
        )
        attempt_id, etag = self.start_attempt()
        attempt = self.workspace / "attempts" / attempt_id
        (attempt / "test_simulation.py").write_text(_SCORING_TESTS, encoding="utf-8")
        return attempt_id, etag

    def _assert_no_scoring_details(self, document: object) -> None:
        rendered = json.dumps(document)
        for forbidden in (
            "SCORER_INTERNAL_SENTINEL",
            "/tmp/private",
            ".scoring",
            "run_group.py",
            "test_simulation.py",
        ):
            self.assertNotIn(forbidden, rendered)

    def test_repeat_submit_returns_stored_result_without_rescoring(self) -> None:
        calls = 0

        original = self.application.scorer_factory

        def recording_scorer(definition):
            def score(attempt):
                nonlocal calls
                calls += 1
                return original(definition)(attempt)

            return score

        self.application.scorer_factory = recording_scorer
        attempt_id, etag = self.start_attempt()
        query = f"?attempt_id={attempt_id}"
        first_status, _headers, first = self.request(
            "POST",
            f"/api/submit{query}",
            body={"content": "final\n"},
            origin=self.origin,
            headers={"If-Match": etag},
        )
        repeat_status, _headers, repeat = self.request(
            "POST",
            f"/api/submit{query}",
            body={"content": "must be ignored\n"},
            origin=self.origin,
            headers={"If-Match": "sha256:" + "f" * 64},
        )
        self.assertEqual(first_status, repeat_status, 200)
        self.assertTrue(first["data"]["newly_submitted"])
        self.assertFalse(repeat["data"]["newly_submitted"])
        first["data"]["newly_submitted"] = False
        self.assertEqual(first, repeat)
        self.assertEqual(calls, 1)
        self.assertEqual(
            first["data"]["practice"]["levels"][0]["candidate_output"],
            "The candidate solution did not pass this practice level.",
        )

    def test_default_bound_scorer_returns_typed_safe_practice_evidence(self) -> None:
        from codesignal_practice_simulator.scoring import IsolatedAttemptScorer

        self.application.scorer_factory = (
            lambda definition: IsolatedAttemptScorer(definition).score
        )
        attempt_id, etag = self.start_attempt()
        status, _headers, document = self.request(
            "POST",
            f"/api/test?attempt_id={attempt_id}",
            body={"content": "print('safe')\n"},
            origin=self.origin,
            headers={"If-Match": etag},
        )
        self.assertEqual(status, 200)
        practice = document["data"]["practice"]
        self.assertEqual(len(practice["levels"]), 4)
        self.assertNotIn(".scoring", json.dumps(practice))
        self.assertNotIn("test_simulation.py", json.dumps(practice))


_SCORING_TESTS = """\
import unittest
from simulation import evaluate


class TestSimulateCodingFramework(unittest.TestCase):
    def test_group_1(self):
        self.assertEqual(evaluate(1), "ok")

    def test_group_2(self):
        self.assertEqual(
            evaluate(2),
            "ok",
            "SCORER_INTERNAL_SENTINEL /tmp/private/test_simulation.py",
        )

    def test_group_3(self):
        self.assertEqual(evaluate(3), "ok")

    def test_group_4(self):
        self.assertEqual(evaluate(4), "ok")
"""


def _candidate_source(mode: str) -> str:
    if mode == "error":
        return """\
def evaluate(group):
    if group == 3:
        raise RuntimeError("candidate boom")
    return "ok"
"""
    return """\
def evaluate(group):
    return "wrong" if group == 2 else "ok"
"""

