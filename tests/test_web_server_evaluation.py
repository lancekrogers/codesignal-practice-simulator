from __future__ import annotations

import json
import time

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

    def test_continuous_output_timeout_is_safe_and_does_not_block_time(self) -> None:
        attempt_id, etag = self._start_isolated_attempt(timeout_seconds=0.1)
        started = time.monotonic()
        status, _headers, document = self.request(
            "POST",
            f"/api/test?attempt_id={attempt_id}",
            body={"content": _continuous_output_candidate_source()},
            origin=self.origin,
            headers={"If-Match": etag},
        )
        evaluation_elapsed = time.monotonic() - started

        self.assertEqual(status, 200)
        practice = document["data"]["practice"]
        self.assertEqual(
            [level["outcome"] for level in practice["levels"]],
            ["error", "passed", "passed", "passed"],
        )
        self.assertEqual(
            practice["levels"][0]["candidate_error"],
            "The local practice check could not be completed.",
        )
        self.assertLess(evaluation_elapsed, 1.5)
        self._assert_no_scoring_details(document)

        started = time.monotonic()
        time_status, _headers, _time_document = self.request(
            "GET",
            f"/api/time?attempt_id={attempt_id}",
        )
        self.assertEqual(time_status, 200)
        self.assertLess(time.monotonic() - started, 0.5)

    def _start_isolated_attempt(
        self, *, timeout_seconds: float = 10.0
    ) -> tuple[str, str]:
        self.application.scorer_factory = (
            lambda definition: IsolatedAttemptScorer(
                definition, timeout_seconds=timeout_seconds
            ).score
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


def _continuous_output_candidate_source() -> str:
    return """\
import os
import time


def evaluate(group):
    if group != 1:
        return "ok"
    deadline = time.monotonic() + 2
    marker = (
        "SCORER_" + "INTERNAL_SENTINEL " + "/" + "tmp" + "/" + "private/runtime-output\\n"
    ).encode()
    while time.monotonic() < deadline:
        os.write(1, marker * 64)
    return "ok"
"""

