"""Attempt lifecycle and concurrency tests for the web server."""

from __future__ import annotations

import json
import socket
import time
from concurrent.futures import ThreadPoolExecutor

try:
    from .web_server_test_support import TEST_TOKEN, WebServerTestCase
except ImportError:
    from web_server_test_support import TEST_TOKEN, WebServerTestCase

from codesignal_practice_simulator.web.server import WebServer, WebServerConfig


class TestWebServerLifecycle(WebServerTestCase):
    def test_concurrent_save_test_submit_and_attempt_content_are_isolated(self) -> None:
        first, etag = self.start_attempt()
        second = self.application.start(
            assessment="file_storage",
            mode="drill",
            drill_duration_seconds=60,
        ).attempt_id
        first_query = f"?attempt_id={first}"
        second_query = f"?attempt_id={second}"
        second_etag = self._source_etag(second_query)

        save_result, test_result = self._run_concurrent_save_and_test(first_query, etag)
        self.assertEqual(sorted((save_result[0], test_result[0])), [200, 409])
        if test_result[0] == 200:
            self.assertEqual(
                test_result[1]["data"]["source"]["content"],
                "tested concurrently\n",
            )

        responses = self._run_concurrent_submissions(second_query, second_etag)
        self.assertEqual(
            sorted(response["data"]["newly_submitted"] for response in responses),
            [False, True],
        )
        status, _headers, isolated = self.request("GET", f"/api/source{second_query}")
        self.assertEqual(status, 200)
        self.assertEqual(isolated["data"]["content"], "final source\n")

    def _source_etag(self, query: str) -> str:
        status, headers, _source = self.request("GET", f"/api/source{query}")
        self.assertEqual(status, 200)
        return headers["etag"]

    def _run_concurrent_save_and_test(
        self, query: str, etag: str
    ) -> tuple[tuple[int, object], tuple[int, object]]:
        calls = (
            lambda: self._save_source(query, etag),
            lambda: self._test_source(query, etag),
        )
        with ThreadPoolExecutor(max_workers=2) as workers:
            return tuple(workers.map(lambda call: call(), calls))

    def _save_source(self, query: str, etag: str) -> tuple[int, object]:
        return self.request(
            "PUT",
            f"/api/source{query}",
            body={"content": "saved concurrently\n"},
            origin=self.origin,
            headers={"If-Match": etag},
        )[0::2]

    def _test_source(self, query: str, etag: str) -> tuple[int, object]:
        return self.request(
            "POST",
            f"/api/test{query}",
            body={"content": "tested concurrently\n"},
            origin=self.origin,
            headers={"If-Match": etag},
        )[0::2]

    def _run_concurrent_submissions(
        self, query: str, etag: str
    ) -> tuple[dict[str, object], dict[str, object]]:
        calls = tuple(
            lambda: self.request(
                "POST",
                f"/api/submit{query}",
                body={"content": "final source\n"},
                origin=self.origin,
                headers={"If-Match": etag},
            )[2]
            for _ in range(2)
        )
        with ThreadPoolExecutor(max_workers=2) as workers:
            return tuple(workers.map(lambda call: call(), calls))

    def test_web_start_persists_one_authoritative_selection_after_confirmation(self) -> None:
        status, _headers, bootstrap = self.request("GET", "/api/bootstrap")
        self.assertEqual((status, bootstrap["data"]["session"]), (200, None))
        self.assertEqual(self.attempt_directories(), [])
        self.assertFalse((self.workspace / "attempts" / "active.json").exists())

        attempt_id, _etag = self.start_attempt()

        directories = self.attempt_directories()
        self.assertEqual([path.name for path in directories], [attempt_id])
        pointer = json.loads(
            (self.workspace / "attempts" / "active.json").read_text(encoding="utf-8")
        )
        self.assertEqual(pointer["attempt_id"], attempt_id)

    def test_concurrent_web_starts_create_one_active_attempt_and_use_lifecycle_envelope(
        self,
    ) -> None:
        def start() -> tuple[int, object]:
            return self.request(
                "POST",
                "/api/attempts",
                body={"mode": "full"},
                origin=self.origin,
            )[0::2]

        with ThreadPoolExecutor(max_workers=2) as workers:
            responses = tuple(workers.map(lambda _item: start(), (1, 2)))

        self.assertEqual(sorted(response[0] for response in responses), [201, 423])
        rejected = next(response[1] for response in responses if response[0] == 423)
        self.assertEqual(rejected["error"]["code"], "lifecycle_locked")
        self.assertEqual(len(self.attempt_directories()), 1)
        pointer = self.application.workspace.persistence.read_active_pointer(
            self.workspace / "attempts"
        )
        self.assertIsNotNone(pointer)
        self.assertEqual(pointer.attempt_id, self.attempt_directories()[0].name)

    def test_web_start_allows_fresh_attempt_after_expiry_or_submission(self) -> None:
        expired_id, _etag = self.start_attempt()
        expired_state = self.application.workspace.persistence.read_session(
            self.workspace / "attempts" / expired_id
        )
        self.application.clock.value = expired_state.deadline_at
        status, _headers, expired_replacement = self.request(
            "POST",
            "/api/attempts",
            body={"mode": "full"},
            origin=self.origin,
        )
        self.assertEqual(status, 201)
        self.assertNotEqual(
            expired_replacement["data"]["session"]["attempt_id"], expired_id
        )

        submitted_id = expired_replacement["data"]["session"]["attempt_id"]
        self.application.submit(attempt_id=submitted_id)
        status, _headers, submitted_replacement = self.request(
            "POST",
            "/api/attempts",
            body={"mode": "drill", "drill_duration_seconds": 60},
            origin=self.origin,
        )
        self.assertEqual(status, 201)
        self.assertNotEqual(
            submitted_replacement["data"]["session"]["attempt_id"], submitted_id
        )

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
        status, _headers, _document = self.request("GET", "/api/bootstrap", token=self.token)
        self.assertEqual(status, 401)
        status, _headers, document = self.request(
            "GET", "/api/bootstrap", token=replacement_token
        )
        self.assertEqual(status, 200)
        self.assertEqual(document["data"]["session"]["attempt_id"], attempt_id)

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

    def test_shutdown_releases_port_and_rejects_unknown_resources(self) -> None:
        port = self.server.port
        status, _headers, _document = self.request("GET", "/not-registered.js", token=None)
        self.assertEqual(status, 404)
        self.server.stop()
        with socket.socket() as probe:
            probe.settimeout(1)
            with self.assertRaises(OSError):
                probe.connect(("127.0.0.1", port))
