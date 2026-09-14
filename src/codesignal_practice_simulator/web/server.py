"""Standard-library loopback server for the packaged simulator shell."""

from __future__ import annotations

import errno
import secrets
import socket
import threading
import webbrowser
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import quote
import re

from ..application import RuntimeApplication, create_application
from .responses import HttpResponse, encode, failure
from .routes import RouteHandler, is_shell_path
from .security import RequestError, request_path


TokenFactory = Callable[[], str]
BrowserOpener = Callable[[str], object]
ApplicationFactory = Callable[[Path], RuntimeApplication]
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43,}\Z")
_REQUEST_TIMEOUT_SECONDS = 1.0
_EXPECTED_CLIENT_DISCONNECTS = (
    BrokenPipeError,
    ConnectionResetError,
    ConnectionAbortedError,
)
_EXPECTED_CLIENT_DISCONNECT_ERRNOS = frozenset(
    {
        errno.EPIPE,
        errno.ECONNRESET,
        errno.ECONNABORTED,
        errno.ENOTCONN,
    }
)
_PERMISSIONS_POLICY = (
    "accelerometer=(), ambient-light-sensor=(), autoplay=(), battery=(), "
    "bluetooth=(), camera=(), clipboard-read=(), clipboard-write=(), "
    "display-capture=(), document-domain=(), encrypted-media=(), "
    "fullscreen=(), gamepad=(), geolocation=(), gyroscope=(), hid=(), "
    "idle-detection=(), magnetometer=(), microphone=(), midi=(), "
    "navigation-override=(), payment=(), picture-in-picture=(), "
    "publickey-credentials-create=(), publickey-credentials-get=(), "
    "screen-wake-lock=(), serial=(), speaker-selection=(), usb=(), "
    "web-share=(), xr-spatial-tracking=()"
)
_MANAGED_RESPONSE_HEADERS = frozenset(
    {
        "cache-control",
        "connection",
        "content-length",
        "content-security-policy",
        "content-type",
        "cross-origin-resource-policy",
        "date",
        "keep-alive",
        "permissions-policy",
        "referrer-policy",
        "server",
        "transfer-encoding",
        "upgrade",
        "x-content-type-options",
        "x-frame-options",
    }
)


@dataclass(frozen=True, slots=True)
class WebServerConfig:
    """Validated launch choices; the host is deliberately loopback-only."""

    workspace_root: Path
    host: str = "127.0.0.1"
    port: int = 0
    no_open: bool = False
    token: str | None = None
    token_factory: TokenFactory = field(
        default=lambda: secrets.token_urlsafe(32),
        repr=False,
    )
    browser_opener: BrowserOpener = field(default=webbrowser.open, repr=False)
    application_factory: ApplicationFactory = field(
        default=create_application,
        repr=False,
    )

    def __post_init__(self) -> None:
        if self.host != "127.0.0.1":
            raise ValueError("web server host must be 127.0.0.1")
        if isinstance(self.port, bool) or not 0 <= self.port <= 65535:
            raise ValueError("web server port is invalid")
        if "\0" in str(self.workspace_root):
            raise ValueError("workspace root is invalid")
        if self.token is not None:
            _validate_token(self.token)


class WebServer:
    """Own one capability-scoped HTTP server and its lifecycle thread."""

    def __init__(
        self,
        config: WebServerConfig,
        *,
        application: RuntimeApplication | None = None,
    ) -> None:
        self.config = config
        self.application = application
        self._httpd: _SimulatorHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._token: str | None = None
        self._url: str | None = None

    @property
    def port(self) -> int:
        if self._httpd is None:
            return self.config.port
        return int(self._httpd.server_address[1])

    @property
    def token(self) -> str | None:
        return self._token

    @property
    def url(self) -> str | None:
        return self._url

    def start(self) -> str:
        """Bind, start the daemon listener, and return its fragment URL."""
        if self._httpd is not None:
            assert self._url is not None
            return self._url
        application = (
            self.application
            if self.application is not None
            else self.config.application_factory(Path(self.config.workspace_root))
        )
        token = self.config.token or self.config.token_factory()
        _validate_token(token)
        httpd: _SimulatorHTTPServer | None = None
        try:
            httpd = _SimulatorHTTPServer(
                (self.config.host, self.config.port),
                _RequestHandler,
                bind_and_activate=False,
            )
            httpd.server_bind()
            httpd.server_activate()
            origin = f"http://{self.config.host}:{httpd.server_address[1]}"
            httpd.route_handler = RouteHandler(
                application,
                token=token,
                origin=origin,
            )
            url = f"{origin}/#token={quote(token, safe='')}"
            thread = threading.Thread(
                target=httpd.serve_forever,
                name="codesignal-sim-web",
                daemon=True,
            )
            thread.start()
        except Exception:
            if httpd is not None:
                httpd.server_close()
            raise
        self._httpd = httpd
        self._token = token
        self._url = url
        self._thread = thread
        return url

    def open_browser(self) -> None:
        """Open the already-published URL after the caller has displayed it."""
        if not self.config.no_open and self._url is not None:
            self.config.browser_opener(self._url)

    def wait(self) -> None:
        """Block until the listener is stopped, as normal browser mode does."""
        if self._thread is None:
            raise RuntimeError("web server has not started")
        self._thread.join()

    def stop(self) -> None:
        """Stop the listener and release its port and thread."""
        httpd, thread = self._httpd, self._thread
        if httpd is None:
            return
        httpd.shutdown()
        httpd.close_connections()
        httpd.server_close()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=5)
        self._httpd = None
        self._thread = None

    close = stop

    def __enter__(self) -> WebServer:
        self.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.stop()


