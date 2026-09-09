"""Real HTTP boundary tests for the loopback browser transport."""

from __future__ import annotations

import hashlib
import http.client
import json
import socket
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from codesignal_practice_simulator.application import RuntimeApplication
from codesignal_practice_simulator.models import LevelResult, ScoreSummary
from codesignal_practice_simulator.prompts import MAX_PROMPT_BYTES
from codesignal_practice_simulator.web.server import WebServer, WebServerConfig
from codesignal_practice_simulator.workspace import ValidatedFixtureCache

TEST_TOKEN = "test-capability-" + "a" * 32

try:
    from .test_cli import FakeClock, write_fixture_project
except ImportError:
    from test_cli import FakeClock, write_fixture_project


class WebServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.workspace, cache = write_fixture_project(root)
        contract = ValidatedFixtureCache(
            cache,
            {
                path.relative_to(cache).as_posix(): hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
                for path in cache.rglob("*")
                if path.is_file()
            },
        )
        score = ScoreSummary(tuple(LevelResult(level, "failed") for level in range(1, 5)))
        self.application = RuntimeApplication(
            self.workspace,
            clock=FakeClock(),
            cache=contract,
            scorer_factory=lambda _definition: lambda _attempt: score,
        )
        self.server = WebServer(
            WebServerConfig(
                self.workspace,
                no_open=True,
                token=TEST_TOKEN,
            ),
            application=self.application,
        )
        self.url = self.server.start()
        self.token = TEST_TOKEN
        self.origin = f"http://127.0.0.1:{self.server.port}"

    def tearDown(self) -> None:
        self.server.stop()
        self.temporary.cleanup()

    def request(
        self,
        method: str,
        path: str,
        *,
        body: object | None = None,
        token: str | None = TEST_TOKEN,
        origin: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, str], object]:
        request_headers = {} if headers is None else dict(headers)
        payload = None
        if body is not None:
            payload = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
            request_headers.setdefault("Content-Length", str(len(payload)))
        if token is not None:
            request_headers["X-Simulator-Token"] = token
        if origin is not None:
            request_headers["Origin"] = origin
        connection = http.client.HTTPConnection("127.0.0.1", self.server.port, timeout=3)
        connection.request(method, path, body=payload, headers=request_headers)
        response = connection.getresponse()
        raw = response.read()
        result: object = raw
        if response.headers.get("Content-Type", "").startswith("application/json"):
            result = json.loads(raw)
        result_headers = {key.lower(): value for key, value in response.headers.items()}
        connection.close()
        return response.status, result_headers, result

    def start_attempt(self) -> tuple[str, str]:
        status, _headers, document = self.request(
            "POST",
            "/api/attempts",
            body={"mode": "drill", "drill_duration_seconds": 60},
            origin=self.origin,
        )
        self.assertEqual(status, 201)
        data = document["data"]
        attempt_id = data["session"]["attempt_id"]
        etag = data["source"]["etag"]
        return attempt_id, etag

    def raw_request(self, request: bytes) -> bytes:
        connection = socket.create_connection(("127.0.0.1", self.server.port), timeout=3)
        try:
            connection.sendall(request)
            chunks: list[bytes] = []
            while True:
                chunk = connection.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
            return b"".join(chunks)
        finally:
            connection.close()

    def test_bootstrap_and_static_shell_are_read_only_and_headered(self) -> None:
        status, headers, document = self.request("GET", "/api/bootstrap")
        self.assertEqual(status, 200)
        self.assertIsNone(document["data"]["session"])
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(headers["x-content-type-options"], "nosniff")
        self.assertEqual(headers["referrer-policy"], "no-referrer")
        status, headers, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"Practice Simulator", body)
        self.assertIn("frame-ancestors 'none'", headers["content-security-policy"])
        status, _headers, body = self.request("GET", "/../study/README.md", token=None)
        self.assertEqual(status, 404)
        self.assertNotIn(b"study", body)
        status, headers, body = self.request("HEAD", "/styles.css", token=None)
        self.assertEqual((status, body), (200, b""))
        self.assertGreater(int(headers["content-length"]), 0)
        status, _headers, _body = self.request("GET", "/app.js?path=../secret", token=None)
        self.assertEqual(status, 404)

    def test_static_mime_cache_nosniff_and_head_parity(self) -> None:
        expected = {
            "/": "text/html; charset=utf-8",
            "/app.js": "text/javascript; charset=utf-8",
            "/styles.css": "text/css; charset=utf-8",
        }
        for path, media_type in expected.items():
            responses = {}
            for method in ("GET", "HEAD"):
                connection = http.client.HTTPConnection(
                    "127.0.0.1", self.server.port, timeout=3
                )
                connection.request(method, path)
                response = connection.getresponse()
                body = response.read()
                responses[method] = response
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers.get_all("Content-Type"), [media_type])
                self.assertEqual(response.headers.get_all("Cache-Control"), ["no-store"])
                self.assertEqual(
                    response.headers.get_all("X-Content-Type-Options"),
                    ["nosniff"],
                )
                if method == "GET":
                    self.assertGreater(len(body), 0)
                else:
                    self.assertEqual(body, b"")
                connection.close()
            self.assertEqual(
                responses["GET"].headers["Content-Length"],
                responses["HEAD"].headers["Content-Length"],
            )

    def test_capability_origin_method_and_query_boundaries(self) -> None:
        for supplied in (None, "wrong"):
            status, _headers, document = self.request(
                "GET",
                "/api/bootstrap",
                token=supplied,
            )
            self.assertEqual(status, 401)
            self.assertFalse(document["ok"])
        status, _headers, document = self.request(
            "POST",
            "/api/attempts",
            body={},
            token=self.token,
            origin="http://127.0.0.1:9",
        )
        self.assertEqual(status, 403)
        self.assertEqual(document["error"]["code"], "forbidden_origin")
        status, _headers, document = self.request(
            "DELETE",
            "/api/bootstrap",
            token=self.token,
        )
        self.assertEqual(status, 405)
        self.assertEqual(document["error"]["code"], "method_not_allowed")
        for path in (
            "/api/bootstrap?unexpected=1",
            "/api/session?attempt_id=bad",
            "/api/session?attempt_id=00000000-0000-0000-0000-000000000000"
            "&attempt_id=00000000-0000-0000-0000-000000000001",
            "/api/prompts/5?attempt_id=00000000-0000-0000-0000-000000000000",
            "/api/%2e%2e/solution",
        ):
            status, _headers, _document = self.request("GET", path, token=self.token)
            self.assertIn(status, (400, 404, 422))

    def test_encoded_index_alias_keeps_csp_and_unsupported_methods_are_json(self) -> None:
        status, headers, body = self.request("GET", "/%69ndex%2Ehtml", token=None)
        self.assertEqual(status, 200)
        self.assertIn("frame-ancestors 'none'", headers["content-security-policy"])
        self.assertIn(b"Practice Simulator", body)
        for method in ("TRACE", "CONNECT", "BREW"):
            status, headers, document = self.request(
                method, "/api/bootstrap", token=self.token
            )
            self.assertIn(status, (405, 501))
            self.assertEqual(headers["content-type"], "application/json; charset=utf-8")
            self.assertFalse(document["ok"])

    def test_token_validation_and_opener_failure_do_not_leave_listener(self) -> None:
        with self.assertRaises(ValueError):
            WebServerConfig(self.workspace, token="short-token")
        bind_conflict = WebServer(
            WebServerConfig(
                self.workspace,
                port=self.server.port,
                no_open=True,
                token=TEST_TOKEN,
            ),
            application=self.application,
        )
        with self.assertRaises(OSError):
            bind_conflict.start()
        bind_conflict.stop()
        opener_failure = WebServer(
            WebServerConfig(
                self.workspace,
                no_open=False,
                token=TEST_TOKEN,
                browser_opener=lambda _url: (_ for _ in ()).throw(
                    RuntimeError("opener failed")
                ),
            ),
            application=self.application,
        )
        url = opener_failure.start()
        port = opener_failure.port
        self.assertIn(str(port), url)
        with self.assertRaises(RuntimeError):
            opener_failure.open_browser()
        opener_failure.stop()
        with socket.socket() as probe:
            probe.settimeout(1)
            with self.assertRaises(OSError):
                probe.connect(("127.0.0.1", port))

    def test_concurrent_save_test_submit_and_attempt_content_are_isolated(self) -> None:
        first, etag = self.start_attempt()
        second, second_etag = self.start_attempt()
        first_query = f"?attempt_id={first}"
        second_query = f"?attempt_id={second}"

        def save() -> tuple[int, object]:
            return self.request(
                "PUT",
                f"/api/source{first_query}",
                body={"content": "saved concurrently\n"},
                origin=self.origin,
                headers={"If-Match": etag},
            )[0::2]

        def test() -> tuple[int, object]:
            return self.request(
                "POST",
                f"/api/test{first_query}",
                body={"content": "tested concurrently\n"},
                origin=self.origin,
                headers={"If-Match": etag},
            )[0::2]

        with ThreadPoolExecutor(max_workers=2) as workers:
            save_result, test_result = tuple(workers.map(lambda call: call(), (save, test)))
        self.assertEqual(sorted((save_result[0], test_result[0])), [200, 409])
        if test_result[0] == 200:
            self.assertEqual(test_result[1]["data"]["source"]["content"], "tested concurrently\n")

        submit_calls = (
            lambda: self.request(
                "POST",
                f"/api/submit{second_query}",
                body={"content": "final source\n"},
                origin=self.origin,
                headers={"If-Match": second_etag},
            )[2],
            lambda: self.request(
                "POST",
                f"/api/submit{second_query}",
                body={"content": "final source\n"},
                origin=self.origin,
                headers={"If-Match": second_etag},
            )[2],
        )
        with ThreadPoolExecutor(max_workers=2) as workers:
            responses = tuple(workers.map(lambda call: call(), submit_calls))
        self.assertEqual(
            sorted(response["data"]["newly_submitted"] for response in responses),
            [False, True],
        )
        status, _headers, isolated = self.request(
            "GET", f"/api/source{second_query}"
        )
        self.assertEqual(status, 200)
        self.assertEqual(isolated["data"]["content"], "final source\n")

    def test_duplicate_headers_json_keys_and_nonascii_token_are_rejected(self) -> None:
        duplicate = self.raw_request(
            (
                f"GET /api/bootstrap HTTP/1.1\r\nHost: 127.0.0.1:{self.server.port}\r\n"
                f"X-Simulator-Token: {self.token}\r\n"
                f"X-Simulator-Token: {self.token}\r\nConnection: close\r\n\r\n"
            ).encode()
        )
        self.assertIn(b"400", duplicate.split(b"\r\n", 1)[0])
        self.assertIn(b'"code":"invalid_headers"', duplicate)
        duplicate_length = self.raw_request(
            (
                f"POST /api/attempts HTTP/1.1\r\nHost: 127.0.0.1:{self.server.port}\r\n"
                f"X-Simulator-Token: {self.token}\r\nOrigin: {self.origin}\r\n"
                "Content-Type: application/json\r\nContent-Length: 2\r\n"
                "Content-Length: 2\r\nConnection: close\r\n\r\n{}"
            ).encode()
        )
        self.assertIn(b"400", duplicate_length.split(b"\r\n", 1)[0])
        self.assertIn(b'"code":"invalid_headers"', duplicate_length)
        status, _headers, document = self.request(
            "POST",
            "/api/attempts",
            body=b'{"mode":"drill","mode":"full"}',
            origin=self.origin,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual((status, document["error"]["code"]), (400, "invalid_json"))
        status, _headers, document = self.request(
            "GET",
            "/api/bootstrap",
            token="é" * 43,
        )
        self.assertEqual((status, document["error"]["code"]), (401, "unauthorized"))

    def test_bootstrap_surfaces_corrupt_selected_state_but_not_absent_pointer(self) -> None:
        status, _headers, document = self.request("GET", "/api/bootstrap")
        self.assertEqual((status, document["data"]["session"]), (200, None))
        attempts = self.workspace / "attempts"
        attempts.mkdir()
        (attempts / "active.json").write_text("{broken", encoding="utf-8")
        status, _headers, document = self.request("GET", "/api/bootstrap")
        self.assertEqual((status, document["error"]["code"]), (404, "session_unavailable"))

    def test_prompt_read_is_bounded_before_response_serialization(self) -> None:
        attempt_id, _etag = self.start_attempt()
        (self.workspace / "attempts" / attempt_id / "level1.md").write_bytes(
            b"x" * (MAX_PROMPT_BYTES + 1)
        )
        status, _headers, document = self.request(
            "GET", f"/api/prompts/1?attempt_id={attempt_id}"
        )
        self.assertEqual((status, document["error"]["code"]), (404, "session_unavailable"))

    def test_partial_body_shutdown_closes_request_without_waiting_for_client(self) -> None:
        attempt_id, etag = self.start_attempt()
        request = (
            f"POST /api/test?attempt_id={attempt_id} HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{self.server.port}\r\n"
            f"X-Simulator-Token: {self.token}\r\nOrigin: {self.origin}\r\n"
            f"If-Match: {etag}\r\nContent-Type: application/json\r\n"
            "Content-Length: 100000\r\nConnection: keep-alive\r\n\r\n{\"content\":"
        ).encode()
        connection = socket.create_connection(("127.0.0.1", self.server.port), timeout=3)
        connection.sendall(request)
        started = time.monotonic()
        self.server.stop()
        self.assertLess(time.monotonic() - started, 2)
        connection.close()

    def test_restart_rotates_capability_without_losing_selected_attempt(self) -> None:
        attempt_id, _etag = self.start_attempt()
        self.server.stop()
        replacement_token = "replacement-token-" + "b" * 32
        replacement = WebServer(
            WebServerConfig(self.workspace, no_open=True, token=replacement_token),
            application=self.application,
        )
        replacement.start()
        self.server = replacement
        status, _headers, _document = self.request(
            "GET",
            "/api/bootstrap",
            token=self.token,
        )
        self.assertEqual(status, 401)
        status, _headers, document = self.request(
            "GET",
            "/api/bootstrap",
            token=replacement_token,
        )
        self.assertEqual(status, 200)
        self.assertEqual(document["data"]["session"]["attempt_id"], attempt_id)

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

    def test_shutdown_releases_port_and_rejects_unknown_resources(self) -> None:
        port = self.server.port
        status, _headers, _document = self.request("GET", "/not-registered.js", token=None)
        self.assertEqual(status, 404)
        self.server.stop()
        with socket.socket() as probe:
            probe.settimeout(1)
            with self.assertRaises(OSError):
                probe.connect(("127.0.0.1", port))


if __name__ == "__main__":
    unittest.main()
