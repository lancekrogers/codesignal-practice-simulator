"""Parser and output boundary for the simulator command-line interface.

This module intentionally owns only command parsing, application-adapter
selection, and rendering.  Lifecycle, persistence, fixture, scoring, and
prompt-reading policies remain in their respective services.
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
import threading
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Literal, Protocol, TextIO
from uuid import UUID, uuid4

from . import __version__
from .application import RuntimeApplication, create_application
from .errors import (
    DomainError,
    ExitCode,
    InvalidInputError,
)
from .lifecycle import (
    AbandonResult,
    RestartResult,
    SubmissionResult,
    TimeObservation,
)
from .models import SessionState, SessionStateV2
from .rendering import ContextResult
from .web.server import WebServer, WebServerConfig


CLI_SCHEMA_VERSION = "cli/v1"
_DEFAULT_ASSESSMENT = "file_storage"


class CommandApplication(Protocol):
    """Injected application boundary used by thin command handlers."""

    def fetch(self, *, source: Path | None) -> object: ...

    def start(
        self,
        *,
        assessment: str,
        mode: Literal["full", "drill"],
        drill_duration_seconds: int | None,
    ) -> object: ...

    def resume(self, *, attempt_id: str | None) -> object: ...

    def status(self, *, attempt_id: str | None) -> object: ...

    def time(self, *, attempt_id: str | None) -> object: ...

    def task(self, *, attempt_id: str | None, level: int) -> object: ...

    def test(self, *, attempt_id: str | None) -> object: ...

    def submit(self, *, attempt_id: str | None) -> object: ...

    def abandon(self, *, attempt_id: str | None, expected_revision: int) -> object: ...

    def restart(
        self,
        *,
        attempt_id: str | None,
        operation_id: str,
        expected_revision: int,
        mode: Literal["full", "drill"] | None,
        drill_duration_seconds: int | None,
    ) -> object: ...

    def context(
        self,
        *,
        attempt_id: str | None,
        output_format: Literal["markdown", "json"],
    ) -> object: ...

    def list_attempts(
        self,
        *,
        filters: Mapping[str, object] | None,
        cursor: str | None,
        limit: int | None,
    ) -> object: ...

    def review(self, *, attempt_id: str, include_source: bool) -> object: ...


ApplicationFactory = Callable[[Path], CommandApplication]
ResultSerializer = Callable[[object], Mapping[str, object]]
WebServerFactory = Callable[[WebServerConfig], WebServer]


class _Parser(argparse.ArgumentParser):
    """Raise a safe domain error instead of exiting or printing a traceback."""

    def error(self, message: str) -> None:
        raise InvalidInputError(message)


class _SerializationError(Exception):
    """Result serialization failed after an application adapter completed."""


def build_parser() -> argparse.ArgumentParser:
    """Build the sole command parser shared by console and module entry points."""
    parser = _Parser(
        prog="codesignal-sim",
        description="CodeSignal Practice Simulator",
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")

    fetch = commands.add_parser("fetch", help="populate the ignored fixture cache")
    _add_common_options(fetch, attempt=False)
    fetch.add_argument(
        "--source",
        type=_workspace_root,
        metavar="PATH",
        help="complete offline tree with the pinned upstream paths",
    )

    start = commands.add_parser("start", help="create a new attempt")
    _add_common_options(start, attempt=False)
    start.add_argument("--assessment", default=_DEFAULT_ASSESSMENT)
    start.add_argument("--mode", choices=("full", "drill"), default="full")
    start.add_argument("--drill-duration-seconds", type=_positive_integer)

    for command, help_text in (
        ("resume", "resume an active attempt"),
        ("status", "show selected attempt status"),
        ("time", "show selected attempt time"),
        ("test", "score selected attempt"),
        ("submit", "submit selected attempt"),
    ):
        subparser = commands.add_parser(command, help=help_text)
        _add_common_options(subparser)

    abandon = commands.add_parser(
        "abandon", help="end the selected active attempt without scoring it"
    )
    _add_common_options(abandon)
    abandon.add_argument(
        "--expected-revision",
        type=_nonnegative_integer,
        required=True,
        metavar="N",
        help="the attempt revision this decision was made against",
    )

    restart = commands.add_parser(
        "restart", help="end the selected active attempt and start a replacement"
    )
    _add_common_options(restart)
    restart.add_argument(
        "--expected-revision",
        type=_nonnegative_integer,
        required=True,
        metavar="N",
        help="the attempt revision this decision was made against",
    )
    restart.add_argument(
        "--operation-id",
        type=_operation_id,
        metavar="UUID",
        help=(
            "idempotency key; repeat it to get the same replacement back "
            "(default: a new UUID, echoed in the result)"
        ),
    )
    restart.add_argument(
        "--mode",
        choices=("full", "drill"),
        help="replacement profile (default: the old attempt's profile)",
    )
    restart.add_argument("--drill-duration-seconds", type=_positive_integer)

    history = commands.add_parser(
        "history", help="list stored attempts from metadata, newest first"
    )
    _add_common_options(history, attempt=False)
    history.add_argument(
        "--status",
        choices=("active", "expired", "submitted", "abandoned"),
        help="only attempts whose effective status matches",
    )
    history.add_argument(
        "--assessment", dest="assessment_id", help="only attempts of this assessment"
    )
    history.add_argument("--cursor", help="next_cursor from a previous page")
    history.add_argument(
        "--limit", type=_positive_integer, help="page size (default 25, max 100)"
    )

    review = commands.add_parser(
        "review", help="show one attempt's stored review without selecting it"
    )
    _add_common_options(review)
    review.add_argument(
        "--no-source",
        dest="include_source",
        action="store_false",
        help="omit the reviewed source text",
    )

    context = commands.add_parser("context", help="show safe selected attempt context")
    _add_common_options(context)
    context.add_argument(
        "--format",
        dest="output_format",
        choices=("markdown", "json"),
        default="markdown",
        help="context representation inside the CLI result (default: markdown)",
    )

    task = commands.add_parser("task", help="show a selected attempt task")
    _add_common_options(task)
    task.add_argument("--level", type=_level, required=True)

    web = commands.add_parser("web", help="serve the local browser assessment")
    _add_common_options(web, attempt=False)
    web.add_argument("--port", type=_port, default=0)
    web.add_argument(
        "--no-open",
        action="store_true",
        help="start the server without opening a browser window",
    )
    return parser


def execute(
    argv: Sequence[str] | None = None,
    *,
    application_factory: ApplicationFactory | None = None,
    serializer: ResultSerializer | None = None,
    output: TextIO | None = None,
    web_server_factory: WebServerFactory | None = None,
) -> int:
    """Execute one parsed command through an injected application adapter."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    output = sys.stdout if output is None else output
    json_requested = "--json" in arguments
    try:
        namespace = build_parser().parse_args(arguments)
        if namespace.command is None:
            raise InvalidInputError("a command is required")
        _validate_arguments(namespace)
        if namespace.command == "web":
            return _execute_web(
                namespace,
                output,
                web_server_factory=web_server_factory,
            )
        selected_application_factory = (
            _default_application
            if application_factory is None
            else application_factory
        )
        application = selected_application_factory(
            namespace.workspace_root
        )
        result = _dispatch(application, namespace)
        selected_serializer = serialize_result if serializer is None else serializer
        document = _serialize_document(selected_serializer, result)
    except DomainError as error:
        _write_document(
            output,
            _error_document(_error_code(error), error.message),
            json_requested=json_requested,
        )
        return int(error.exit_code)
    except _SerializationError:
        _write_document(
            output,
            _error_document("serialization_failed", "could not serialize command result"),
            json_requested=json_requested,
        )
        return int(ExitCode.INVALID_INPUT)
    except Exception:
        _write_document(
            output,
            _error_document("internal_error", "command could not be completed safely"),
            json_requested=json_requested,
        )
        return int(ExitCode.INVALID_INPUT)
    _write_document(output, document, json_requested=namespace.json)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Console-script entry point."""
    try:
        return execute(argv)
    except SystemExit as exit_error:
        return int(exit_error.code) if isinstance(exit_error.code, int) else 0


def serialize_result(result: object) -> Mapping[str, object]:
    """Convert supported typed service results to JSON-safe result documents."""
    if isinstance(result, (SessionState, SessionStateV2)):
        return {"session": result.to_dict()}
    if isinstance(result, TimeObservation):
        return {
            "session": result.state.to_dict(),
            "observed_at": result.observed_at.isoformat(),
            "elapsed_seconds": result.elapsed_seconds,
            "remaining_seconds": result.remaining_seconds,
        }
    if isinstance(result, SubmissionResult):
        return {
            "session": result.state.to_dict(),
            "score": result.score.to_dict(),
            "newly_submitted": result.newly_submitted,
        }
    if isinstance(result, AbandonResult):
        return result.to_dict()
    if isinstance(result, RestartResult):
        return result.to_dict()
    if isinstance(result, ContextResult):
        return result.to_dict()
    if isinstance(result, Mapping):
        return dict(result)
    to_dict = getattr(result, "to_dict", None)
    if callable(to_dict):
        document = to_dict()
        if isinstance(document, Mapping):
            return dict(document)
    raise TypeError("command result has no supported serializer")


def _add_common_options(
    parser: argparse.ArgumentParser, *, attempt: bool = True
) -> None:
    parser.add_argument("--json", action="store_true", help="emit a JSON envelope")
    parser.add_argument(
        "--workspace-root",
        type=_workspace_root,
        default=Path.cwd(),
        metavar="PATH",
        help="workspace root (default: current directory)",
    )
    if attempt:
        parser.add_argument(
            "--attempt",
            dest="attempt_id",
            type=_attempt_id,
            metavar="UUID",
            help="explicit attempt selector; takes precedence over active selection",
        )


def _dispatch(application: CommandApplication, namespace: argparse.Namespace) -> object:
    command = namespace.command
    if command == "fetch":
        return application.fetch(source=namespace.source)
    if command == "start":
        return application.start(
            assessment=namespace.assessment,
            mode=namespace.mode,
            drill_duration_seconds=namespace.drill_duration_seconds,
        )
    if command == "task":
        return application.task(attempt_id=namespace.attempt_id, level=namespace.level)
    if command == "abandon":
        return application.abandon(
            attempt_id=namespace.attempt_id,
            expected_revision=namespace.expected_revision,
        )
    if command == "restart":
        return application.restart(
            attempt_id=namespace.attempt_id,
            operation_id=namespace.operation_id or str(uuid4()),
            expected_revision=namespace.expected_revision,
            mode=namespace.mode,
            drill_duration_seconds=namespace.drill_duration_seconds,
        )
    if command == "context":
        return application.context(
            attempt_id=namespace.attempt_id,
            output_format=namespace.output_format,
        )
    if command == "history":
        filters = {
            key: value
            for key, value in (
                ("status", namespace.status),
                ("assessment_id", namespace.assessment_id),
            )
            if value is not None
        }
        return application.list_attempts(
            filters=filters or None,
            cursor=namespace.cursor,
            limit=namespace.limit,
        )
    if command == "review":
        return application.review(
            attempt_id=namespace.attempt_id,
            include_source=namespace.include_source,
        )
    method = getattr(application, command)
    return method(attempt_id=namespace.attempt_id)


def _validate_arguments(namespace: argparse.Namespace) -> None:
    if (
        namespace.command == "start"
        and namespace.mode == "full"
        and namespace.drill_duration_seconds is not None
    ):
        raise InvalidInputError("full mode does not accept a drill duration")
    if (
        namespace.command == "restart"
        and namespace.mode != "drill"
        and namespace.drill_duration_seconds is not None
    ):
        raise InvalidInputError("a drill duration requires --mode drill")
    if namespace.command == "review" and namespace.attempt_id is None:
        # Review is explicit by design: it never resolves or changes selection.
        raise InvalidInputError("review requires --attempt UUID")


def _default_application(workspace_root: Path) -> RuntimeApplication:
    return create_application(workspace_root)


def _execute_web(
    namespace: argparse.Namespace,
    output: TextIO,
    *,
    web_server_factory: WebServerFactory | None,
) -> int:
    factory = WebServer if web_server_factory is None else web_server_factory
    server = factory(
        WebServerConfig(
            workspace_root=namespace.workspace_root,
            port=namespace.port,
            no_open=namespace.no_open,
        )
    )
    try:
        url = server.start()
        document = _success_document({"url": url, "port": server.port})
        _write_document(output, document, json_requested=namespace.json)
        output.flush()
        if not namespace.no_open:
            open_browser = getattr(server, "open_browser", None)
            if callable(open_browser):
                open_browser()
        server.wait()
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception:
        _write_document(
            output,
            _error_document("internal_error", "web server could not be started safely"),
            json_requested=namespace.json,
        )
        return int(ExitCode.INVALID_INPUT)
    finally:
        # A second Ctrl-C must not interrupt shutdown and leave a traceback or
        # partially released listener. Signal handlers are main-thread only.
        if threading.current_thread() is threading.main_thread():
            previous = signal.signal(signal.SIGINT, signal.SIG_IGN)
            try:
                server.stop()
            finally:
                signal.signal(signal.SIGINT, previous)
        else:
            server.stop()


def _serialize_document(
    serializer: ResultSerializer, result: object
) -> Mapping[str, object]:
    try:
        document = _success_document(serializer(result))
        json.dumps(document, ensure_ascii=False, sort_keys=True)
        return document
    except (TypeError, ValueError) as error:
        raise _SerializationError from error


def _canonical_uuid(value: str, label: str) -> str:
    try:
        parsed = UUID(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"{label} must be a canonical UUID") from error
    if str(parsed) != value:
        raise argparse.ArgumentTypeError(f"{label} must be a canonical UUID")
    return value


def _attempt_id(value: str) -> str:
    return _canonical_uuid(value, "attempt ID")


def _operation_id(value: str) -> str:
    return _canonical_uuid(value, "operation ID")


def _nonnegative_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a non-negative integer") from error
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return parsed


def _workspace_root(value: str) -> Path:
    if not value or "\0" in value:
        raise argparse.ArgumentTypeError("workspace root must be a valid path")
    return Path(value)


def _positive_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer") from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _port(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("port must be between 0 and 65535") from error
    if parsed < 0 or parsed > 65535:
        raise argparse.ArgumentTypeError("port must be between 0 and 65535")
    return parsed


def _level(value: str) -> int:
    level = _positive_integer(value)
    if level not in (1, 2, 3, 4):
        raise argparse.ArgumentTypeError("level must be between 1 and 4")
    return level


def _success_document(result: Mapping[str, object]) -> dict[str, object]:
    return {"schema_version": CLI_SCHEMA_VERSION, "ok": True, "result": dict(result)}


def _error_document(code: str, message: str) -> dict[str, object]:
    return {
        "schema_version": CLI_SCHEMA_VERSION,
        "ok": False,
        "error": {"code": code, "message": message},
    }


def _error_code(error: DomainError) -> str:
    specific = getattr(error, "code", None)
    if isinstance(specific, str) and specific:
        return specific
    return {
        ExitCode.INVALID_INPUT: "invalid_input",
        ExitCode.SESSION_UNAVAILABLE: "session_unavailable",
        ExitCode.ILLEGAL_LIFECYCLE: "illegal_lifecycle",
        ExitCode.CANDIDATE_FAILURE: "candidate_failure",
    }[error.exit_code]


def _write_document(
    output: TextIO, document: Mapping[str, object], *, json_requested: bool
) -> None:
    if json_requested:
        output.write(json.dumps(document, ensure_ascii=False, sort_keys=True) + "\n")
        return
    if document["ok"]:
        output.write(f"[{document['schema_version']}] success\n")
        for key, value in document["result"].items():  # type: ignore[index]
            if key == "context" and isinstance(value, str):
                output.write(f"{key}:\n{value}")
                continue
            if key == "context" and isinstance(value, Mapping):
                rendered = json.dumps(
                    value, ensure_ascii=False, indent=2, sort_keys=True
                )
                output.write(f"{key}:\n{rendered}\n")
                continue
            output.write(f"{key}: {value}\n")
        return
    error: Mapping[str, Any] = document["error"]  # type: ignore[assignment]
    output.write(
        f"[{document['schema_version']}] error ({error['code']}): "
        f"{error['message']}\n"
    )


__all__ = [
    "CLI_SCHEMA_VERSION",
    "ApplicationFactory",
    "CommandApplication",
    "ResultSerializer",
    "WebServerFactory",
    "build_parser",
    "execute",
    "main",
    "serialize_result",
]
