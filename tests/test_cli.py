"""Contract tests for the parser and output adapter boundary."""

from __future__ import annotations

import base64
import io
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from codesignal_practice_simulator import cli
from codesignal_practice_simulator.application import RuntimeApplication
from codesignal_practice_simulator.errors import (
    CandidateFailureError,
    IllegalLifecycleError,
    InvalidInputError,
    SessionUnavailableError,
)
from codesignal_practice_simulator.filesystem import LocalFilesystem
from codesignal_practice_simulator.models import (
    FULL_DURATION_SECONDS,
    SUBMITTED,
    LevelResult,
    ScoreSummary,
)
from codesignal_practice_simulator.persistence import (
    SUBMISSION_RECOVERY_FILENAME,
    Persistence,
)
from codesignal_practice_simulator.scoring import IsolatedAttemptScorer
from codesignal_practice_simulator.workspace import CACHE_INPUTS, ValidatedFixtureCache


CANONICAL_ATTEMPT = "123e4567-e89b-12d3-a456-426614174000"
START = datetime(2026, 9, 8, 19, 0, tzinfo=timezone.utc)


class FakeClock:
    def __init__(self, value: datetime = START) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


class FailSubmissionEventPersistenceFilesystem(LocalFilesystem):
    """Leave a marker when both event append and replacement are unavailable."""

    def append_bytes(self, path: Path, data: bytes) -> None:
        if path.name == "events.jsonl":
            raise OSError("injected submission event append failure")
        super().append_bytes(path, data)

    def replace(self, source: Path, destination: Path) -> None:
        if destination.name == "events.jsonl":
            raise OSError("injected submission event replacement failure")
        super().replace(source, destination)


