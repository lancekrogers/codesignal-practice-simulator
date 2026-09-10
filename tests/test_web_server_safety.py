"""State-corruption, bounded-read, and disconnect tests for the web server."""

from __future__ import annotations

import errno
from unittest.mock import Mock

try:
    from .web_server_test_support import WebServerTestCase
except ImportError:
    from web_server_test_support import WebServerTestCase

from codesignal_practice_simulator.prompts import MAX_PROMPT_BYTES
from codesignal_practice_simulator.web.responses import HttpResponse
from codesignal_practice_simulator.web.server import _RequestHandler


class TestWebServerSafety(WebServerTestCase):
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

    def test_invalid_utf8_and_symlinked_source_are_safe_http_failures(self) -> None:
        attempt_id, _etag = self.start_attempt()
        source = self.workspace / "attempts" / attempt_id / "simulation.py"
        source.write_bytes(b"\xff")
        status, _headers, document = self.request(
            "GET", f"/api/source?attempt_id={attempt_id}"
        )
        self.assertEqual((status, document["error"]["code"]), (422, "invalid_input"))
        self.assert_safe_source_failure(document)

        external = self.workspace / "outside-source.py"
        external.write_text("external sentinel\n", encoding="utf-8")
        source.unlink()
        source.symlink_to(external)
        status, _headers, document = self.request(
            "GET", f"/api/source?attempt_id={attempt_id}"
        )
        self.assertEqual((status, document["error"]["code"]), (404, "session_unavailable"))
        self.assert_safe_source_failure(document)
        self.assertEqual(external.read_text(encoding="utf-8"), "external sentinel\n")

    def assert_safe_source_failure(self, document: object) -> None:
        self.assertEqual(
            document,
            {
                "schema_version": "web/v1",
                "ok": False,
                "error": {
                    "code": document["error"]["code"],
                    "message": "request values are invalid"
                    if document["error"]["code"] == "invalid_input"
                    else "selected session is unavailable",
                },
            },
        )

    def test_expected_client_disconnects_are_suppressed_but_other_oserrors_raise(
        self,
    ) -> None:
        for error in (
            BrokenPipeError(),
            ConnectionResetError(),
            OSError(errno.EPIPE, "broken pipe"),
        ):
            handler = object.__new__(_RequestHandler)
            handler.close_connection = False
            handler.send_response = Mock(side_effect=error)
            handler._send(HttpResponse(200, {}, {}), head=False)
            self.assertTrue(handler.close_connection)

        handler = object.__new__(_RequestHandler)
        handler.close_connection = False
        handler.send_response = Mock(side_effect=OSError("unexpected socket failure"))
        with self.assertRaisesRegex(OSError, "unexpected socket failure"):
            handler._send(HttpResponse(200, {}, {}), head=False)
