"""Parser and output boundary for the simulator command-line interface.

This module intentionally owns only command parsing, application-adapter
selection, and rendering.  Lifecycle, persistence, fixture, scoring, and
prompt-reading policies remain in their respective services.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol, TextIO
from uuid import UUID

from . import __version__
from .assessments import AssessmentRegistry, DEFAULT_ASSESSMENT_REGISTRY
from .clock import Clock, UTCClock
from .evaluation import EvaluationService
from .errors import (
    DomainError,
    ExitCode,
    FixtureSetupRequiredError,
    InvalidInputError,
)
from .fixture_setup import FixtureSetupError, populate_runtime_fixture
from .lifecycle import LifecycleService, SubmissionResult, TimeObservation
from .models import ScoreSummary, SessionState
from .prompts import PromptService
from .rendering import AttemptContextService, ContextResult, DerivedStatusService
from .scoring import IsolatedAttemptScorer
from .workspace import ATTEMPTS_DIRECTORY, ValidatedFixtureCache, WorkspaceManager


CLI_SCHEMA_VERSION = "cli/v1"
_DEFAULT_ASSESSMENT = "file_storage"


class CommandApplication(Protocol):
    """Injected application boundary used by thin command handlers."""

    def fetch(self, *, source: Path | None) -> object: ...

    def start(
        self, *, assessment: str, mode: str, drill_duration_seconds: int | None
    ) -> object: ...

    def resume(self, *, attempt_id: str | None) -> object: ...

    def status(self, *, attempt_id: str | None) -> object: ...

    def time(self, *, attempt_id: str | None) -> object: ...

    def task(self, *, attempt_id: str | None, level: int) -> object: ...

    def test(self, *, attempt_id: str | None) -> object: ...

    def submit(self, *, attempt_id: str | None) -> object: ...

    def context(self, *, attempt_id: str | None, output_format: str) -> object: ...


ApplicationFactory = Callable[[Path], CommandApplication]
ResultSerializer = Callable[[object], Mapping[str, object]]


class _Parser(argparse.ArgumentParser):
    """Raise a safe domain error instead of exiting or printing a traceback."""

    def error(self, message: str) -> None:
        raise InvalidInputError(message)


class _SerializationError(Exception):
    """Result serialization failed after an application adapter completed."""


class _RuntimeApplication:
    """Thin production adapter over the registry, workspace, and lifecycle services."""

    def __init__(
        self,
        workspace_root: Path,
        *,
        clock: Clock | None = None,
        registry: AssessmentRegistry = DEFAULT_ASSESSMENT_REGISTRY,
    ) -> None:
        _validate_root(workspace_root, "workspace root")
        resolved_workspace = workspace_root.resolve()
        cache = ValidatedFixtureCache.from_runtime_manifest(resolved_workspace)
        self.workspace = WorkspaceManager(
            resolved_workspace, cache, registry=registry
        )
        self.lifecycle = LifecycleService(
            self.workspace,
            clock or UTCClock(),
            self._score_selected_attempt,
        )
        self.evaluation = EvaluationService(self.lifecycle)
        self.prompts = PromptService(self.workspace)
        self.contexts = AttemptContextService(self.workspace)
        self.derived_status = DerivedStatusService(self.workspace)
        self.registry = registry

    def _score_selected_attempt(self, attempt: Path) -> ScoreSummary:
        """Create an assessment-specific isolated runner from persisted metadata."""
        state = self.workspace.persistence.read_session(attempt)
        definition = self.workspace.definition_for_persisted_session(state)
        return IsolatedAttemptScorer(definition).score(attempt)

    def fetch(self, *, source: Path | None) -> Mapping[str, object]:
        """Populate this workspace's ignored fixture cache from packaged metadata."""
        try:
            cache_root = populate_runtime_fixture(
                self.workspace.workspace_root, source_root=source
            )
        except FixtureSetupError as error:
            raise FixtureSetupRequiredError(
                f"fixture setup is required: {error}"
            ) from error
        return {"fixture_cache": str(cache_root)}

    def start(
        self, *, assessment: str, mode: str, drill_duration_seconds: int | None
    ) -> SessionState:
        definition = self.registry.require(assessment)
        # ``create_attempt`` validates the same complete cache again immediately
        # before it creates any workspace path, closing the validation-to-write gap.
        try:
            self.workspace.cache.validate(self.workspace.filesystem)
        except FixtureSetupRequiredError as error:
            raise FixtureSetupRequiredError(
                f"{error.message}; run "
                "`codesignal-sim fetch --workspace-root "
                f"{self.workspace.workspace_root}`"
            ) from error
        state = self.lifecycle.start(
            definition.metadata,
            mode=mode,  # type: ignore[arg-type]
            drill_duration_seconds=drill_duration_seconds,
        )
        self.derived_status.refresh(state.attempt_id)
        return state

    def resume(self, *, attempt_id: str | None) -> SessionState:
        state = self.lifecycle.resume(attempt_id)
        self.derived_status.refresh(state.attempt_id)
        return state

    def status(self, *, attempt_id: str | None) -> SessionState:
        state = self.lifecycle.status(attempt_id)
        self.derived_status.refresh(state.attempt_id)
        return state

    def time(self, *, attempt_id: str | None) -> TimeObservation:
        observation = self.lifecycle.time(attempt_id)
        self.derived_status.refresh(observation.state.attempt_id)
        return observation

    def task(self, *, attempt_id: str | None, level: int) -> object:
        result = self.prompts.read_prompt(attempt_id=attempt_id, level=level)
        self.derived_status.refresh(result.attempt_id)
        return result

    def test(self, *, attempt_id: str | None) -> SessionState:
        state = self.evaluation.test(attempt_id)
        self.derived_status.refresh(state.attempt_id)
        return state

    def submit(self, *, attempt_id: str | None) -> SubmissionResult:
        result = self.evaluation.submit(attempt_id)
        if result.newly_submitted:
            self.derived_status.refresh(result.state.attempt_id)
        return result

    def context(
        self, *, attempt_id: str | None, output_format: str
    ) -> ContextResult:
        return self.contexts.read(
            attempt_id=attempt_id,
            output_format=output_format,  # type: ignore[arg-type]
        )


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
    return parser


