"""Hermetic real-process verification of the public CLI lifecycle."""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
START = datetime(2000, 1, 1, tzinfo=timezone.utc)
_SCORER_CAPTURE_TIMEOUT_SECONDS = 4
_SCORER_CAPTURE_POLL_SECONDS = 0.02
_CANDIDATE_GROUP_DURATION_SECONDS = 0.5


def _bytes_under(root: Path, *, ignored_names: set[str] | None = None) -> dict[str, bytes]:
    ignored_names = ignored_names or set()
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and path.name not in ignored_names
    }


def _event_names(attempt: Path) -> list[str]:
    return [
        json.loads(line)["name"]
        for line in (attempt / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]


def _without_python_environment() -> dict[str, str]:
    return {
        key: value for key, value in os.environ.items() if not key.startswith("PYTHON")
    }


def _offline_environment() -> dict[str, str]:
    environment = _without_python_environment()
    environment["PIP_NO_INDEX"] = "1"
    return environment


def _tree_snapshot(root: Path) -> dict[str, bytes | None] | None:
    """Capture a target including its existence, files, and empty directories."""
    if not root.exists():
        return None
    snapshot: dict[str, bytes | None] = {"": None}
    for path in sorted(root.rglob("*")):
        snapshot[path.relative_to(root).as_posix()] = (
            path.read_bytes() if path.is_file() else None
        )
    return snapshot


def _parent_snapshot(workspace: Path) -> dict[str, bytes | None]:
    """Capture the command cwd, excluding its explicitly-created workspace."""
    prefix = f"{workspace.name}/"
    return {
        relative: contents
        for relative, contents in (_tree_snapshot(workspace.parent) or {}).items()
        if relative != workspace.name and not relative.startswith(prefix)
    }


def _purelib(interpreter: Path) -> Path:
    return Path(
        subprocess.check_output(
            (
                str(interpreter),
                "-c",
                "import sysconfig; print(sysconfig.get_paths()['purelib'])",
            ),
            text=True,
            env=_without_python_environment(),
        ).strip()
    ).resolve()


def _stop_process(process: subprocess.Popen[str], scorer_pids: set[int]) -> None:
    """Stop the command and observed isolated scorer groups on every exit path."""
    if os.name == "posix":
        for pid in scorer_pids:
            try:
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    if process.poll() is None:
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGTERM)
            else:
                process.terminate()
        except ProcessLookupError:
            pass
    try:
        process.communicate(timeout=1)
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            process.kill()
        process.communicate(timeout=1)