def write_fixture_project(root: Path) -> tuple[Path, Path]:
    """Build an isolated workspace cache accepted by the runtime adapter."""
    project = root / "workspace"
    cache = project / ".cache" / "codesignal-fixtures" / "6aab304"
    contents = {"vendor-readme.md": b"vendor fixture\n"}
    contents.update(
        {
            f"assessment/file_storage/{name}": (
                f"cached {name}\n".encode("utf-8")
                if name.startswith("level")
                else f"cached {name} fixture\n".encode("utf-8")
            )
            for name in CACHE_INPUTS
        }
    )
    fetches = []
    for relative, data in contents.items():
        path = cache.joinpath(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        fetches.append(
            {
                "cache_path": relative,
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    manifest = {
        "fixture_cache_root": ".cache/codesignal-fixtures/6aab304",
        "fetches": fetches,
    }
    manifest_path = project / "docs" / "migration-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return project, cache


def file_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and not path.name.endswith(".lock")
    }


def synthetic_runtime_fixture() -> tuple[dict[str, object], dict[str, bytes]]:
    """Build a wheel-safe complete fixture contract with synthetic bytes only."""
    cache_files = (
        "vendor-readme.md",
        *(f"assessment/file_storage/{name}" for name in CACHE_INPUTS),
    )
    payloads = {
        f"offline/file-{index}.txt": f"synthetic fixture {index}\n".encode("utf-8")
        for index in range(len(cache_files))
    }
    return (
        {
            "fixture_cache_root": ".cache/codesignal-fixtures/synthetic",
            "upstream": {"repository": "example/fixtures", "commit": "offline"},
            "fetches": [
                {
                    "upstream_path": upstream_path,
                    "repository_path": upstream_path,
                    "cache_path": cache_path,
                    "sha256": hashlib.sha256(payloads[upstream_path]).hexdigest(),
                }
                for cache_path, upstream_path in zip(cache_files, payloads)
            ],
        },
        payloads,
    )


def replace_wheel_runtime_manifest(wheel: Path, manifest: dict[str, object]) -> None:
    """Replace only the wheel's first-party manifest and update its RECORD."""
    manifest_member = "codesignal_practice_simulator/resources/fixture-manifest.json"
    manifest_bytes = json.dumps(manifest, sort_keys=True).encode("utf-8")
    with zipfile.ZipFile(wheel) as archive:
        infos = archive.infolist()
        members = {info.filename: archive.read(info.filename) for info in infos}
    record_member = next(name for name in members if name.endswith(".dist-info/RECORD"))
    digest = base64.urlsafe_b64encode(hashlib.sha256(manifest_bytes).digest())
    record_entry = (
        f"{manifest_member},sha256={digest.rstrip(b'=').decode('ascii')},"
        f"{len(manifest_bytes)}"
    )
    record_lines = members[record_member].decode("utf-8").splitlines()
    members[manifest_member] = manifest_bytes
    members[record_member] = (
        "\n".join(
            record_entry if line.startswith(f"{manifest_member},") else line
            for line in record_lines
        )
        + "\n"
    ).encode("utf-8")
    replacement = wheel.with_suffix(".replacement.whl")
    with zipfile.ZipFile(replacement, "w") as archive:
        for info in infos:
            archive.writestr(info, members[info.filename])
    os.replace(replacement, wheel)


class RecordingApplication:
    def __init__(self, result: object | Exception = None) -> None:
        self.result = {"selected": "active"} if result is None else result
        self.calls: list[tuple[str, dict[str, object]]] = []

    def __getattr__(self, command: str):
        def adapter(**arguments: object) -> object:
            self.calls.append((command, arguments))
            if isinstance(self.result, Exception):
                raise self.result
            return self.result

        return adapter


class RecordingWebServer:
    def __init__(self, config) -> None:
        self.config = config
        self.stopped = False

    @property
    def port(self) -> int:
        return 43210

    def start(self) -> str:
        return "http://127.0.0.1:43210/#token=test"

    def wait(self) -> None:
        return

    def stop(self) -> None:
        self.stopped = True


class CliTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "POSIX SIGINT delivery")
    def test_web_cleanup_ignores_repeated_interrupts_and_restores_handler(self) -> None:
        original = signal.getsignal(signal.SIGINT)

        class InterruptedServer(RecordingWebServer):
            def wait(self):
                raise KeyboardInterrupt

            def stop(self):
                os.kill(os.getpid(), signal.SIGINT)
                os.kill(os.getpid(), signal.SIGINT)
                super().stop()

        server = InterruptedServer(None)
        code = cli.execute(
            ["web", "--no-open"], output=io.StringIO(),
            web_server_factory=lambda _config: server,
        )
        self.assertEqual(code, 0)
        self.assertTrue(server.stopped)
        self.assertEqual(signal.getsignal(signal.SIGINT), original)

    def execute(
        self,
        arguments: list[str],
        application: RecordingApplication | None = None,
        **kwargs: object,
    ) -> tuple[int, str]:
        output = io.StringIO()
        application = application or RecordingApplication()
        code = cli.execute(
            arguments,
            application_factory=lambda _root: application,
            output=output,
            **kwargs,
        )
        return code, output.getvalue()

    def test_parser_exposes_the_documented_command_tree_and_common_options(self) -> None:
        parser = cli.build_parser()
        commands = next(
            action for action in parser._actions if action.dest == "command"
        ).choices
        self.assertEqual(
            set(commands),
            {
                "fetch",
                "start",
                "resume",
                "status",
                "time",
                "task",
                "test",
                "submit",
                "context",
                "web",
            },
        )
        for name, command in commands.items():
            options = {option for action in command._actions for option in action.option_strings}
            self.assertTrue({"--json", "--workspace-root"} <= options, name)
            if name in ("fetch", "start", "web"):
                self.assertNotIn("--attempt", options)
            else:
                self.assertIn("--attempt", options)
        context_options = {
            option for action in commands["context"]._actions for option in action.option_strings
        }
        self.assertIn("--format", context_options)

    def test_default_application_uses_the_public_runtime_factory(self) -> None:
        expected = RecordingApplication()
        workspace_root = Path("temporary-workspace")

        with patch.object(cli, "create_application", return_value=expected) as factory:
            self.assertIs(cli._default_application(workspace_root), expected)

        factory.assert_called_once_with(workspace_root)

    def test_web_command_uses_injected_server_and_returns_capability_url(self) -> None:
        created: list[RecordingWebServer] = []

        def factory(config):
            server = RecordingWebServer(config)
            created.append(server)
            return server

        output = io.StringIO()
        code = cli.execute(
            [
                "web",
                "--json",
                "--workspace-root",
                "sandbox",
                "--port",
                "0",
                "--no-open",
            ],
            application_factory=lambda _root: (_ for _ in ()).throw(
                AssertionError("web must not construct the CLI application")
            ),
            output=output,
            web_server_factory=factory,
        )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["result"]["port"], 43210)
        self.assertTrue(created[0].stopped)
        self.assertEqual(created[0].config.host, "127.0.0.1")
        self.assertTrue(created[0].config.no_open)

    def test_console_adapter_and_module_help_are_identical(self) -> None:
        environment = os.environ | {"PYTHONPATH": str(PROJECT / "src")}
        for arguments in (["--help"], ["context", "--help"]):
            with self.subTest(arguments=arguments):
                console_output = io.StringIO()
                with redirect_stdout(console_output):
                    self.assertEqual(cli.main(arguments), 0)

                completed = subprocess.run(
                    [sys.executable, "-m", "codesignal_practice_simulator", *arguments],
                    cwd=PROJECT,
                    env=environment,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(completed.stdout, console_output.getvalue())
                self.assertEqual(completed.stderr, "")

    def test_options_are_parsed_after_the_subcommand_and_attempt_is_forwarded(self) -> None:
        application = RecordingApplication({"attempt_id": CANONICAL_ATTEMPT})
        code, output = self.execute(
            [
                "status",
                "--json",
                "--workspace-root",
                "sandbox",
                "--attempt",
                CANONICAL_ATTEMPT,
            ],
            application,
        )
        self.assertEqual(code, 0)
        self.assertEqual(
            application.calls,
            [("status", {"attempt_id": CANONICAL_ATTEMPT})],
        )
        self.assertEqual(
            json.loads(output),
            {
                "schema_version": "cli/v1",
                "ok": True,
                "result": {"attempt_id": CANONICAL_ATTEMPT},
            },
        )

    def test_explicit_selector_is_forwarded_without_active_pointer_fallback(self) -> None:
        application = RecordingApplication({"selection": "explicit"})
        code, _output = self.execute(
            ["context", "--attempt", CANONICAL_ATTEMPT], application
        )
        self.assertEqual(code, 0)
        self.assertEqual(
            application.calls,
            [
                (
                    "context",
                    {
                        "attempt_id": CANONICAL_ATTEMPT,
                        "output_format": "markdown",
                    },
                )
            ],
        )

    def test_domain_errors_have_stable_json_envelopes_and_exits(self) -> None:
        cases = (
            (InvalidInputError("bad input"), 2, "invalid_input"),
            (SessionUnavailableError("missing session"), 3, "session_unavailable"),
            (IllegalLifecycleError("not allowed"), 4, "illegal_lifecycle"),
            (CandidateFailureError("tests failed"), 5, "candidate_failure"),
        )
        for error, exit_code, error_code in cases:
            with self.subTest(error=error_code):
                code, output = self.execute(
                    ["status", "--json"], RecordingApplication(error)
                )
                self.assertEqual(code, exit_code)
                self.assertEqual(
                    json.loads(output),
                    {
                        "schema_version": "cli/v1",
                        "ok": False,
                        "error": {"code": error_code, "message": error.message},
                    },
                )

    def test_parse_and_serializer_failures_are_safe_json_input_errors(self) -> None:
        application = RecordingApplication()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = tuple(root.iterdir())
            code, output = self.execute(
                ["status", "--json", "--attempt", "not-a-uuid"], application
            )
            self.assertEqual(code, 2)
            self.assertEqual(application.calls, [])
            self.assertEqual(tuple(root.iterdir()), before)
            self.assertEqual(json.loads(output)["error"]["code"], "invalid_input")

        code, output = self.execute(
            ["start", "--json", "--workspace-root", "\0"], application
        )
        self.assertEqual(code, 2)
        self.assertEqual(application.calls, [])
        self.assertEqual(json.loads(output)["error"]["code"], "invalid_input")

        code, output = self.execute(
            ["status", "--json"],
            RecordingApplication({"unsafe": object()}),
        )
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output)["error"]["code"], "serialization_failed")

    def test_bad_input_does_not_construct_an_application_or_mutate_workspace(self) -> None:
        application = RecordingApplication()
        factory_calls: list[Path] = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = io.StringIO()
            code = cli.execute(
                [
                    "start",
                    "--json",
                    "--workspace-root",
                    str(root),
                    "--mode",
                    "full",
                    "--drill-duration-seconds",
                    "30",
                ],
                application_factory=lambda workspace_root: (
                    factory_calls.append(workspace_root) or application
                ),
                output=output,
            )
            self.assertEqual(code, 2)
            self.assertEqual(tuple(root.iterdir()), ())
        self.assertEqual(factory_calls, [])
        self.assertEqual(application.calls, [])
        self.assertEqual(json.loads(output.getvalue())["error"]["code"], "invalid_input")

    def test_unexpected_adapter_failure_uses_a_safe_internal_error(self) -> None:
        code, output = self.execute(
            ["status", "--json"], RecordingApplication(ValueError("unsafe detail"))
        )
        self.assertEqual(code, 2)
        self.assertEqual(
            json.loads(output)["error"],
            {
                "code": "internal_error",
                "message": "command could not be completed safely",
            },
        )

    def test_human_success_and_error_envelopes_are_versioned(self) -> None:
        code, output = self.execute(["status"], RecordingApplication({"state": "active"}))
        self.assertEqual(code, 0)
        self.assertEqual(output, "[cli/v1] success\nstate: active\n")

        code, output = self.execute(
            ["status"], RecordingApplication(SessionUnavailableError("missing"))
        )
        self.assertEqual(code, 3)
        self.assertEqual(
            output, "[cli/v1] error (session_unavailable): missing\n"
        )


class RuntimeCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.project, self.cache = write_fixture_project(root)
        self.workspace = self.project
        self.clock = FakeClock()
        self.runtime_cache = ValidatedFixtureCache(
            self.cache,
            {
                path.relative_to(self.cache).as_posix(): hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
                for path in self.cache.rglob("*")
                if path.is_file()
            },
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def execute(self, arguments: list[str]) -> tuple[int, dict[str, object]]:
        output = io.StringIO()
        code = cli.execute(
            arguments,
            application_factory=self.runtime_application,
            output=output,
        )
        return code, json.loads(output.getvalue())

    def runtime_application(self, workspace_root: Path) -> RuntimeApplication:
        """Use synthetic fixture bytes while exercising the production adapter."""
        application = RuntimeApplication(workspace_root, clock=self.clock)
        application.workspace.cache = self.runtime_cache
        return application

    @staticmethod
    def session(document: dict[str, object]) -> dict[str, object]:
        return document["result"]["session"]  # type: ignore[index,return-value]

    @staticmethod
    def score(*outcomes: str) -> ScoreSummary:
        return ScoreSummary(
            tuple(
                LevelResult(level, outcome)  # type: ignore[arg-type]
                for level, outcome in enumerate(outcomes, start=1)
            )
        )

    @staticmethod
    def event_names(attempt: Path) -> list[str]:
        return [
            event["name"]
            for event in (
                json.loads(line)
                for line in (attempt / "events.jsonl").read_text(
                    encoding="utf-8"
                ).splitlines()
            )
        ]

    def test_start_uses_project_fixture_cache_and_persists_full_or_drill_profiles(self) -> None:
        cache_before = file_bytes(self.cache)

        code, full_document = self.execute(
            ["start", "--workspace-root", str(self.workspace), "--json"]
        )
        self.assertEqual(code, 0)
        full = self.session(full_document)
        self.assertEqual(full["profile"]["profile_id"], "full-90m")  # type: ignore[index]
        self.assertEqual(full["profile"]["duration_seconds"], FULL_DURATION_SECONDS)  # type: ignore[index]
        self.assertEqual(full["deadline_at"], "2026-09-08T20:30:00+00:00")
        full_attempt = self.workspace / "attempts" / full["attempt_id"]  # type: ignore[operator]

        code, drill_document = self.execute(
            [
                "start",
                "--workspace-root",
                str(self.workspace),
                "--mode",
                "drill",
                "--drill-duration-seconds",
                "73",
                "--json",
            ]
        )
        self.assertEqual(code, 0)
        drill = self.session(drill_document)
        self.assertEqual(drill["profile"], {  # type: ignore[arg-type]
            "mode": "drill",
            "profile_id": "drill-30m",
            "duration_seconds": 73,
        })
        self.assertEqual(file_bytes(self.cache), cache_before)
        self.assertEqual(
            (full_attempt / "simulation.py").read_bytes(),
            b"cached simulation.py fixture\n",
        )

    def test_missing_or_invalid_cache_reports_setup_repair_before_workspace_mutation(self) -> None:
        for mutation in ("missing", "invalid"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                workspace, cache = write_fixture_project(Path(directory))
                if mutation == "missing":
                    cache.rename(cache.with_name("missing-cache"))
                else:
                    (cache / "assessment" / "file_storage" / "level1.md").write_text(
                        "modified cache\n", encoding="utf-8"
                    )
                output = io.StringIO()
                code = cli.execute(
                    ["start", "--workspace-root", str(workspace), "--json"],
                    application_factory=lambda workspace_root: RuntimeApplication(
                        workspace_root, clock=self.clock
                    ),
                    output=output,
                )
                document = json.loads(output.getvalue())
                self.assertEqual(code, 3)
                self.assertEqual(document["error"]["code"], "session_unavailable")  # type: ignore[index]
                self.assertIn("fixture setup is required", document["error"]["message"])  # type: ignore[index]
                self.assertIn("codesignal-sim fetch", document["error"]["message"])  # type: ignore[index]
                self.assertFalse((workspace / "attempts").exists())

    def test_unregistered_persisted_assessment_is_corrupt_in_json_and_human_output(self) -> None:
        started = self.session(
            self.execute(["start", "--workspace-root", str(self.workspace), "--json"])[1]
        )
        attempt = self.workspace / "attempts" / started["attempt_id"]  # type: ignore[operator]
        persisted = json.loads((attempt / "session.json").read_text(encoding="utf-8"))
        persisted["assessment"]["assessment_id"] = "removed_assessment"
        (attempt / "session.json").write_text(json.dumps(persisted), encoding="utf-8")

        code, document = self.execute(
            ["status", "--workspace-root", str(self.workspace), "--json"]
        )
        self.assertEqual(code, 3)
        self.assertEqual(document["error"]["code"], "session_unavailable")  # type: ignore[index]
        self.assertEqual(
            document["error"]["message"], "selected attempt assessment is not registered"  # type: ignore[index]
        )

        output = io.StringIO()
        code = cli.execute(
            ["status", "--workspace-root", str(self.workspace)],
            application_factory=self.runtime_application,
            output=output,
        )
        self.assertEqual(code, 3)
        self.assertEqual(
            output.getvalue(),
            "[cli/v1] error (session_unavailable): "
            "selected attempt assessment is not registered\n",
        )
        self.assertNotIn("Traceback", output.getvalue())

    def test_no_or_corrupt_pointer_is_unavailable_but_explicit_selector_precedes_it(self) -> None:
        code, document = self.execute(
            ["status", "--workspace-root", str(self.workspace), "--json"]
        )
        self.assertEqual(code, 3)
        self.assertIn("no active attempt", document["error"]["message"])  # type: ignore[index]

        first = self.session(
            self.execute(["start", "--workspace-root", str(self.workspace), "--json"])[1]
        )
        second = self.session(
            self.execute(["start", "--workspace-root", str(self.workspace), "--json"])[1]
        )
        first_attempt = self.workspace / "attempts" / first["attempt_id"]  # type: ignore[operator]
        second_attempt = self.workspace / "attempts" / second["attempt_id"]  # type: ignore[operator]
        second_before = file_bytes(second_attempt)
        (self.workspace / "attempts" / "active.json").write_text("{bad", encoding="utf-8")

        code, document = self.execute(
            [
                "status",
                "--workspace-root",
                str(self.workspace),
                "--attempt",
                first["attempt_id"],  # type: ignore[list-item]
                "--json",
            ]
        )
        self.assertEqual(code, 0)
        self.assertEqual(self.session(document)["attempt_id"], first["attempt_id"])
        self.assertEqual(file_bytes(second_attempt), second_before)
        self.assertTrue(first_attempt.exists())

        code, _document = self.execute(
            ["status", "--workspace-root", str(self.workspace), "--json"]
        )
        self.assertEqual(code, 3)

    def test_runtime_lock_contention_returns_exit_four_without_mutation(self) -> None:
        started = self.session(
            self.execute(["start", "--workspace-root", str(self.workspace), "--json"])[1]
        )
        attempt = self.workspace / "attempts" / started["attempt_id"]  # type: ignore[operator]
        before = file_bytes(attempt)
        adapter = self.runtime_application(self.workspace)

        with adapter.workspace.persistence.attempt_lock(attempt):
            code, document = self.execute(
                ["status", "--workspace-root", str(self.workspace), "--json"]
            )

        self.assertEqual(code, 4)
        self.assertEqual(document["error"]["code"], "illegal_lifecycle")  # type: ignore[index]
        self.assertEqual(file_bytes(attempt), before)

    def test_status_and_time_expire_once_and_final_resume_does_not_mutate(self) -> None:
        started = self.session(
            self.execute(["start", "--workspace-root", str(self.workspace), "--json"])[1]
        )
        attempt = self.workspace / "attempts" / started["attempt_id"]  # type: ignore[operator]
        candidate_before = (attempt / "simulation.py").read_bytes()
        cache_before = file_bytes(self.cache)
        self.clock.value = START + timedelta(seconds=FULL_DURATION_SECONDS)

        with patch(
            "codesignal_practice_simulator.rendering.refresh_status",
            side_effect=OSError("status write failed"),
        ):
            code, status = self.execute(
                ["status", "--workspace-root", str(self.workspace), "--json"]
            )
        self.assertEqual(code, 0)
        self.assertEqual(self.session(status)["status"], "expired")
        self.assertEqual(self.session(status)["revision"], 1)
        durable_after_expiry = (
            (attempt / "session.json").read_bytes(),
            (attempt / "events.jsonl").read_bytes(),
        )
        code, elapsed = self.execute(["time", "--workspace-root", str(self.workspace), "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(elapsed["result"]["remaining_seconds"], 0)  # type: ignore[index]
        self.assertEqual(
            (
                (attempt / "session.json").read_bytes(),
                (attempt / "events.jsonl").read_bytes(),
            ),
            durable_after_expiry,
        )
        bytes_after_time = file_bytes(attempt)

        code, document = self.execute(
            ["resume", "--workspace-root", str(self.workspace), "--json"]
        )
        self.assertEqual(code, 4)
        self.assertEqual(document["error"]["code"], "illegal_lifecycle")  # type: ignore[index]
        self.assertEqual(file_bytes(attempt), bytes_after_time)
        self.assertEqual((attempt / "simulation.py").read_bytes(), candidate_before)
        self.assertEqual(file_bytes(self.cache), cache_before)

    def test_submitted_resume_does_not_mutate(self) -> None:
        started = self.session(
            self.execute(["start", "--workspace-root", str(self.workspace), "--json"])[1]
        )
        attempt = self.workspace / "attempts" / started["attempt_id"]  # type: ignore[operator]
        adapter = self.runtime_application(self.workspace)
        state = adapter.workspace.persistence.read_session(attempt)
        submitted = replace(
            state,
            status=SUBMITTED,
            revision=1,
            score=ScoreSummary(tuple(LevelResult(level, "passed") for level in range(1, 5))),
            submitted_at=START,
        )
        adapter.workspace.persistence.write_session(attempt, submitted)
        before = file_bytes(attempt)

        code, document = self.execute(
            ["resume", "--workspace-root", str(self.workspace), "--json"]
        )
        self.assertEqual(code, 4)
        self.assertEqual(document["error"]["code"], "illegal_lifecycle")  # type: ignore[index]
        self.assertEqual(file_bytes(attempt), before)

    def test_runtime_adapter_delegates_derived_status_to_typed_service(self) -> None:
        started = self.session(
            self.execute(["start", "--workspace-root", str(self.workspace), "--json"])[1]
        )
        attempt = self.workspace / "attempts" / started["attempt_id"]  # type: ignore[operator]
        adapter = self.runtime_application(self.workspace)

        with patch.object(
            adapter.workspace.persistence,
            "workspace_lock",
            wraps=adapter.workspace.persistence.workspace_lock,
        ) as workspace_lock, patch.object(
            adapter.workspace.persistence,
            "attempt_lock",
            wraps=adapter.workspace.persistence.attempt_lock,
        ) as attempt_lock:
            adapter.derived_status.refresh(started["attempt_id"])  # type: ignore[arg-type]

        workspace_lock.assert_called_once_with(adapter.workspace.attempts_directory)
        attempt_lock.assert_called_once_with(attempt.resolve())

    def test_task_reads_only_copied_selected_prompt_and_validates_level(self) -> None:
        started = self.session(
            self.execute(["start", "--workspace-root", str(self.workspace), "--json"])[1]
        )
        attempt = self.workspace / "attempts" / started["attempt_id"]  # type: ignore[operator]
        (attempt / "level1.md").write_text("copied prompt only\n", encoding="utf-8")
        candidate_before = (attempt / "simulation.py").read_bytes()
        session_before = (attempt / "session.json").read_bytes()
        events_before = (attempt / "events.jsonl").read_bytes()
        cache_before = file_bytes(self.cache)

        code, document = self.execute(
            ["task", "--workspace-root", str(self.workspace), "--level", "1", "--json"]
        )
        self.assertEqual(code, 0)
        self.assertEqual(document["result"]["prompt"], "copied prompt only\n")  # type: ignore[index]
        self.assertEqual((attempt / "simulation.py").read_bytes(), candidate_before)
        self.assertEqual((attempt / "session.json").read_bytes(), session_before)
        self.assertEqual((attempt / "events.jsonl").read_bytes(), events_before)
        self.assertEqual(file_bytes(self.cache), cache_before)

        (attempt / "level4.md").unlink()
        code, document = self.execute(
            ["task", "--workspace-root", str(self.workspace), "--level", "4", "--json"]
        )
        self.assertEqual(code, 3)
        self.assertIn("selected level is unavailable", document["error"]["message"])  # type: ignore[index]

        code, document = self.execute(
            ["task", "--workspace-root", str(self.workspace), "--level", "0", "--json"]
        )
        self.assertEqual(code, 2)
        self.assertEqual(document["error"]["code"], "invalid_input")  # type: ignore[index]

    def test_test_persists_all_four_outcomes_and_returns_candidate_failure(self) -> None:
        started = self.session(
            self.execute(["start", "--workspace-root", str(self.workspace), "--json"])[1]
        )
        attempt = self.workspace / "attempts" / started["attempt_id"]  # type: ignore[operator]
        expected = self.score("passed", "failed", "error", "passed")

        with patch.object(
            IsolatedAttemptScorer,
            "score",
            return_value=expected,
        ) as score_attempt:
            code, document = self.execute(
                ["test", "--workspace-root", str(self.workspace), "--json"]
            )

        self.assertEqual(code, 5)
        self.assertEqual(document["error"]["code"], "candidate_failure")  # type: ignore[index]
        score_attempt.assert_called_once()
        persisted = json.loads((attempt / "session.json").read_text(encoding="utf-8"))
        self.assertEqual(persisted["score"], expected.to_dict())
        self.assertEqual(persisted["revision"], 1)
        self.assertEqual(self.event_names(attempt), ["started", "tested"])

    def test_test_all_passes_returns_zero_with_isolated_subprocess_score(self) -> None:
        started = self.session(
            self.execute(["start", "--workspace-root", str(self.workspace), "--json"])[1]
        )
        attempt = self.workspace / "attempts" / started["attempt_id"]  # type: ignore[operator]
        (attempt / "simulation.py").write_text(
            "def evaluate(group):\n    return 'ok'\n", encoding="utf-8"
        )
        test_lines = [
            "import unittest",
            "from simulation import evaluate",
            "",
            "class TestSimulateCodingFramework(unittest.TestCase):",
        ]
        for group in range(1, 5):
            test_lines.extend(
                (
                    f"    def test_group_{group}(self):",
                    f"        self.assertEqual(evaluate({group}), 'ok')",
                )
            )
        (attempt / "test_simulation.py").write_text(
            "\n".join(test_lines) + "\n",
            encoding="utf-8",
        )

        code, document = self.execute(
            ["test", "--workspace-root", str(self.workspace), "--json"]
        )

        self.assertEqual(code, 0)
        self.assertEqual(self.session(document)["score"]["passed_levels"], 4)  # type: ignore[index]
        self.assertEqual(self.event_names(attempt), ["started", "tested"])

    def test_expired_test_records_one_expiry_and_never_starts_a_runner(self) -> None:
        started = self.session(
            self.execute(["start", "--workspace-root", str(self.workspace), "--json"])[1]
        )
        attempt = self.workspace / "attempts" / started["attempt_id"]  # type: ignore[operator]
        self.clock.value = START + timedelta(seconds=FULL_DURATION_SECONDS)

        with patch.object(IsolatedAttemptScorer, "score") as score_attempt:
            first_code, first = self.execute(
                ["test", "--workspace-root", str(self.workspace), "--json"]
            )
            bytes_after_first = file_bytes(attempt)
            context_code, context = self.execute(
                [
                    "context",
                    "--workspace-root",
                    str(self.workspace),
                    "--format",
                    "json",
                    "--json",
                ]
            )
            second_code, second = self.execute(
                ["test", "--workspace-root", str(self.workspace), "--json"]
            )

        self.assertEqual((first_code, context_code, second_code), (4, 0, 4))
        self.assertEqual(first["error"]["code"], "illegal_lifecycle")  # type: ignore[index]
        self.assertEqual(second, first)
        self.assertEqual(context["result"]["context"]["lifecycle"]["status"], "expired")  # type: ignore[index]
        score_attempt.assert_not_called()
        self.assertEqual(file_bytes(attempt), bytes_after_first)
        self.assertEqual(self.event_names(attempt), ["started", "expired"])

    def test_submit_is_byte_identical_and_never_rescores_after_finality(self) -> None:
        started = self.session(
            self.execute(["start", "--workspace-root", str(self.workspace), "--json"])[1]
        )
        attempt = self.workspace / "attempts" / started["attempt_id"]  # type: ignore[operator]
        expected = self.score("passed", "failed", "passed", "passed")

        def execute_raw() -> tuple[int, str]:
            output = io.StringIO()
            code = cli.execute(
                ["submit", "--workspace-root", str(self.workspace), "--json"],
                application_factory=self.runtime_application,
                output=output,
            )
            return code, output.getvalue()

        with patch.object(
            IsolatedAttemptScorer,
            "score",
            return_value=expected,
        ) as score_attempt:
            first_code, first = execute_raw()
            bytes_after_first = file_bytes(attempt)
            second_code, second = execute_raw()
            invalid_test_code, invalid_test = self.execute(
                ["test", "--workspace-root", str(self.workspace), "--json"]
            )

        self.assertEqual((first_code, second_code), (0, 0))
        self.assertEqual(invalid_test_code, 4)
        self.assertEqual(invalid_test["error"]["code"], "illegal_lifecycle")  # type: ignore[index]
        first_document = json.loads(first)
        second_document = json.loads(second)
        self.assertTrue(first_document["result"]["newly_submitted"])
        self.assertFalse(second_document["result"]["newly_submitted"])
        first_document["result"]["newly_submitted"] = second_document["result"][
            "newly_submitted"
        ]
        self.assertEqual(first_document, second_document)
        self.assertEqual(file_bytes(attempt), bytes_after_first)
        score_attempt.assert_called_once()
        self.assertEqual(self.event_names(attempt), ["started", "submitted"])
        self.assertEqual(
            json.loads(first)["result"]["score"], expected.to_dict()  # type: ignore[index]
        )

    def test_submit_cli_recovers_a_failed_event_append_without_rescoring_or_touching_neighbors(self) -> None:
        application = self.runtime_application(self.workspace)

        def invoke(arguments: list[str]) -> tuple[int, dict[str, object]]:
            output = io.StringIO()
            code = cli.execute(
                [*arguments, "--workspace-root", str(self.workspace), "--json"],
                application_factory=lambda _workspace_root: application,
                output=output,
            )
            return code, json.loads(output.getvalue())

        started = self.session(invoke(["start"])[1])
        _neighbor = self.session(invoke(["start"])[1])
        attempt = self.workspace / "attempts" / started["attempt_id"]  # type: ignore[operator]
        neighbor = self.workspace / "attempts" / _neighbor["attempt_id"]  # type: ignore[operator]
        candidate_before = (attempt / "simulation.py").read_bytes()
        neighbor_before = file_bytes(neighbor)
        cache_before = file_bytes(self.cache)
        reference = self.project / "reference.md"
        reference.write_text("reference bytes must remain unchanged\n", encoding="utf-8")
        reference_before = reference.read_bytes()
        expected = self.score("passed", "failed", "passed", "passed")
        failing = Persistence(FailSubmissionEventPersistenceFilesystem())
        application.workspace.persistence = failing
        application.lifecycle.persistence = failing

        with patch.object(
            IsolatedAttemptScorer, "score", return_value=expected
        ) as score_attempt:
            failed_code, failed = invoke(["submit", "--attempt", started["attempt_id"]])  # type: ignore[list-item]
            self.assertEqual((failed_code, failed["error"]["code"]), (2, "internal_error"))  # type: ignore[index]
            self.assertEqual(
                json.loads((attempt / "session.json").read_text(encoding="utf-8"))["status"],
                "submitted",
            )
            self.assertEqual(self.event_names(attempt), ["started"])
            self.assertTrue((attempt / SUBMISSION_RECOVERY_FILENAME).is_file())

            recovered_persistence = Persistence()
            application.workspace.persistence = recovered_persistence
            application.lifecycle.persistence = recovered_persistence
            recovered_code, recovered = invoke(
                ["submit", "--attempt", started["attempt_id"]]  # type: ignore[list-item]
            )
            after_recovery = file_bytes(attempt)
            repeated_code, repeated = invoke(
                ["submit", "--attempt", started["attempt_id"]]  # type: ignore[list-item]
            )

        self.assertEqual((recovered_code, repeated_code), (0, 0))
        self.assertTrue(recovered["result"]["newly_submitted"])  # type: ignore[index]
        self.assertFalse(repeated["result"]["newly_submitted"])  # type: ignore[index]
        recovered["result"]["newly_submitted"] = repeated["result"]["newly_submitted"]  # type: ignore[index]
        self.assertEqual(recovered, repeated)
        self.assertEqual(file_bytes(attempt), after_recovery)
        score_attempt.assert_called_once()
        self.assertEqual(self.event_names(attempt), ["started", "submitted"])
        self.assertFalse((attempt / SUBMISSION_RECOVERY_FILENAME).exists())
        self.assertEqual((attempt / "simulation.py").read_bytes(), candidate_before)
        self.assertEqual(file_bytes(neighbor), neighbor_before)
        self.assertEqual(file_bytes(self.cache), cache_before)
        self.assertEqual(reference.read_bytes(), reference_before)

    def test_overdue_submit_expires_then_finalizes_once_and_scoring_error_is_atomic(self) -> None:
        started = self.session(
            self.execute(["start", "--workspace-root", str(self.workspace), "--json"])[1]
        )
        attempt = self.workspace / "attempts" / started["attempt_id"]  # type: ignore[operator]
        self.clock.value = START + timedelta(seconds=FULL_DURATION_SECONDS)
        expected = self.score("passed", "passed", "passed", "passed")

        with patch.object(IsolatedAttemptScorer, "score", return_value=expected):
            code, document = self.execute(
                ["submit", "--workspace-root", str(self.workspace), "--json"]
            )

        self.assertEqual(code, 0)
        self.assertEqual(self.session(document)["status"], SUBMITTED)
        self.assertEqual(self.event_names(attempt), ["started", "expired", "submitted"])

        active = self.session(
            self.execute(["start", "--workspace-root", str(self.workspace), "--json"])[1]
        )
        active_attempt = self.workspace / "attempts" / active["attempt_id"]  # type: ignore[operator]
        active_before = file_bytes(active_attempt)
        adapter = self.runtime_application(self.workspace)
        with patch.object(adapter.lifecycle, "scorer", side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                adapter.submit(attempt_id=active["attempt_id"])  # type: ignore[arg-type]
        self.assertEqual(file_bytes(active_attempt), active_before)
        self.assertEqual(self.event_names(active_attempt), ["started"])

    def test_context_is_safe_read_only_and_available_after_submission(self) -> None:
        started = self.session(
            self.execute(["start", "--workspace-root", str(self.workspace), "--json"])[1]
        )
        attempt = self.workspace / "attempts" / started["attempt_id"]  # type: ignore[operator]
        (attempt / "simulation.py").write_text("candidate source secret\n", encoding="utf-8")
        (attempt / "test_simulation.py").write_text("test fixture secret\n", encoding="utf-8")
        expected = self.score("passed", "passed", "passed", "passed")
        with patch.object(IsolatedAttemptScorer, "score", return_value=expected):
            self.execute(["submit", "--workspace-root", str(self.workspace), "--json"])
        before_context = file_bytes(attempt)

        code, document = self.execute(
            [
                "context",
                "--workspace-root",
                str(self.workspace),
                "--format",
                "json",
                "--json",
            ]
        )
        markdown_code, markdown = self.execute(
            [
                "context",
                "--workspace-root",
                str(self.workspace),
                "--format",
                "markdown",
                "--json",
            ]
        )

        self.assertEqual((code, markdown_code), (0, 0))
        self.assertEqual(file_bytes(attempt), before_context)
        context = document["result"]["context"]  # type: ignore[index]
        self.assertEqual(context["lifecycle"]["status"], SUBMITTED)  # type: ignore[index]
        self.assertEqual(
            [event["name"] for event in context["events"]],  # type: ignore[index]
            ["started", "submitted"],
        )
        self.assertIn("# Attempt status", markdown["result"]["context"])  # type: ignore[index]
        for forbidden in ("candidate source secret", "test fixture secret", "simulation.py"):
            self.assertNotIn(forbidden, json.dumps(document))
            self.assertNotIn(forbidden, markdown["result"]["context"])  # type: ignore[index]


class WheelRuntimeTests(unittest.TestCase):
    def test_installed_wheel_fetches_offline_then_starts_outside_checkout(self) -> None:
        builder = next(
            (
                candidate
                for candidate in (
                    sys.executable,
                    shutil.which("python3.12"),
                    shutil.which("python3.11"),
                    shutil.which("python3.10"),
                )
                if candidate is not None
                and subprocess.run(
                    [candidate, "-c", "import setuptools"],
                    capture_output=True,
                    check=False,
                ).returncode
                == 0
            ),
            None,
        )
        if builder is None:
            self.skipTest("a Python interpreter with setuptools is required to build a wheel")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wheel_directory = root / "wheel"
            built = subprocess.run(
                [
                    builder,
                    "-m",
                    "pip",
                    "wheel",
                    "--no-deps",
                    "--no-build-isolation",
                    "--wheel-dir",
                    str(wheel_directory),
                    str(PROJECT),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(built.returncode, 0, built.stderr)
            wheel = next(wheel_directory.glob("codesignal_practice_simulator-*.whl"))
            manifest, payloads = synthetic_runtime_fixture()
            replace_wheel_runtime_manifest(wheel, manifest)

            environment = root / "environment"
            subprocess.run([builder, "-m", "venv", str(environment)], check=True)
            executable = environment / "bin" / "codesignal-sim"
            installed = subprocess.run(
                [environment / "bin" / "pip", "install", "--no-deps", str(wheel)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(installed.returncode, 0, installed.stderr)

            workspace = root / "outside-checkout"
            source = root / "offline-source"
            for relative, data in payloads.items():
                path = source / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            fetched = subprocess.run(
                [
                    executable,
                    "fetch",
                    "--workspace-root",
                    str(workspace),
                    "--source",
                    str(source),
                    "--json",
                ],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(fetched.returncode, 0, fetched.stderr)
            self.assertEqual(
                json.loads(fetched.stdout)["result"]["fixture_cache"],  # type: ignore[index]
                str(
                    (
                        workspace / ".cache" / "codesignal-fixtures" / "synthetic"
                    ).resolve()
                ),
            )
            completed = subprocess.run(
                [executable, "start", "--workspace-root", str(workspace), "--json"],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            document = json.loads(completed.stdout)
            self.assertEqual(document["result"]["session"]["status"], "active")  # type: ignore[index]
            self.assertTrue((workspace / "attempts").is_dir())


if __name__ == "__main__":
    unittest.main()