def execute(
    argv: Sequence[str] | None = None,
    *,
    application_factory: ApplicationFactory | None = None,
    serializer: ResultSerializer | None = None,
    output: TextIO | None = None,
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
        application = (application_factory or _default_application)(
            namespace.workspace_root
        )
        result = _dispatch(application, namespace)
        document = _serialize_document(serializer or serialize_result, result)
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
    if isinstance(result, SessionState):
        return {"session": result.to_dict()}
    if isinstance(result, TimeObservation):
        return {
            "session": result.state.to_dict(),
            "observed_at": result.observed_at.isoformat(),
            "elapsed_seconds": result.elapsed_seconds,
            "remaining_seconds": result.remaining_seconds,
        }
    if isinstance(result, SubmissionResult):
        return {"session": result.state.to_dict(), "score": result.score.to_dict()}
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
    if command == "context":
        return application.context(
            attempt_id=namespace.attempt_id,
            output_format=namespace.output_format,
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


def _default_application(workspace_root: Path) -> CommandApplication:
    return _RuntimeApplication(workspace_root)


def _validate_root(path: Path, label: str) -> None:
    """Reject invalid filesystem destinations before any service can mutate them."""
    try:
        resolved = path.resolve()
        if path.exists() and (not path.is_dir() or path.is_symlink()):
            raise InvalidInputError(f"{label} must be a non-symlink directory")
        ancestor = resolved
        while not ancestor.exists() and ancestor != ancestor.parent:
            ancestor = ancestor.parent
        if not ancestor.is_dir():
            raise InvalidInputError(f"{label} parent must be a directory")
        destination = resolved / ATTEMPTS_DIRECTORY
        if destination == resolved or resolved not in destination.parents:
            raise InvalidInputError(f"{label} attempts destination is invalid")
    except OSError as error:
        raise InvalidInputError(f"{label} must be a valid path") from error


def _serialize_document(
    serializer: ResultSerializer, result: object
) -> Mapping[str, object]:
    try:
        document = _success_document(serializer(result))
        json.dumps(document, ensure_ascii=False, sort_keys=True)
        return document
    except (TypeError, ValueError) as error:
        raise _SerializationError from error


def _attempt_id(value: str) -> str:
    try:
        parsed = UUID(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "attempt ID must be a canonical UUID"
        ) from error
    if str(parsed) != value:
        raise argparse.ArgumentTypeError("attempt ID must be a canonical UUID")
    return value


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
    "build_parser",
    "execute",
    "main",
    "serialize_result",
]