def _commands_from_ps(*known_paths: Path) -> dict[int, tuple[str, ...]]:
    """Return process argv values after preserving known paths with spaces."""
    try:
        processes = subprocess.run(
            ["/bin/ps", "-axww", "-o", "pid=", "-o", "command="],
            text=True,
            capture_output=True,
            check=False,
            timeout=1,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {}

    path_strings = tuple(
        sorted((str(path) for path in known_paths), key=len, reverse=True)
    )
    commands: dict[int, tuple[str, ...]] = {}
    for line in processes.stdout.splitlines():
        try:
            pid_text, separator, command_line = line.strip().partition(" ")
            if not separator:
                continue
            pid = int(pid_text)
            # BSD ps renders argv as an unquoted string. Re-quote the two
            # known absolute argv paths before letting shlex preserve them.
            quoted_line = command_line
            for path in path_strings:
                quoted_line = quoted_line.replace(path, shlex.quote(path))
            arguments = shlex.split(quoted_line)
        except (TypeError, ValueError):
            continue
        command = tuple(
            os.path.realpath(argument) if os.path.isabs(argument) else argument
            for argument in arguments
        )
        commands[pid] = command
    return commands


def _scorer_commands_from_ps(
    runner: Path, interpreter: Path
) -> dict[int, tuple[str, ...]]:
    resolved_runner = os.path.realpath(runner)
    return {
        pid: command
        for pid, command in _commands_from_ps(runner, interpreter).items()
        if resolved_runner in command
    }


def _ps_executable_for(interpreter: Path) -> str:
    """Report the executable ps shows for a process launched by this venv."""
    probe = subprocess.Popen(
        [str(interpreter), "-c", "import time; time.sleep(0.5)"],
        cwd=interpreter.parent.parent,
        env=_without_python_environment(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    deadline = time.monotonic() + 1
    try:
        while time.monotonic() < deadline:
            command = _commands_from_ps(interpreter).get(probe.pid)
            if command is not None:
                return command[0]
            time.sleep(_SCORER_CAPTURE_POLL_SECONDS)
    finally:
        _stop_process(probe, set())
    raise RuntimeError("ps did not report the venv interpreter")


class EndToEndTests(unittest.TestCase):
    """Run hermetic editable console and module entry points outside this checkout."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.checkout_target_snapshots = {
            target: _tree_snapshot(PROJECT / target) for target in ("attempts", ".cache")
        }
        cls.parent_snapshots: dict[Path, dict[str, bytes | None]] = {}
        cls.temporary = tempfile.TemporaryDirectory(prefix="codesignal e2e ")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        if " " not in str(cls.root):
            raise RuntimeError("the E2E workspace must contain a path space")
        cls.editable = cls.root / "editable-project"
        cls.editable.mkdir()
        shutil.copy2(PROJECT / "pyproject.toml", cls.editable / "pyproject.toml")
        shutil.copy2(PROJECT / "README.md", cls.editable / "README.md")
        shutil.copytree(PROJECT / "src", cls.editable / "src")
        source_manifest = (
            PROJECT
            / "src"
            / "codesignal_practice_simulator"
            / "resources"
            / "fixture-manifest.json"
        )
        resources = cls.editable / "src" / "codesignal_practice_simulator" / "resources"
        copied_manifest = resources / "fixture-manifest.json"
        if copied_manifest.read_bytes() != source_manifest.read_bytes():
            raise RuntimeError("editable source copy did not preserve package resources")
        cls.payloads, cls.manifest = cls._write_synthetic_editable_manifest()
        (cls.editable / "src" / "editable_project_sentinel.py").write_text(
            "raise AssertionError('editable project was imported during scoring')\n",
            encoding="utf-8",
        )

        cls.environment = cls.root / "environment"
        cls.python = cls._install_editable_project()
        cls.site_packages = _purelib(cls.python)
        cls.console = cls.environment / "bin" / "codesignal-sim"
        if not cls.console.is_file():
            raise RuntimeError(
                "editable installation succeeded but did not generate "
                f"the codesignal-sim entry point at {cls.console}"
            )
        cls._assert_editable_environment()
        cls.scorer_executable = _ps_executable_for(cls.python)

        cls.source = cls.root / "synthetic-offline-source"
        for upstream_path, data in cls.payloads.items():
            path = cls.source / upstream_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    @classmethod
    def _install_editable_project(cls) -> Path:
        candidates = tuple(
            dict.fromkeys(
                candidate
                for candidate in (
                    sys.executable,
                    shutil.which("python3.11"),
                    shutil.which("python3.10"),
                )
                if candidate is not None
            )
        )
        diagnostics: list[str] = []
        for candidate in candidates:
            version = subprocess.run(
                [
                    candidate,
                    "-c",
                    "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')",
                ],
                text=True,
                capture_output=True,
                env=_without_python_environment(),
                check=False,
            )
            if version.returncode != 0:
                diagnostics.append(
                    f"{candidate}: cannot determine version: {version.stderr.strip()}"
                )
                continue
            if version.stdout.strip() not in {"3.10", "3.11"}:
                diagnostics.append(
                    f"{candidate}: Python {version.stdout.strip()} is not 3.10 or 3.11"
                )
                continue

            shutil.rmtree(cls.environment, ignore_errors=True)
            created = subprocess.run(
                [candidate, "-m", "venv", str(cls.environment)],
                text=True,
                capture_output=True,
                cwd=cls.root,
                env=_without_python_environment(),
                check=False,
            )
            if created.returncode != 0:
                diagnostics.append(
                    f"{candidate}: normal venv creation failed: {created.stderr.strip()}"
                )
                continue

            interpreter = cls.environment / "bin" / "python"
            bundled = subprocess.run(
                [str(interpreter), "-c", "import setuptools, wheel"],
                text=True,
                capture_output=True,
                cwd=cls.root,
                env=_without_python_environment(),
                check=False,
            )
            if bundled.returncode != 0:
                diagnostics.append(
                    f"{candidate}: its fresh normal venv lacks bundled setuptools "
                    f"and wheel: {bundled.stderr.strip()}"
                )
                continue

            installed = subprocess.run(
                [
                    str(interpreter),
                    "-m",
                    "pip",
                    "install",
                    "--no-index",
                    "--no-deps",
                    "--no-build-isolation",
                    "--disable-pip-version-check",
                    "-e",
                    str(cls.editable),
                ],
                text=True,
                capture_output=True,
                cwd=cls.root,
                env=_offline_environment(),
                check=False,
            )
            if installed.returncode == 0:
                return interpreter
            diagnostics.append(
                f"{candidate}: offline editable install failed:\n"
                f"{installed.stdout}{installed.stderr}"
            )

        shutil.rmtree(cls.environment, ignore_errors=True)
        details = "\n".join(f"  - {diagnostic}" for diagnostic in diagnostics)
        raise RuntimeError(
            "No suitable Python 3.10 or 3.11 interpreter was found. The E2E test "
            "requires one whose fresh normal venv includes pip, setuptools, and wheel "
            "so it can install this copied project without network access.\n"
            f"Checked:\n{details or '  - no Python candidates were found'}"
        )

    @classmethod
    def _assert_editable_environment(cls) -> None:
        probe = subprocess.run(
            (
                str(cls.python),
                "-c",
                (
                    "import json, site, sys, sysconfig; "
                    "import codesignal_practice_simulator; "
                    "print(json.dumps({'prefix': sys.prefix, "
                    "'base_prefix': sys.base_prefix, "
                    "'purelib': sysconfig.get_paths()['purelib'], "
                    "'site_packages': site.getsitepackages(), "
                    "'sys_path': sys.path, "
                    "'module_file': codesignal_practice_simulator.__file__}))"
                ),
            ),
            text=True,
            capture_output=True,
            cwd=cls.root,
            env=_without_python_environment(),
            check=False,
        )
        if probe.returncode != 0:
            raise RuntimeError(f"editable import seam failed:\n{probe.stderr}")
        details = json.loads(probe.stdout)
        environment = cls.environment.resolve()
        site_packages = cls.site_packages.resolve()
        if (
            os.path.realpath(details["prefix"]) != str(environment)
            or os.path.realpath(details["base_prefix"]) == str(environment)
        ):
            raise RuntimeError("venv did not retain an isolated sys.prefix")
        if Path(details["purelib"]).resolve() != site_packages:
            raise RuntimeError("venv purelib location changed unexpectedly")
        if [Path(path).resolve() for path in details["site_packages"]] != [site_packages]:
            raise RuntimeError("venv exposes base or system site-packages")
        exposed_site_packages = {
            Path(path).resolve()
            for path in details["sys_path"]
            if "site-packages" in Path(path).parts
        }
        if exposed_site_packages != {site_packages}:
            raise RuntimeError("venv sys.path exposes base or system site-packages")
        if not Path(details["module_file"]).resolve().is_relative_to(
            (cls.editable / "src").resolve()
        ):
            raise RuntimeError("editable import did not resolve to copied source")

    @classmethod
    def _write_synthetic_editable_manifest(cls) -> tuple[dict[str, bytes], dict[str, object]]:
        records = (
            ("README.md", "vendor-readme.md", b"synthetic vendor readme\n"),
            (
                "practice_assessments/file_storage/level1.md",
                "assessment/file_storage/level1.md",
                b"synthetic level one prompt\n",
            ),
            (
                "practice_assessments/file_storage/level2.md",
                "assessment/file_storage/level2.md",
                b"synthetic level two prompt\n",
            ),
            (
                "practice_assessments/file_storage/level3.md",
                "assessment/file_storage/level3.md",
                b"synthetic level three prompt\n",
            ),
            (
                "practice_assessments/file_storage/level4.md",
                "assessment/file_storage/level4.md",
                b"synthetic level four prompt\n",
            ),
            (
                "practice_assessments/file_storage/simulation.py",
                "assessment/file_storage/simulation.py",
                cls._passing_candidate().encode("utf-8"),
            ),
            (
                "practice_assessments/file_storage/test_simulation.py",
                "assessment/file_storage/test_simulation.py",
                cls._test_module().encode("utf-8"),
            ),
        )
        payloads = {upstream_path: data for upstream_path, _cache_path, data in records}
        manifest: dict[str, object] = {
            "fixture_cache_root": ".cache/codesignal-fixtures/synthetic",
            "upstream": {"repository": "offline/example", "commit": "synthetic"},
            "fetches": [
                {
                    "upstream_path": upstream_path,
                    "repository_path": upstream_path,
                    "cache_path": cache_path,
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
                for upstream_path, cache_path, data in records
            ],
        }
        manifest_path = (
            cls.editable
            / "src"
            / "codesignal_practice_simulator"
            / "resources"
            / "fixture-manifest.json"
        )
        manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
        return payloads, manifest

    @staticmethod
    def _passing_candidate() -> str:
        return f"""\
import importlib
import os
import sys
import time


def evaluate(group):
    assert os.getcwd() == sys.path[0]
    assert all(not key.startswith("PYTHON") for key in os.environ)
    assert all("site-packages" not in entry for entry in sys.path)
    for name in (
        "editable_project_sentinel",
        "hostile_pythonpath_sentinel",
        "loose_reference_sentinel",
    ):
        try:
            importlib.import_module(name)
        except ModuleNotFoundError:
            pass
        else:
            raise AssertionError(f"forbidden import succeeded: {{name}}")
    time.sleep({_CANDIDATE_GROUP_DURATION_SECONDS})
    return "ok"
"""

    @staticmethod
    def _test_module() -> str:
        methods = "\n".join(
            f"""\
    def test_group_{group}(self):
        self.assertEqual(evaluate({group}), "ok")
"""
            for group in range(1, 5)
        )
        return (
            "import unittest\n"
            "from simulation import evaluate\n\n\n"
            "class TestSimulateCodingFramework(unittest.TestCase):\n"
            f"{methods}"
        )

    def _entry(self, kind: str) -> list[str]:
        if kind == "console":
            return [str(self.console)]
        if kind == "module":
            return [str(self.python), "-m", "codesignal_practice_simulator"]
        raise AssertionError(f"unknown entry point: {kind}")

    def _workspace(self, name: str) -> Path:
        parent = self.root / "workspaces" / name
        workspace = parent / "workspace"
        workspace.mkdir(parents=True)
        hostile = parent / "hostile"
        hostile.mkdir()
        (hostile / "hostile_pythonpath_sentinel.py").write_text(
            "raise AssertionError('hostile PYTHONPATH was imported')\n", encoding="utf-8"
        )
        (parent / "loose_reference_sentinel.py").write_text(
            "raise AssertionError('loose reference was imported')\n", encoding="utf-8"
        )
        self.parent_snapshots[workspace] = _parent_snapshot(workspace)
        return workspace

    def _run(
        self,
        kind: str,
        workspace: Path,
        *arguments: str,
        wait: bool = True,
    ) -> subprocess.CompletedProcess[str] | subprocess.Popen[str]:
        command = [*self._entry(kind), *arguments, "--workspace-root", str(workspace), "--json"]
        environment = _without_python_environment()
        hostile = workspace.parent / "hostile"
        environment["PYTHONPATH"] = str(hostile)
        environment["PYTHONUSERBASE"] = str(hostile)
        if not wait:
            return subprocess.Popen(
                command,
                cwd=workspace.parent,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
        return subprocess.run(
            command,
            cwd=workspace.parent,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def _document(
        self, completed: subprocess.CompletedProcess[str], expected_exit: int
    ) -> dict[str, object]:
        self.assertEqual(completed.returncode, expected_exit, completed.stderr)
        self.assertEqual(completed.stderr, "")
        self.assertTrue(completed.stdout.endswith("\n"))
        document = json.loads(completed.stdout)
        self.assertEqual(document["schema_version"], "cli/v1")
        self.assertEqual(document["ok"], expected_exit == 0)
        return document

    def _fetch(self, kind: str, workspace: Path) -> Path:
        completed = self._run(kind, workspace, "fetch", "--source", str(self.source))
        assert isinstance(completed, subprocess.CompletedProcess)
        document = self._document(completed, 0)
        cache = workspace / ".cache" / "codesignal-fixtures" / "synthetic"
        self.assertEqual(document["result"]["fixture_cache"], str(cache.resolve()))  # type: ignore[index]
        expected = {
            record["cache_path"]: self.payloads[record["upstream_path"]]  # type: ignore[index]
            for record in self.manifest["fetches"]  # type: ignore[index]
        }
        self.assertEqual(_bytes_under(cache), expected)
        self.assertEqual(
            (cache / "vendor-readme.md").read_bytes(), self.payloads["README.md"]
        )
        return cache

    def _start(self, kind: str, workspace: Path, *options: str) -> tuple[str, Path]:
        completed = self._run(kind, workspace, "start", *options)
        assert isinstance(completed, subprocess.CompletedProcess)
        document = self._document(completed, 0)
        session = document["result"]["session"]  # type: ignore[index]
        attempt_id = session["attempt_id"]  # type: ignore[index]
        self.assertIsInstance(attempt_id, str)
        return attempt_id, workspace / "attempts" / attempt_id

    def _assert_workspace_isolation(self, workspace: Path, cache_before: dict[str, bytes]) -> None:
        cache = workspace / ".cache" / "codesignal-fixtures" / "synthetic"
        self.assertEqual(_bytes_under(cache), cache_before)
        self.assertEqual({path.name for path in workspace.iterdir()}, {".cache", "attempts"})
        for ignored_path in (
            "attempts/.runtime-sentinel",
            ".cache/codesignal-fixtures/.runtime-sentinel",
        ):
            ignored = subprocess.run(
                ["git", "check-ignore", "-q", "--no-index", ignored_path],
                cwd=PROJECT,
                capture_output=True,
                check=False,
            )
            self.assertEqual(ignored.returncode, 0, ignored.stderr.decode())

    def tearDown(self) -> None:
        for target, before in self.checkout_target_snapshots.items():
            self.assertEqual(
                _tree_snapshot(PROJECT / target),
                before,
                f"E2E subprocesses mutated checkout target: {PROJECT / target}",
            )
        for workspace, before in self.parent_snapshots.items():
            self.assertEqual(
                _parent_snapshot(workspace),
                before,
                f"E2E subprocesses mutated their parent cwd outside the allowed "
                f"workspace and sentinels: {workspace.parent}",
            )

    def test_full_console_and_drill_module_complete_lifecycles(self) -> None:
        for kind, mode, options, expected_duration in (
            ("console", "full", (), 5400),
            ("console", "drill", ("--mode", "drill", "--drill-duration-seconds", "60"), 60),
            ("module", "full", (), 5400),
            ("module", "drill", ("--mode", "drill", "--drill-duration-seconds", "60"), 60),
        ):
            with self.subTest(entry=kind, mode=mode):
                workspace = self._workspace(f"{kind}-{mode}")
                cache = self._fetch(kind, workspace)
                cache_before = _bytes_under(cache)
                attempt_id, attempt = self._start(kind, workspace, *options)

                resume = self._run(kind, workspace, "resume", "--attempt", attempt_id)
                assert isinstance(resume, subprocess.CompletedProcess)
                resumed = self._document(resume, 0)["result"]["session"]  # type: ignore[index]
                self.assertEqual(resumed["attempt_id"], attempt_id)  # type: ignore[index]
                self.assertEqual(resumed["profile"]["mode"], mode)  # type: ignore[index]
                self.assertEqual(resumed["profile"]["duration_seconds"], expected_duration)  # type: ignore[index]

                status = self._run(kind, workspace, "status")
                observed_time = self._run(kind, workspace, "time")
                task = self._run(kind, workspace, "task", "--level", "1")
                assert all(
                    isinstance(result, subprocess.CompletedProcess)
                    for result in (status, observed_time, task)
                )
                self.assertEqual(
                    self._document(status, 0)["result"]["session"]["status"], "active"  # type: ignore[index]
                )
                self.assertGreaterEqual(
                    self._document(observed_time, 0)["result"]["remaining_seconds"], 0  # type: ignore[index]
                )
                self.assertEqual(
                    self._document(task, 0)["result"]["prompt"], "synthetic level one prompt\n"  # type: ignore[index]
                )

                tested = self._run(kind, workspace, "test")
                assert isinstance(tested, subprocess.CompletedProcess)
                tested_session = self._document(tested, 0)["result"]["session"]  # type: ignore[index]
                self.assertEqual(tested_session["revision"], 1)  # type: ignore[index]
                self.assertEqual(tested_session["score"]["passed_levels"], 4)  # type: ignore[index]
                self.assertEqual(_event_names(attempt), ["started", "tested"])

                submitted = self._run(kind, workspace, "submit")
                assert isinstance(submitted, subprocess.CompletedProcess)
                submitted_document = self._document(submitted, 0)
                self.assertEqual(submitted_document["result"]["session"]["status"], "submitted")  # type: ignore[index]
                self.assertEqual(_event_names(attempt), ["started", "tested", "submitted"])
                durable_after_submit = (
                    (attempt / "session.json").read_bytes(),
                    (attempt / "events.jsonl").read_bytes(),
                )
                repeated = self._run(kind, workspace, "submit")
                assert isinstance(repeated, subprocess.CompletedProcess)
                self._document(repeated, 0)
                self.assertEqual(repeated.stdout, submitted.stdout)
                self.assertEqual(
                    (
                        (attempt / "session.json").read_bytes(),
                        (attempt / "events.jsonl").read_bytes(),
                    ),
                    durable_after_submit,
                )
                self._assert_workspace_isolation(workspace, cache_before)

    def test_scorer_uses_the_exact_isolated_argv_and_rejects_external_imports(self) -> None:
        workspace = self._workspace("scorer-argv")
        self._fetch("console", workspace)
        _attempt_id, attempt = self._start("console", workspace)
        completed = self._run("console", workspace, "test", wait=False)
        assert isinstance(completed, subprocess.Popen)
        runner = (attempt / ".scoring" / "run_group.py").resolve()
        captured: dict[int, tuple[str, ...]] = {}
        deadline = time.monotonic() + _SCORER_CAPTURE_TIMEOUT_SECONDS
        try:
            while True:
                captured.update(_scorer_commands_from_ps(runner, self.python.resolve()))
                if completed.poll() is not None:
                    break
                if time.monotonic() >= deadline:
                    self.fail("scorer command did not finish before the capture deadline")
                time.sleep(_SCORER_CAPTURE_POLL_SECONDS)
            stdout, stderr = completed.communicate(timeout=1)
            finished = subprocess.CompletedProcess(
                completed.args, completed.returncode, stdout, stderr
            )
            self._document(finished, 0)

            expected = {
                (
                    self.scorer_executable,
                    "-I",
                    "-S",
                    str(runner),
                    str(group),
                )
                for group in range(1, 5)
            }
            self.assertEqual(
                set(captured.values()),
                expected,
                "unexpected or missing scorer commands; "
                f"expected interpreter: {self.scorer_executable}; "
                f"recorded: {set(captured.values())}",
            )
            self.assertEqual(len(captured), 4, f"duplicate scorer commands: {captured}")
        finally:
            _stop_process(completed, set(captured))

    def test_selection_jsonl_tail_lock_and_candidate_failure_paths(self) -> None:
        no_pointer = self._workspace("no-pointer")
        self._fetch("console", no_pointer)
        absent = self._run("console", no_pointer, "status")
        assert isinstance(absent, subprocess.CompletedProcess)
        self.assertEqual(
            absent.stdout,
            '{"error": {"code": "session_unavailable", "message": '
            '"no active attempt; provide --attempt or start a new attempt"}, '
            '"ok": false, "schema_version": "cli/v1"}\n',
        )
        self._document(absent, 3)

        workspace = self._workspace("selection-and-tail")
        self._fetch("console", workspace)
        first_id, first = self._start("console", workspace)
        _second_id, second = self._start("console", workspace)
        second_before = _bytes_under(second, ignored_names={".session.lock"})
        pointer = workspace / "attempts" / "active.json"
        pointer.write_text("{bad", encoding="utf-8")
        explicit = self._run("console", workspace, "status", "--attempt", first_id)
        assert isinstance(explicit, subprocess.CompletedProcess)
        self.assertEqual(
            self._document(explicit, 0)["result"]["session"]["attempt_id"], first_id  # type: ignore[index]
        )
        self.assertEqual(_bytes_under(second, ignored_names={".session.lock"}), second_before)
        corrupt = self._run("console", workspace, "status")
        assert isinstance(corrupt, subprocess.CompletedProcess)
        self.assertEqual(self._document(corrupt, 3)["error"]["code"], "session_unavailable")  # type: ignore[index]

        events = first / "events.jsonl"
        events.write_bytes(events.read_bytes().rstrip(b"\n"))
        valid_tail = self._run("console", workspace, "test", "--attempt", first_id)
        assert isinstance(valid_tail, subprocess.CompletedProcess)
        self._document(valid_tail, 0)
        self.assertTrue(events.read_bytes().endswith(b"\n"))
        self.assertEqual(_event_names(first), ["started", "tested"])

        malformed_workspace = self._workspace("malformed-tail")
        self._fetch("module", malformed_workspace)
        malformed_id, malformed_attempt = self._start("module", malformed_workspace)
        malformed_events = malformed_attempt / "events.jsonl"
        malformed_events.write_bytes(malformed_events.read_bytes() + b"{")
        malformed_before = malformed_events.read_bytes()
        malformed = self._run("module", malformed_workspace, "status", "--attempt", malformed_id)
        assert isinstance(malformed, subprocess.CompletedProcess)
        self.assertEqual(
            self._document(malformed, 0)["result"]["session"]["attempt_id"], malformed_id  # type: ignore[index]
        )
        self.assertEqual(malformed_events.read_bytes(), malformed_before)

        lock_workspace = self._workspace("lock-contention")
        self._fetch("console", lock_workspace)
        lock_id, lock_attempt = self._start("console", lock_workspace)
        lock_path = lock_attempt / ".session.lock"
        locker = subprocess.Popen(
            [
                str(self.python),
                "-c",
                (
                    "import fcntl, sys, time; "
                    "handle = open(sys.argv[1], 'a+'); "
                    "fcntl.flock(handle, fcntl.LOCK_EX); "
                    "print('locked', flush=True); time.sleep(10)"
                ),
                str(lock_path),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            assert locker.stdout is not None
            self.assertEqual(locker.stdout.readline().strip(), "locked")
            lock_before = _bytes_under(lock_attempt, ignored_names={".session.lock"})
            locked = self._run("console", lock_workspace, "status", "--attempt", lock_id)
            assert isinstance(locked, subprocess.CompletedProcess)
            self.assertEqual(self._document(locked, 4)["error"]["code"], "illegal_lifecycle")  # type: ignore[index]
            self.assertEqual(
                _bytes_under(lock_attempt, ignored_names={".session.lock"}), lock_before
            )
        finally:
            locker.terminate()
            locker.communicate(timeout=5)

        failure_workspace = self._workspace("candidate-failure")
        self._fetch("module", failure_workspace)
        failure_id, failure_attempt = self._start("module", failure_workspace)
        (failure_attempt / "simulation.py").write_text(
            "def evaluate(group):\n    return 'wrong' if group == 2 else 'ok'\n",
            encoding="utf-8",
        )
        failed = self._run("module", failure_workspace, "test", "--attempt", failure_id)
        assert isinstance(failed, subprocess.CompletedProcess)
        self.assertEqual(
            failed.stdout,
            '{"error": {"code": "candidate_failure", "message": '
            '"one or more test groups did not pass"}, "ok": false, '
            '"schema_version": "cli/v1"}\n',
        )
        self._document(failed, 5)
        self.assertEqual(_event_names(failure_attempt), ["started", "tested"])
        stored = json.loads((failure_attempt / "session.json").read_text(encoding="utf-8"))
        self.assertEqual(
            [result["outcome"] for result in stored["score"]["levels"]],
            ["passed", "failed", "passed", "passed"],
        )

    def test_persisted_expiry_is_deterministic_and_submission_is_final_once(self) -> None:
        workspace = self._workspace("expired")
        self._fetch("module", workspace)
        attempt_id, attempt = self._start(
            "module", workspace, "--mode", "drill", "--drill-duration-seconds", "1"
        )
        session_path = attempt / "session.json"
        session = json.loads(session_path.read_text(encoding="utf-8"))
        session["started_at"] = START.isoformat()
        session["deadline_at"] = (START + timedelta(seconds=1)).isoformat()
        session_path.write_text(json.dumps(session, sort_keys=True) + "\n", encoding="utf-8")
        runner_marker = attempt / "runner-was-called"
        (attempt / "simulation.py").write_text(
            f"from pathlib import Path\nPath({str(runner_marker)!r}).write_text('called')\n"
            "def evaluate(group):\n    return 'ok'\n",
            encoding="utf-8",
        )

        status = self._run("module", workspace, "status", "--attempt", attempt_id)
        observed_time = self._run("module", workspace, "time", "--attempt", attempt_id)
        assert isinstance(status, subprocess.CompletedProcess)
        assert isinstance(observed_time, subprocess.CompletedProcess)
        self.assertEqual(self._document(status, 0)["result"]["session"]["status"], "expired")  # type: ignore[index]
        self.assertEqual(self._document(observed_time, 0)["result"]["remaining_seconds"], 0)  # type: ignore[index]
        after_expiry = (session_path.read_bytes(), (attempt / "events.jsonl").read_bytes())
        self.assertEqual(_event_names(attempt), ["started", "expired"])

        resumed = self._run("module", workspace, "resume", "--attempt", attempt_id)
        tested = self._run("module", workspace, "test", "--attempt", attempt_id)
        assert isinstance(resumed, subprocess.CompletedProcess)
        assert isinstance(tested, subprocess.CompletedProcess)
        self.assertEqual(self._document(resumed, 4)["error"]["code"], "illegal_lifecycle")  # type: ignore[index]
        self.assertEqual(self._document(tested, 4)["error"]["code"], "illegal_lifecycle")  # type: ignore[index]
        self.assertFalse(runner_marker.exists())
        self.assertEqual((session_path.read_bytes(), (attempt / "events.jsonl").read_bytes()), after_expiry)

        submitted = self._run("module", workspace, "submit", "--attempt", attempt_id)
        assert isinstance(submitted, subprocess.CompletedProcess)
        submitted_document = self._document(submitted, 0)
        self.assertEqual(submitted_document["result"]["session"]["status"], "submitted")  # type: ignore[index]
        self.assertTrue(runner_marker.exists())
        self.assertEqual(_event_names(attempt), ["started", "expired", "submitted"])
        after_submit = (session_path.read_bytes(), (attempt / "events.jsonl").read_bytes())
        repeated = self._run("module", workspace, "submit", "--attempt", attempt_id)
        assert isinstance(repeated, subprocess.CompletedProcess)
        self._document(repeated, 0)
        self.assertEqual(repeated.stdout, submitted.stdout)
        self.assertEqual((session_path.read_bytes(), (attempt / "events.jsonl").read_bytes()), after_submit)


if __name__ == "__main__":
    unittest.main()
