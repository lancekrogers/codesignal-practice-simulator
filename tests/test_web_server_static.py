"""Static-resource and request-boundary tests for the web server."""

from __future__ import annotations

import http.client
import socket
from unittest.mock import patch

try:
    from .web_server_test_support import TEST_TOKEN, WebServerTestCase
except ImportError:
    from web_server_test_support import TEST_TOKEN, WebServerTestCase

from codesignal_practice_simulator.web.resources import asset_names
from codesignal_practice_simulator.web.server import WebServer, WebServerConfig


class TestWebServerStatic(WebServerTestCase):
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

    def test_static_route_maps_one_read_missing_asset_to_not_found(self) -> None:
        with patch(
            "codesignal_practice_simulator.web.routes.read_asset",
            side_effect=FileNotFoundError("missing"),
        ) as read:
            status, _headers, document = self.request(
                "GET",
                "/index.html",
                token=None,
            )
        self.assertEqual(status, 404)
        self.assertFalse(document["ok"])
        self.assertEqual(read.call_count, 1)

    def test_static_mime_cache_nosniff_and_head_parity(self) -> None:
        font_name = next(name for name in asset_names() if name.endswith(".ttf"))
        expected = {
            "/": ("text/html; charset=utf-8", "no-store"),
            "/app.js": ("text/javascript; charset=utf-8", "no-store"),
            "/styles.css": ("text/css; charset=utf-8", "no-store"),
            f"/{font_name}": ("font/ttf", "public, max-age=31536000, immutable"),
        }
        for path, (media_type, cache_control) in expected.items():
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
                self.assertEqual(
                    response.headers.get_all("Cache-Control"), [cache_control]
                )
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
                "GET", "/api/bootstrap", token=supplied
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
            "DELETE", "/api/bootstrap", token=self.token
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
        with self.assertRaises(OSError):
            with socket.socket() as probe:
                probe.settimeout(1)
                probe.connect(("127.0.0.1", port))

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
            "GET", "/api/bootstrap", token="é" * 43
        )
        self.assertEqual((status, document["error"]["code"]), (401, "unauthorized"))
