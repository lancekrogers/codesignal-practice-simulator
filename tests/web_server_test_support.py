"""Shared HTTP harness for the focused web-server test modules."""

from __future__ import annotations

import hashlib
import http.client
import json
import socket
import sys
import tempfile
from pathlib import Path

import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from codesignal_practice_simulator.application import RuntimeApplication
from codesignal_practice_simulator.models import LevelResult, ScoreSummary
from codesignal_practice_simulator.web.server import WebServer, WebServerConfig
from codesignal_practice_simulator.workspace import ValidatedFixtureCache

try:
    from .test_cli import FakeClock, write_fixture_project
except ImportError:
    from test_cli import FakeClock, write_fixture_project


TEST_TOKEN = "test-capability-" + "a" * 32


class WebServerTestCase(unittest.TestCase):
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
            WebServerConfig(self.workspace, no_open=True, token=TEST_TOKEN),
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
        return data["session"]["attempt_id"], data["source"]["etag"]

    def attempt_directories(self) -> list[Path]:
        attempts = self.workspace / "attempts"
        if not attempts.exists():
            return []
        return sorted(
            path
            for path in attempts.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        )

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
