"""HTTP and CLI exposure of history listing, explicit review, abandon and restart."""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
from uuid import uuid4

from tests.workspace_test_support import tree_snapshot

try:
    from .web_server_test_support import TEST_TOKEN, WebServerTestCase
except ImportError:
    from web_server_test_support import TEST_TOKEN, WebServerTestCase

from codesignal_practice_simulator import cli
from codesignal_practice_simulator.errors import InvalidInputError
from codesignal_practice_simulator.filesystem import LocalFilesystem
from codesignal_practice_simulator.persistence import (
    SUBMISSION_RECOVERY_FILENAME,
    Persistence,
)


class PointerFailFilesystem(LocalFilesystem):
    """Make the restart's pointer publication fail after the journal is durable."""

    def replace(self, source: Path, destination: Path) -> None:
        if destination.name == "active.json":
            raise OSError("injected pointer failure")
        super().replace(source, destination)


class HistoryAndReviewRouteTests(WebServerTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.scorer_calls = 0
        original = self.application.scorer_factory

        def counting_factory(definition):
            scorer = original(definition)

            def score(attempt):
                self.scorer_calls += 1
                return scorer(attempt)

            return score

        self.application.scorer_factory = counting_factory

    # -- helpers ------------------------------------------------------------

    def post(self, path: str, body: object, **kwargs):
        return self.request("POST", path, body=body, origin=self.origin, **kwargs)

    def submit(self, attempt_id: str, etag: str) -> None:
        status, _headers, _document = self.post(
            f"/api/submit?attempt_id={attempt_id}",
            {"content": "def evaluate(group):\n    return 'ok'\n"},
            headers={"If-Match": etag},
        )
        self.assertEqual(status, 200)

    def attempts_snapshot(self):
        return tree_snapshot(self.workspace / "attempts")

    def pointer(self) -> str:
        return json.loads((self.workspace / "attempts" / "active.json").read_text())["attempt_id"]

    # -- listing --------------------------------------------------------------

    def test_listing_is_paginated_filtered_and_read_only(self) -> None:
        first, etag = self.start_attempt()
        self.submit(first, etag)
        second, _etag = self.start_attempt()
        status, _h, ended = self.post(f"/api/attempts/{second}/abandon", {"expected_revision": 0})
        self.assertEqual(status, 200)
        self.assertEqual(ended["data"]["session"]["status"], "abandoned")
        third, _etag = self.start_attempt()
        before = self.attempts_snapshot()
        scorer_before = self.scorer_calls

        # The test clock is fixed, so all three share a creation time and the
        # documented tie-break (UUID descending) decides the order.
        expected_order = sorted((first, second, third), reverse=True)
        expected_status = {first: "submitted", second: "abandoned", third: "active"}

        status, _h, page = self.request("GET", "/api/attempts?limit=2")
        self.assertEqual(status, 200)
        items = page["data"]["items"]
        self.assertEqual([item["attempt_id"] for item in items], expected_order[:2])
        self.assertIsNotNone(page["data"]["next_cursor"])
        status, _h, rest = self.request(
            "GET", f"/api/attempts?limit=2&cursor={page['data']['next_cursor']}"
        )
        self.assertEqual(status, 200)
        self.assertEqual([item["attempt_id"] for item in rest["data"]["items"]], expected_order[2:])
        self.assertIsNone(rest["data"]["next_cursor"])
        for item in items + rest["data"]["items"]:
            self.assertEqual(item["status"], expected_status[item["attempt_id"]])
            self.assertEqual(item["review_available"], item["attempt_id"] == first)
            self.assertNotIn("source", item)
            self.assertNotIn('"content":', json.dumps(item))
            self.assertNotIn("def evaluate", json.dumps(item))
            self.assertNotIn(str(self.workspace), json.dumps(item))

        status, _h, filtered = self.request("GET", "/api/attempts?status=submitted")
        self.assertEqual(status, 200)
        self.assertEqual([item["attempt_id"] for item in filtered["data"]["items"]], [first])

        self.assertEqual(self.attempts_snapshot(), before)
        self.assertEqual(self.pointer(), third)
        self.assertEqual(self.scorer_calls, scorer_before)

    def test_listing_rejects_bad_queries_with_the_cli_message(self) -> None:
        self.start_attempt()
        before = self.attempts_snapshot()
        cases = {
            "unknown filter": ("/api/attempts?newest=1", 400, "invalid_query"),
            "empty value": ("/api/attempts?status=", 400, "invalid_query"),
            "non-decimal limit": ("/api/attempts?limit=ten", 400, "invalid_query"),
            "limit too large": ("/api/attempts?limit=101", 422, "invalid_input"),
            "zero limit": ("/api/attempts?limit=0", 422, "invalid_input"),
            "unknown status": ("/api/attempts?status=paused", 422, "invalid_input"),
            "bad cursor": ("/api/attempts?cursor=garbage", 422, "invalid_input"),
        }
        for label, (path, expected_status, code) in cases.items():
            with self.subTest(case=label):
                status, _h, document = self.request("GET", path)
                self.assertEqual((status, document["error"]["code"]), (expected_status, code))
        # A cursor issued for other filters is the same error, same words, as the CLI.
        status, _h, page = self.request("GET", "/api/attempts?limit=1")
        self.assertEqual(status, 200)
        status, _h, first_page = self.request("GET", "/api/attempts?limit=1")
        cursor = first_page["data"]["next_cursor"]
        self.assertIsNone(cursor)  # one attempt only
        with self.assertRaises(InvalidInputError) as cli_error:
            self.application.list_attempts(cursor="garbage")
        status, _h, document = self.request("GET", "/api/attempts?cursor=garbage")
        self.assertEqual(document["error"]["message"], cli_error.exception.message)
        self.assertEqual(self.attempts_snapshot(), before)
        status, _h, document = self.request("POST", "/api/attempts", body={}, origin=self.origin)
        self.assertEqual(status, 423)  # plain start against the live attempt

    # -- review -----------------------------------------------------------------

    def test_review_of_an_old_attempt_never_selects_or_rescores(self) -> None:
        reviewed, etag = self.start_attempt()
        self.submit(reviewed, etag)
        live, _etag = self.start_attempt()
        before = self.attempts_snapshot()
        scorer_before = self.scorer_calls

        status, _h, document = self.request("GET", f"/api/attempts/{reviewed}/review")
        self.assertEqual(status, 200, document)
        review = document["data"]
        self.assertEqual(review["attempt_id"], reviewed)
        self.assertEqual(review["status"], "submitted")
        self.assertEqual(review["source_binding"], "captured")
        self.assertEqual(review["source"]["content"], "def evaluate(group):\n    return 'ok'\n")
        self.assertEqual(review["assessment"]["content_identity"], "pinned")
        self.assertEqual(review["issues"], [])
        self.assertNotIn(str(self.workspace), json.dumps(review))

        status, _h, metadata_only = self.request(
            "GET", f"/api/attempts/{reviewed}/review?include_source=false"
        )
        self.assertEqual(status, 200)
        self.assertIsNone(metadata_only["data"]["source"])
        self.assertEqual(metadata_only["data"]["score"], review["score"])

        status, _h, unsubmitted = self.request("GET", f"/api/attempts/{live}/review")
        self.assertEqual(status, 200)
        self.assertEqual(unsubmitted["data"]["source_binding"], "not_applicable")

        self.assertEqual(self.attempts_snapshot(), before)
        self.assertEqual(self.pointer(), live)
        self.assertEqual(self.scorer_calls, scorer_before)
        status, _h, bootstrap = self.request("GET", "/api/bootstrap")
        self.assertEqual(status, 200)
        self.assertEqual(bootstrap["data"]["session"]["attempt_id"], live)

    def test_unsafe_ids_and_unknown_actions_are_rejected_before_filesystem_access(self) -> None:
        attempt, _etag = self.start_attempt()
        before = self.attempts_snapshot()
        cases = {
            "not a uuid": (f"/api/attempts/not-a-uuid/review", 422, "invalid_input"),
            "uppercase uuid": (f"/api/attempts/{attempt.upper()}/review", 422, "invalid_input"),
            # Decoded traversal produces extra path segments and is an unknown
            # route before any ID is examined.
            "traversal": ("/api/attempts/..%2F..%2Fsecret/review", 404, "not_found"),
            "unknown action": (f"/api/attempts/{attempt}/delete", 404, "not_found"),
            "too deep": (f"/api/attempts/{attempt}/review/extra", 404, "not_found"),
            "unknown attempt": (f"/api/attempts/{uuid4()}/review", 404, "session_unavailable"),
            "bad include_source": (
                f"/api/attempts/{attempt}/review?include_source=maybe",
                400,
                "invalid_query",
            ),
        }
        for label, (path, expected_status, code) in cases.items():
            with self.subTest(case=label):
                status, _h, document = self.request("GET", path)
                self.assertEqual((status, document["error"]["code"]), (expected_status, code))
                self.assertNotIn(str(self.workspace), json.dumps(document))
        status, _h, document = self.request("POST", f"/api/attempts/{attempt}/review", body={}, origin=self.origin)
        self.assertEqual(status, 405)
        self.assertEqual(self.attempts_snapshot(), before)

    def test_unauthorized_requests_leak_nothing_and_change_nothing(self) -> None:
        attempt, _etag = self.start_attempt()
        before = self.attempts_snapshot()

        status, _h, document = self.request("GET", "/api/attempts", token=None)
        self.assertEqual((status, document["error"]["code"]), (401, "unauthorized"))
        status, _h, document = self.request(
            "GET", f"/api/attempts/{attempt}/review", token="wrong-" + "b" * 32
        )
        self.assertEqual((status, document["error"]["code"]), (401, "unauthorized"))
        status, _h, document = self.request(
            "POST", f"/api/attempts/{attempt}/abandon", body={"expected_revision": 0}
        )
        self.assertEqual((status, document["error"]["code"]), (403, "forbidden_origin"))
        status, _h, document = self.request(
            "POST",
            f"/api/attempts/{attempt}/restart",
            body={"operation_id": str(uuid4()), "expected_revision": 0},
            origin="http://evil.example",
        )
        self.assertEqual((status, document["error"]["code"]), (403, "forbidden_origin"))
        for document_text in (json.dumps(document),):
            self.assertNotIn(attempt, document_text)
            self.assertNotIn(str(self.workspace), document_text)
        self.assertEqual(self.attempts_snapshot(), before)

    # -- actions ----------------------------------------------------------------

    def test_abandon_and_restart_routes_share_the_lifecycle_contract(self) -> None:
        attempt, _etag = self.start_attempt()

        status, _h, stale = self.post(f"/api/attempts/{attempt}/abandon", {"expected_revision": 5})
        self.assertEqual((status, stale["error"]["code"]), (409, "stale_revision"))
        self.assertIn("refresh and retry", stale["error"]["message"])
        for body in ({"expected_revision": -1}, {"expected_revision": "0"}, {}, {"expected_revision": 0, "x": 1}):
            with self.subTest(body=body):
                status, _h, document = self.post(f"/api/attempts/{attempt}/abandon", body)
                self.assertEqual((status, document["error"]["code"]), (422, "invalid_input"))

        status, _h, ended = self.post(f"/api/attempts/{attempt}/abandon", {"expected_revision": 0})
        self.assertEqual(status, 200)
        self.assertTrue(ended["data"]["newly_abandoned"])
        self.assertEqual(ended["data"]["session"]["status"], "abandoned")
        status, _h, again = self.post(f"/api/attempts/{attempt}/abandon", {"expected_revision": 0})
        self.assertEqual((status, again["data"]["newly_abandoned"]), (200, False))
        self.assertEqual(again["data"]["session"], ended["data"]["session"])

        # The ended attempt is still selected, so a plain start is now allowed.
        live, _etag = self.start_attempt()
        operation = str(uuid4())
        status, _h, restarted = self.post(
            f"/api/attempts/{live}/restart",
            {"operation_id": operation, "expected_revision": 0, "mode": "drill", "drill_duration_seconds": 120},
        )
        self.assertEqual(status, 201)
        data = restarted["data"]
        self.assertEqual((data["replayed"], data["old_attempt_id"]), (False, live))
        self.assertEqual(data["session"]["profile"]["duration_seconds"], 120)
        self.assertEqual(data["abandoned_session"]["status"], "abandoned")
        replacement = data["replacement_attempt_id"]
        self.assertEqual(self.pointer(), replacement)

        status, _h, replayed = self.post(
            f"/api/attempts/{live}/restart",
            {"operation_id": operation, "expected_revision": 0, "mode": "drill", "drill_duration_seconds": 120},
        )
        self.assertEqual((status, replayed["data"]["replayed"]), (200, True))
        self.assertEqual(replayed["data"]["replacement_attempt_id"], replacement)
        self.assertIsNone(replayed["data"]["session"])
        status, _h, conflict = self.post(
            f"/api/attempts/{live}/restart",
            {"operation_id": operation, "expected_revision": 0},
        )
        self.assertEqual((status, conflict["error"]["code"]), (409, "operation_conflict"))
        status, _h, terminal = self.post(
            f"/api/attempts/{live}/restart",
            {"operation_id": str(uuid4()), "expected_revision": 1},
        )
        self.assertEqual((status, terminal["error"]["code"]), (423, "lifecycle_locked"))
        invalid_bodies = (
            {"operation_id": "nope", "expected_revision": 0},
            {"operation_id": str(uuid4()), "expected_revision": 0, "mode": "fast"},
            {"operation_id": str(uuid4()), "expected_revision": 0, "drill_duration_seconds": 0},
            {"operation_id": str(uuid4()), "expected_revision": 0, "drill_duration_seconds": 60},
            {"expected_revision": 0},
        )
        for body in invalid_bodies:
            with self.subTest(body=body):
                status, _h, document = self.post(f"/api/attempts/{replacement}/restart", body)
                self.assertEqual((status, document["error"]["code"]), (422, "invalid_input"))
        self.assertEqual(len(self.attempt_directories()), 3)

    def test_pending_states_are_503_over_http_and_retry_replays(self) -> None:
        reviewed, etag = self.start_attempt()
        self.submit(reviewed, etag)
        live, _etag = self.start_attempt()
        attempts = self.workspace / "attempts"
        marker = attempts / reviewed / SUBMISSION_RECOVERY_FILENAME
        marker.write_text("{}", encoding="utf-8")
        status, _h, pending = self.request("GET", f"/api/attempts/{reviewed}/review")
        self.assertEqual((status, pending["error"]["code"]), (503, "review_pending"))
        self.assertNotIn(str(self.workspace), json.dumps(pending))
        marker.unlink()

        failing = Persistence(PointerFailFilesystem())
        working = self.application.workspace.persistence
        self.application.workspace.persistence = failing
        self.application.lifecycle.persistence = failing
        operation = str(uuid4())
        try:
            status, _h, committed = self.post(
                f"/api/attempts/{live}/restart",
                {"operation_id": operation, "expected_revision": 0},
            )
        finally:
            self.application.workspace.persistence = working
            self.application.lifecycle.persistence = working
        self.assertEqual((status, committed["error"]["code"]), (503, "recovery_pending"))
        self.assertIn(operation, committed["error"]["message"])

        # The same operation ID replays the committed restart once storage works.
        status, _h, replayed = self.post(
            f"/api/attempts/{live}/restart",
            {"operation_id": operation, "expected_revision": 0},
        )
        self.assertEqual((status, replayed["data"]["replayed"]), (200, True))
        self.assertEqual(self.pointer(), replayed["data"]["replacement_attempt_id"])

        status, _h, unsafe = self.request("GET", "/api/attempts")
        self.assertEqual(status, 200)
        (attempts / "active.json").unlink()
        attempts.rename(attempts.with_name("attempts-moved"))
        os.symlink(attempts.with_name("attempts-moved"), attempts)
        status, _h, unsafe = self.request("GET", "/api/attempts")
        self.assertEqual((status, unsafe["error"]["code"]), (404, "history_unavailable"))
        self.assertNotIn(str(self.workspace), json.dumps(unsafe))

    # -- CLI parity --------------------------------------------------------------

    def test_cli_history_and_review_call_the_same_services(self) -> None:
        reviewed, etag = self.start_attempt()
        self.submit(reviewed, etag)
        live, _etag = self.start_attempt()
        before = self.attempts_snapshot()

        def run(arguments: list[str]) -> tuple[int, dict[str, object]]:
            output = io.StringIO()
            code = cli.execute(
                [*arguments, "--workspace-root", str(self.workspace), "--json"],
                application_factory=lambda _root: self.application,
                output=output,
            )
            return code, json.loads(output.getvalue())

        newest, oldest = sorted((reviewed, live), reverse=True)  # fixed clock: UUID order
        code, listed = run(["history", "--limit", "1"])
        self.assertEqual(code, 0)
        self.assertEqual(listed["result"]["items"][0]["attempt_id"], newest)
        code, rest = run(["history", "--limit", "1", "--cursor", listed["result"]["next_cursor"]])
        self.assertEqual(code, 0)
        self.assertEqual(rest["result"]["items"][0]["attempt_id"], oldest)
        code, filtered = run(["history", "--status", "submitted", "--assessment", "file_storage"])
        self.assertEqual([item["attempt_id"] for item in filtered["result"]["items"]], [reviewed])

        code, review = run(["review", "--attempt", reviewed])
        self.assertEqual(code, 0)
        self.assertEqual(review["result"]["source_binding"], "captured")
        code, bare = run(["review", "--attempt", reviewed, "--no-source"])
        self.assertIsNone(bare["result"]["source"])
        code, missing = run(["review"])
        self.assertEqual((code, missing["error"]["code"]), (2, "invalid_input"))
        code, bad_cursor = run(["history", "--cursor", "garbage"])
        self.assertEqual((code, bad_cursor["error"]["code"]), (2, "invalid_input"))
        status, _h, http_bad_cursor = self.request("GET", "/api/attempts?cursor=garbage")
        self.assertEqual(http_bad_cursor["error"]["message"], bad_cursor["error"]["message"])
        code, bad_status = run(["history", "--status", "paused"])
        self.assertEqual(code, 2)

        self.assertEqual(self.attempts_snapshot(), before)
        self.assertEqual(self.pointer(), live)
