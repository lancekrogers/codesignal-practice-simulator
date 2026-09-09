"""Source mutation, CAS, and submission tests for the web server."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

try:
    from .web_server_test_support import WebServerTestCase
except ImportError:
    from web_server_test_support import WebServerTestCase


class TestWebServerSource(WebServerTestCase):
    def test_source_cas_history_reset_restore_and_content_isolation(self) -> None:
        attempt_id, etag = self.start_attempt()
        query = f"?attempt_id={attempt_id}"
        source = self._read_source(query, etag)
        current = self._save_and_conflict(query, etag)
        self._restore_and_reset(query, current, source)

    def _read_source(self, query: str, etag: str) -> dict[str, object]:
        status, headers, source = self.request("GET", f"/api/source{query}")
        self.assertEqual(status, 200)
        self.assertEqual(headers["etag"], etag)
        return source["data"]

    def _save_and_conflict(self, query: str, etag: str) -> dict[str, object]:
        status, _headers, saved = self.request(
            "PUT",
            f"/api/source{query}",
            body={"content": "candidate-only sentinel\n"},
            origin=self.origin,
            headers={"If-Match": etag},
        )
        self.assertEqual(status, 200)
        current = saved["data"]["source"]
        self.assertEqual(current["content"], "candidate-only sentinel\n")
        status, headers, conflict = self.request(
            "PUT",
            f"/api/source{query}",
            body={"content": "stale\n"},
            origin=self.origin,
            headers={"If-Match": etag},
        )
        self.assertEqual((status, conflict["error"]["code"]), (409, "conflict"))
        self.assertEqual(headers["etag"], current["etag"])
        return current

    def _restore_and_reset(
        self,
        query: str,
        current: dict[str, object],
        source: dict[str, object],
    ) -> None:
        status, _headers, history = self.request("GET", f"/api/source/history{query}")
        self.assertEqual(status, 200)
        snapshot = history["data"]["snapshots"][0]
        self.assertNotIn("candidate-only sentinel", snapshot["content_preview"])
        status, _headers, restored = self.request(
            "POST",
            f"/api/source/restore{query}",
            body={"snapshot_id": snapshot["snapshot_id"]},
            origin=self.origin,
            headers={"If-Match": current["etag"]},
        )
        self.assertEqual(status, 200)
        self.assertNotEqual(restored["data"]["source"]["content"], current["content"])
        status, _headers, reset = self.request(
            "POST",
            f"/api/source/reset{query}",
            body={},
            origin=self.origin,
            headers={"If-Match": restored["data"]["source"]["etag"]},
        )
        self.assertEqual(status, 200)
        self.assertEqual(reset["data"]["source"], source)

    def test_body_validation_and_evaluation_flush(self) -> None:
        attempt_id, etag = self.start_attempt()
        query = f"?attempt_id={attempt_id}"
        self._assert_mutation_validation(query, etag)
        source = self._test_latest_source(query, etag)
        self._assert_submit_is_idempotent(query, source)
        self._assert_oversized_body(query)

    def _assert_mutation_validation(self, query: str, etag: str) -> None:
        status, _headers, document = self.request(
            "PUT",
            f"/api/source{query}",
            body={"content": "missing origin\n"},
            headers={"If-Match": etag},
        )
        self.assertEqual(status, 403)
        status, _headers, document = self.request(
            "PUT",
            f"/api/source{query}",
            body={"content": "bad fields\n", "extra": True},
            origin=self.origin,
            headers={"If-Match": etag},
        )
        self.assertEqual((status, document["error"]["code"]), (422, "invalid_input"))
        status, _headers, document = self.request(
            "PUT",
            f"/api/source{query}",
            body={"content": "bad etag\n"},
            origin=self.origin,
            headers={"If-Match": "sha256:" + "0" * 64},
        )
        self.assertEqual(status, 409)

    def _test_latest_source(self, query: str, etag: str) -> dict[str, object]:
        status, _headers, document = self.request(
            "POST",
            f"/api/test{query}",
            body={"content": "latest source\n"},
            origin=self.origin,
            headers={"If-Match": etag},
        )
        self.assertEqual(status, 200)
        self.assertEqual(document["data"]["source"]["content"], "latest source\n")
        self.assertEqual(document["data"]["score"]["passed_levels"], 0)
        return document["data"]["source"]

    def _assert_submit_is_idempotent(
        self,
        query: str,
        source: dict[str, object],
    ) -> None:
        status, _headers, submitted = self.request(
            "POST",
            f"/api/submit{query}",
            body={"content": "repeat source is ignored after finality\n"},
            origin=self.origin,
            headers={"If-Match": source["etag"]},
        )
        self.assertEqual(status, 200)
        status, _headers, repeated = self.request(
            "POST",
            f"/api/submit{query}",
            body={"content": "different source must not replace final state\n"},
            origin=self.origin,
            headers={"If-Match": "sha256:" + "f" * 64},
        )
        self.assertEqual(status, 200)
        self.assertEqual(submitted["data"]["newly_submitted"], True)
        self.assertEqual(repeated["data"]["newly_submitted"], False)
        submitted["data"]["newly_submitted"] = repeated["data"]["newly_submitted"]
        self.assertEqual(repeated, submitted)

    def _assert_oversized_body(self, query: str) -> None:
        status, _headers, document = self.request(
            "POST",
            f"/api/test{query}",
            body=b"",
            origin=self.origin,
            headers={
                "If-Match": "sha256:" + "0" * 64,
                "Content-Length": str(256 * 1024 + 1),
            },
        )
        self.assertEqual(status, 413)
        self.assertEqual(document["error"]["code"], "body_too_large")

    def test_malformed_body_and_concurrent_cas_requests_are_bounded(self) -> None:
        attempt_id, etag = self.start_attempt()
        query = f"?attempt_id={attempt_id}"
        cases = (
            (b"{bad", {"Content-Type": "application/json"}, 400),
            (b'"scalar"', {"Content-Type": "application/json"}, 422),
            (b"{}", {"Content-Type": "text/plain"}, 400),
        )
        for raw, headers, expected in cases:
            status, _response_headers, _document = self.request(
                "PUT",
                f"/api/source{query}",
                body=raw,
                origin=self.origin,
                headers={"If-Match": etag, **headers},
            )
            self.assertEqual(status, expected)

        def save(content: str) -> int:
            status, _headers, _document = self.request(
                "PUT",
                f"/api/source{query}",
                body={"content": content},
                origin=self.origin,
                headers={"If-Match": etag},
            )
            return status

        with ThreadPoolExecutor(max_workers=2) as workers:
            statuses = sorted(workers.map(save, ("winner-a\n", "winner-b\n")))
        self.assertEqual(statuses[0], 200)
        self.assertIn(statuses[1], (409, 423))