class _SimulatorHTTPServer(ThreadingHTTPServer):
    daemon_threads = False
    allow_reuse_address = True

    def __init__(self, address, handler_class, *, bind_and_activate: bool = True) -> None:
        self.route_handler: RouteHandler | None = None
        self._connections: set[socket.socket] = set()
        self._connections_lock = threading.Lock()
        super().__init__(
            address,
            handler_class,
            bind_and_activate=bind_and_activate,
        )

    def register_connection(self, connection: socket.socket) -> None:
        with self._connections_lock:
            self._connections.add(connection)

    def unregister_connection(self, connection: socket.socket) -> None:
        with self._connections_lock:
            self._connections.discard(connection)

    def close_connections(self) -> None:
        with self._connections_lock:
            connections = tuple(self._connections)
        for connection in connections:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError as error:
                if not _is_expected_client_disconnect(error):
                    raise
            try:
                connection.close()
            except OSError as error:
                if not _is_expected_client_disconnect(error):
                    raise


class _RequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def handle(self) -> None:
        try:
            super().handle()
        except OSError as error:
            if not _is_expected_client_disconnect(error):
                raise
            self.close_connection = True

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(_REQUEST_TIMEOUT_SECONDS)
        server = self.server
        assert isinstance(server, _SimulatorHTTPServer)
        server.register_connection(self.connection)

    def finish(self) -> None:
        try:
            super().finish()
        except OSError as error:
            if not _is_expected_client_disconnect(error):
                raise
        finally:
            server = self.server
            assert isinstance(server, _SimulatorHTTPServer)
            server.unregister_connection(self.connection)

    def version_string(self) -> str:
        return "codesignal-sim"

    def date_time_string(self, timestamp: float | None = None) -> str:
        return super().date_time_string(timestamp)

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_HEAD(self) -> None:
        self._dispatch("HEAD")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def do_PUT(self) -> None:
        self._dispatch("PUT")

    def do_DELETE(self) -> None:
        self._dispatch("DELETE")

    def do_OPTIONS(self) -> None:
        self._dispatch("OPTIONS")

    def do_TRACE(self) -> None:
        self._dispatch("TRACE")

    def do_CONNECT(self) -> None:
        self._dispatch("CONNECT")

    def do_PATCH(self) -> None:
        self._dispatch("PATCH")

    def _dispatch(self, method: str) -> None:
        server = self.server
        assert isinstance(server, _SimulatorHTTPServer)
        assert server.route_handler is not None
        response = server.route_handler.dispatch(method, self.path, self)
        self._send(response, head=method == "HEAD")

    def _send(self, response: HttpResponse, *, head: bool) -> None:
        try:
            body = response.body if response.body is not None else encode(response)
        except (TypeError, ValueError):
            response = failure(500, "internal_error", "response could not be serialized")
            body = encode(response)
        try:
            self.send_response(response.status)
            self._send_headers(response, len(body))
            self.end_headers()
            if not head:
                self.wfile.write(body)
        except OSError as error:
            if not _is_expected_client_disconnect(error):
                raise
            self.close_connection = True

    def _send_headers(self, response: HttpResponse, body_length: int) -> None:
        """Send managed headers once and preserve validated static headers."""
        self.send_header("Content-Length", str(body_length))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", _PERMISSIONS_POLICY)
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        if response.status >= 400:
            self.send_header("Connection", "close")
            self.close_connection = True
        raw_path = getattr(self, "path", "")
        if raw_path.startswith("/api/"):
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Type", "application/json; charset=utf-8")
        elif response.body is None:
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Type", "application/json; charset=utf-8")
        else:
            for header_name in ("Content-Type", "Cache-Control"):
                for name, value in response.headers.items():
                    if name.lower() == header_name.lower():
                        self.send_header(header_name, value)
                        break
        for name, value in response.headers.items():
            if name.lower() in _MANAGED_RESPONSE_HEADERS:
                continue
            self.send_header(name, value)
        self._send_shell_policy(raw_path)

    def _send_shell_policy(self, raw_path: str) -> None:
        try:
            canonical_path, _query = request_path(raw_path)
        except RequestError:
            canonical_path = ""
        if is_shell_path(canonical_path):
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; font-src 'self' data:; "
                "connect-src 'self'; img-src 'self' data:; object-src 'none'; "
                "worker-src 'self'; child-src 'self'; base-uri 'none'; "
                "frame-ancestors 'none'; form-action 'none'",
            )

    def send_error(
        self,
        code: int,
        message: str | None = None,
        explain: str | None = None,
    ) -> None:
        if code == 501:
            response = failure(
                501,
                "method_not_allowed",
                "request method is not supported",
            )
        else:
            response = failure(code, "invalid_request", "request is invalid")
        self._send(response, head=False)

    def log_message(self, *_args: object) -> None:
        return


def _is_expected_client_disconnect(error: OSError) -> bool:
    return isinstance(error, _EXPECTED_CLIENT_DISCONNECTS) or (
        error.errno in _EXPECTED_CLIENT_DISCONNECT_ERRNOS
    )


__all__ = [
    "ApplicationFactory",
    "BrowserOpener",
    "TokenFactory",
    "WebServer",
    "WebServerConfig",
]


def _validate_token(token: object) -> str:
    if not isinstance(token, str) or _TOKEN_PATTERN.fullmatch(token) is None:
        raise ValueError(
            "web server capability must be URL-safe ASCII with at least 256 bits"
        )
    return token
