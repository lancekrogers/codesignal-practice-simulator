"""Registry and subprocess-isolation tests for copied assessment attempts."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from codesignal_practice_simulator.assessments import (
    DEFAULT_ASSESSMENT_REGISTRY,
    FILE_STORAGE,
)
from codesignal_practice_simulator.errors import (
    FixtureSetupRequiredError,
    InvalidInputError,
)
from codesignal_practice_simulator.lifecycle import LifecycleService
from codesignal_practice_simulator.models import (
    ACTIVE,
    FULL_DURATION_SECONDS,
    FULL_MODE,
    FULL_PROFILE,
    SESSION_SCHEMA_VERSION,
    AssessmentMetadata,
    ModeProfile,
    SessionState,
)
from codesignal_practice_simulator.scoring import (
    MAX_OUTPUT_BYTES,
    RUNNER_DIRECTORY,
    RUNNER_FILENAME,
    IsolatedAttemptScorer,
    _POSIX_PS,
    _PROCESS_POLL_SECONDS,
    _collect_bounded_output,
)
from codesignal_practice_simulator.workspace import (
    CACHE_INPUTS,
    ValidatedFixtureCache,
    WorkspaceManager,
)


START = datetime(2026, 9, 8, 19, tzinfo=timezone.utc)
TEST_MODULE = """
import unittest
from simulation import evaluate


class TestSimulateCodingFramework(unittest.TestCase):
    def test_group_1(self):
        self.assertEqual(evaluate(1), "ok")

    def test_group_2(self):
        self.assertEqual(evaluate(2), "ok")

    def test_group_3(self):
        self.assertEqual(evaluate(3), "ok")

    def test_group_4(self):
        self.assertEqual(evaluate(4), "ok")
"""
PASSING_CANDIDATE = """
def evaluate(group):
    return "ok"
"""
_POSIX_CONTAINMENT_AVAILABLE = (
    os.name == "posix"
    and _POSIX_PS is not None
    and hasattr(os, "fork")
    and hasattr(os, "setsid")
)


def _pid_has_exited(pid: int, timeout_seconds: float) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.01)


def _read_recorded_pid(path: Path, timeout_seconds: float) -> int | None:
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            return int(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            if time.monotonic() >= deadline:
                return None
            time.sleep(0.01)


def _bounded_test_process_cleanup(
    process: subprocess.Popen[bytes], descendant_pid: int | None
) -> None:
    if descendant_pid is not None:
        try:
            os.kill(descendant_pid, 9)
        except ProcessLookupError:
            pass
        _pid_has_exited(descendant_pid, 0.2)
    try:
        os.killpg(process.pid, 9)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=0.2)
    except subprocess.TimeoutExpired:
        pass
    if process.stdout is not None and not process.stdout.closed:
        process.stdout.close()


class FakeClock:
    def now(self) -> datetime:
        return START


class _SteppingClock:
    def __init__(self, step: float) -> None:
        self.value = 0.0
        self.step = step

    def monotonic(self) -> float:
        value = self.value
        self.value += self.step
        return value


class _FakeStream:
    def __init__(self) -> None:
        self.closed = False

    def fileno(self) -> int:
        return 123

    def close(self) -> None:
        self.closed = True


class _RunningProcess:
    def __init__(self) -> None:
        self.stdout = _FakeStream()
        self.pid = 456

    def poll(self) -> None:
        return None


class _RecordingSelector:
    def __init__(self) -> None:
        self.waits: list[float] = []

    def register(self, _stream: object, _events: int) -> None:
        pass

    def unregister(self, _stream: object) -> None:
        pass

    def select(self, timeout: float) -> list[object]:
        self.waits.append(timeout)
        return []

    def close(self) -> None:
        pass


def make_cache(root: Path) -> ValidatedFixtureCache:
    contents = {"vendor-readme.md": b"vendor readme\n"}
    contents.update(
        {
            f"assessment/file_storage/{name}": (
                TEST_MODULE.encode("utf-8")
                if name == "test_simulation.py"
                else PASSING_CANDIDATE.encode("utf-8")
                if name == "simulation.py"
                else f"prompt for {name}\n".encode("utf-8")
            )
            for name in CACHE_INPUTS
        }
    )
    hashes: dict[str, str] = {}
    cache = root / "cache"
    for relative, data in contents.items():
        path = cache.joinpath(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        hashes[relative] = hashlib.sha256(data).hexdigest()
    return ValidatedFixtureCache(cache, hashes, content_version="upstream-0000000")


def state() -> SessionState:
    return SessionState(
        schema_version=SESSION_SCHEMA_VERSION,
        attempt_id="2b4fbdaa-7f5c-4019-ae26-24d535000001",
        assessment=AssessmentMetadata("file_storage", "File Storage"),
        profile=ModeProfile(FULL_MODE, FULL_PROFILE, FULL_DURATION_SECONDS),
        started_at=START,
        deadline_at=START.replace(hour=20, minute=30),
        status=ACTIVE,
        revision=0,
    )


class ScoringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.cache = make_cache(root)
        self.workspace = WorkspaceManager(root / "workspace", self.cache)
        self.attempt = self.workspace.create_attempt(state())

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def write_candidate(self, source: str) -> None:
        (self.attempt / "simulation.py").write_text(source, encoding="utf-8")

    def test_registry_has_only_file_storage_with_its_complete_contract(self) -> None:
        definition = DEFAULT_ASSESSMENT_REGISTRY.require("file_storage")

        self.assertIs(definition, FILE_STORAGE)
        self.assertEqual(definition.copied_filenames, CACHE_INPUTS)
        self.assertEqual(definition.level_groups, (1, 2, 3, 4))
        self.assertEqual(
            definition.profile_ids, frozenset(("full-90m", "drill-30m"))
        )
        with self.assertRaisesRegex(InvalidInputError, "unknown assessment"):
            DEFAULT_ASSESSMENT_REGISTRY.require("another_assessment")

    def test_workspace_copies_runner_and_only_registered_candidate_inputs(self) -> None:
        self.assertTrue(
            (self.attempt / RUNNER_DIRECTORY / RUNNER_FILENAME).is_file()
        )
        self.assertTrue((self.attempt / RUNNER_DIRECTORY / "bootstrap.py").is_file())
        self.assertFalse((self.attempt / "vendor-readme.md").exists())
        self.assertFalse((self.attempt / "solution").exists())
        self.assertFalse((self.attempt / "study").exists())

    def test_lifecycle_persists_four_independent_results_from_exact_launches(self) -> None:
        scorer = IsolatedAttemptScorer(FILE_STORAGE)
        service = LifecycleService(self.workspace, FakeClock(), scorer)

        recorded = service.test(state().attempt_id)

        self.assertEqual(
            [result.outcome for result in recorded.score.levels],  # type: ignore[union-attr]
            ["passed", "passed", "passed", "passed"],
        )
        self.assertEqual(recorded.score.passed_levels, 4)  # type: ignore[union-attr]
        self.assertEqual(recorded.score.highest_contiguous_level, 4)  # type: ignore[union-attr]
        self.assertEqual(
            [run.command for run in scorer.last_runs],
            [
                (
                    str(scorer.interpreter),
                    "-I",
                    "-S",
                    str(self.attempt / ".scoring" / "run_group.py"),
                    str(group),
                )
                for group in (1, 2, 3, 4)
            ],
        )
        self.assertEqual(
            [
                event.name
                for event in self.workspace.persistence.read_events(self.attempt)
            ],
            ["started", "tested"],
        )

    def test_failure_crash_timeout_and_missing_input_do_not_skip_later_groups(self) -> None:
        self.write_candidate(
            """
import os
import time


def evaluate(group):
    if group == 1:
        return "wrong"
    if group == 2:
        os._exit(7)
    if group == 3:
        time.sleep(2)
    return "ok"
"""
        )
        scorer = IsolatedAttemptScorer(FILE_STORAGE, timeout_seconds=0.1)
        score = scorer.score(self.attempt)

        self.assertEqual(
            [result.outcome for result in score.levels],
            ["failed", "error", "error", "passed"],
        )
        self.assertEqual([run.group for run in scorer.last_runs], [1, 2, 3, 4])
        self.assertEqual(scorer.last_runs[2].detail, "timeout")

        (self.attempt / "test_simulation.py").unlink()
        missing_score = scorer.score(self.attempt)
        self.assertEqual(
            [result.outcome for result in missing_score.levels],
            ["error", "error", "error", "error"],
        )

    def test_launch_error_is_recorded_for_each_group(self) -> None:
        scorer = IsolatedAttemptScorer(
            FILE_STORAGE,
            interpreter=Path(self.temporary_directory.name) / "missing-python",
        )

        score = scorer.score(self.attempt)

        self.assertEqual(
            [result.outcome for result in score.levels],
            ["error", "error", "error", "error"],
        )
        self.assertTrue(
            all(run.detail.startswith("launch error:") for run in scorer.last_runs)
        )

    def test_runner_rejects_an_invalid_group_and_wrong_working_directory(self) -> None:
        scorer = IsolatedAttemptScorer(FILE_STORAGE)
        with self.assertRaisesRegex(InvalidInputError, "invalid level group"):
            scorer.run_group(self.attempt, 5)

        completed = subprocess.run(
            (
                str(scorer.interpreter),
                "-I",
                "-S",
                str(self.attempt / ".scoring" / "run_group.py"),
                "1",
            ),
            cwd=self.attempt.parent,
            env={},
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("not executing from its attempt", completed.stderr)

    def test_output_is_bounded(self) -> None:
        self.write_candidate(
            """
def evaluate(group):
    print("x" * 20000)
    return "wrong"
"""
        )
        run = IsolatedAttemptScorer(FILE_STORAGE).run_group(self.attempt, 1)

        self.assertEqual(run.outcome, "failed")
        self.assertIn("[output truncated]", run.detail)
        self.assertLessEqual(
            len(run.detail.encode("utf-8")),
            MAX_OUTPUT_BYTES + len("\n[output truncated]"),
        )

    def test_continuously_readable_output_rechecks_deadline_after_each_read(self) -> None:
        process = _RunningProcess()
        selector = _RecordingSelector()
        clock = _SteppingClock(0.01)
        reads = 0

        def always_readable(_descriptor: int, _size: int) -> bytes:
            nonlocal reads
            reads += 1
            if reads > 6:
                self.fail("continuous output was drained without a deadline recheck")
            return b"x" * 4096

        with (
            patch(
                "codesignal_practice_simulator.scoring.selectors.DefaultSelector",
                return_value=selector,
            ),
            patch("codesignal_practice_simulator.scoring.os.set_blocking"),
            patch(
                "codesignal_practice_simulator.scoring.os.read",
                side_effect=always_readable,
            ),
            patch(
                "codesignal_practice_simulator.scoring.time.monotonic",
                side_effect=clock.monotonic,
            ),
            patch(
                "codesignal_practice_simulator.scoring._snapshot_descendant_pids",
                return_value=(),
            ),
            patch("codesignal_practice_simulator.scoring._stop_process_tree"),
            patch("codesignal_practice_simulator.scoring._poll_cleanup"),
        ):
            output, timed_out = _collect_bounded_output(process, 0.03)  # type: ignore[arg-type]

        self.assertTrue(timed_out)
        self.assertLessEqual(reads, 4)
        self.assertIn("[output truncated]", output)
        self.assertTrue(
            all(wait <= _PROCESS_POLL_SECONDS for wait in selector.waits)
        )

    @unittest.skipUnless(os.name == "posix", "requires POSIX process containment")
    def test_continuous_writer_times_out_is_reaped_and_later_groups_run(self) -> None:
        pid_file = self.attempt / "continuous-writer.pid"
        self.write_candidate(
            f"""
import os
import time
from pathlib import Path


def evaluate(group):
    if group != 1:
        return "ok"
    Path({str(pid_file)!r}).write_text(str(os.getpid()), encoding="utf-8")
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        os.write(1, b"RUNTIME_OUTPUT_PATH /tmp/private/continuous\\n" * 64)
    return "ok"
"""
        )
        scorer = IsolatedAttemptScorer(FILE_STORAGE, timeout_seconds=0.1)
        started = time.monotonic()

        score = scorer.score(self.attempt)
        elapsed = time.monotonic() - started
        writer_pid = _read_recorded_pid(pid_file, 0.2)

        self.assertEqual(
            [result.outcome for result in score.levels],
            ["error", "passed", "passed", "passed"],
        )
        self.assertEqual(scorer.last_runs[0].detail, "timeout")
        self.assertLess(elapsed, 1.5)
        self.assertIsNotNone(writer_pid)
        assert writer_pid is not None
        self.assertTrue(_pid_has_exited(writer_pid, 0.5))

    @unittest.skipUnless(
        os.name == "posix" and hasattr(os, "fork"),
        "requires POSIX fork",
    )
    def test_exited_parent_does_not_wait_for_descendant_held_output_pipe(self) -> None:
        source = """
import os
import time


if os.fork() == 0:
    time.sleep(2)
    os._exit(0)
os._exit(0)
"""
        process = subprocess.Popen(
            (sys.executable, "-c", source),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        started = time.monotonic()
        try:
            _output, timed_out = _collect_bounded_output(process, 1.0)
            elapsed = time.monotonic() - started

            self.assertFalse(timed_out)
            self.assertEqual(process.returncode, 0)
            self.assertLess(elapsed, 0.4)
        finally:
            _bounded_test_process_cleanup(process, None)

    @unittest.skipUnless(
        _POSIX_CONTAINMENT_AVAILABLE, "requires POSIX process containment"
    )
    def test_candidate_fork_for_setsid_is_rejected_without_creating_a_child(self) -> None:
        pid_file = self.attempt / "detached-descendant.pid"
        self.write_candidate(
            f"""
import os
import time
from pathlib import Path


def evaluate(group):
    try:
        descendant = os.fork()
    except RuntimeError as error:
        assert "unsafe child process creation" in str(error)
        return "ok"
    if descendant == 0:
        Path({str(pid_file)!r}).write_text(str(os.getpid()), encoding="utf-8")
        os.setsid()
        while True:
            time.sleep(60)
    deadline = time.monotonic() + 0.2
    while not Path({str(pid_file)!r}).exists() and time.monotonic() < deadline:
        time.sleep(0.001)
    raise AssertionError("fork unexpectedly succeeded")
"""
        )
        descendant_pid: int | None = None
        try:
            run = IsolatedAttemptScorer(
                FILE_STORAGE, timeout_seconds=0.4
            ).run_group(self.attempt, 1)
            self.assertEqual(run.outcome, "passed", run.detail)
            self.assertFalse(pid_file.exists())
        finally:
            if pid_file.exists():
                try:
                    descendant_pid = int(pid_file.read_text(encoding="utf-8"))
                except ValueError:
                    pass
            if descendant_pid is not None:
                try:
                    os.kill(descendant_pid, 9)
                except ProcessLookupError:
                    pass
                _pid_has_exited(descendant_pid, 0.2)

    @unittest.skipUnless(
        _POSIX_CONTAINMENT_AVAILABLE, "requires POSIX process containment"
    )
    def test_timeout_kills_a_detached_descendant_from_the_immediate_snapshot(self) -> None:
        pid_file = self.attempt / "detached-descendant.pid"
        source = """
import os
import sys
import time
from pathlib import Path


pid_file = Path(sys.argv[1])
descendant = os.fork()
if descendant == 0:
    os.setsid()
    pid_file.write_text(str(os.getpid()), encoding="utf-8")
    while True:
        time.sleep(60)
while not pid_file.exists():
    time.sleep(0.001)
while True:
    time.sleep(60)
"""
        process = subprocess.Popen(
            (sys.executable, "-c", source, str(pid_file)),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        descendant_pid: int | None = None
        timeout = 0.15
        started = time.monotonic()
        try:
            _, timed_out = _collect_bounded_output(process, timeout)
            elapsed = time.monotonic() - started
            descendant_pid = _read_recorded_pid(pid_file, 0.2)

            self.assertTrue(timed_out)
            self.assertLess(elapsed, timeout + 0.5)
            self.assertIsNotNone(descendant_pid)
            assert descendant_pid is not None
            self.assertTrue(_pid_has_exited(descendant_pid, 0.5))
        finally:
            if descendant_pid is None:
                descendant_pid = _read_recorded_pid(pid_file, 0.2)
            _bounded_test_process_cleanup(process, descendant_pid)

    def test_coaching_status_and_cache_changes_do_not_affect_candidate_only_score(self) -> None:
        cache_before = {
            path.relative_to(self.cache.root).as_posix(): path.read_bytes()
            for path in self.cache.root.rglob("*")
            if path.is_file()
        }
        (self.attempt / "COACHING.md").write_text("wrong answer", encoding="utf-8")
        (self.attempt / "STATUS.md").write_text("submitted", encoding="utf-8")
        cache_candidate = self.cache.root / "assessment" / "file_storage" / "simulation.py"
        cache_candidate.write_text("def evaluate(group): return 'wrong'\n", encoding="utf-8")
        cache_after = {
            path.relative_to(self.cache.root).as_posix(): path.read_bytes()
            for path in self.cache.root.rglob("*")
            if path.is_file()
        }
        self.assertNotEqual(cache_after, cache_before)

        score = IsolatedAttemptScorer(FILE_STORAGE).score(self.attempt)

        self.assertEqual(score.passed_levels, 4)
        self.assertEqual(
            {
                path.relative_to(self.cache.root).as_posix(): path.read_bytes()
                for path in self.cache.root.rglob("*")
                if path.is_file()
            },
            cache_after,
        )

    def test_isolation_excludes_editable_install_pythonpath_and_loose_reference(self) -> None:
        hostile = Path(self.temporary_directory.name) / "hostile"
        hostile.mkdir()
        (hostile / "hostile_pythonpath_sentinel.py").write_text(
            "raise AssertionError('hostile PYTHONPATH was imported')\n", encoding="utf-8"
        )
        (self.attempt.parent / "loose_reference_sentinel.py").write_text(
            "raise AssertionError('loose reference was imported')\n", encoding="utf-8"
        )
        sentinel_name = f"editable_project_sentinel_{uuid4().hex}"
        sentinel = PROJECT / "src" / f"{sentinel_name}.py"
        sentinel.write_text("VALUE = 'installed editable sentinel'\n", encoding="utf-8")
        self.addCleanup(sentinel.unlink)

        environment = Path(self.temporary_directory.name) / "editable-environment"
        candidates = (sys.executable, shutil.which("python3.10"), shutil.which("python3.11"))
        for base_interpreter in dict.fromkeys(
            candidate for candidate in candidates if candidate is not None
        ):
            created = subprocess.run(
                [base_interpreter, "-m", "venv", "--without-pip", str(environment)],
                capture_output=True,
                check=False,
            )
            if created.returncode == 0:
                break
            shutil.rmtree(environment, ignore_errors=True)
        else:
            self.fail("a Python interpreter able to create an isolated venv is required")
        interpreter = environment / "bin" / "python"
        site_packages = Path(
            subprocess.check_output(
                (
                    str(interpreter),
                    "-c",
                    "import sysconfig; print(sysconfig.get_paths()['purelib'])",
                ),
                text=True,
            ).strip()
        )
        (site_packages / "codesignal_practice_simulator-editable.pth").write_text(
            f"{PROJECT / 'src'}\nimport os\n", encoding="utf-8"
        )
        installed = subprocess.run(
            (
                str(interpreter),
                "-c",
                f"import {sentinel_name}; assert {sentinel_name}.VALUE",
            ),
            capture_output=True,
            text=True,
        )
        self.assertEqual(installed.returncode, 0, installed.stderr)

        self.write_candidate(
            f"""
import importlib
import os
import site
import sys


def evaluate(group):
    assert os.getcwd() == sys.path[0]
    assert all("site-packages" not in path for path in sys.path)
    assert all(not key.startswith("PYTHON") for key in os.environ)
    assert {str(PROJECT / "src")!r} not in sys.path
    try:
        site.main()
    except RuntimeError as error:
        assert "unsafe" in str(error)
    try:
        site.addsitedir({str(site_packages)!r})
    except RuntimeError as error:
        assert "unsafe" in str(error)
    sys.path.append({str(hostile)!r})
    try:
        exec("pass")
    except RuntimeError as error:
        assert "unsafe dynamic" in str(error)
    else:
        raise AssertionError("unsafe dynamic execution succeeded")
    for name in (
        {sentinel_name!r},
        "hostile_pythonpath_sentinel",
        "loose_reference_sentinel",
    ):
        try:
            importlib.import_module(name)
        except (ModuleNotFoundError, RuntimeError):
            continue
        raise AssertionError(f"forbidden import succeeded: {{name}}")
    return "ok"
"""
        )
        scorer = IsolatedAttemptScorer(FILE_STORAGE, interpreter=interpreter)
        with patch.dict(
            os.environ,
            {"PYTHONPATH": str(hostile), "PYTHONUSERBASE": str(hostile)},
            clear=False,
        ):
            score = scorer.score(self.attempt)

        self.assertEqual(score.passed_levels, 4, scorer.last_runs)

    def test_setup_required_cache_failure_occurs_before_workspace_mutation(self) -> None:
        missing = ValidatedFixtureCache(
            Path(self.temporary_directory.name) / "missing-cache", {}
        )
        workspace = WorkspaceManager(
            Path(self.temporary_directory.name) / "missing-workspace", missing
        )

        with self.assertRaisesRegex(FixtureSetupRequiredError, "setup is required"):
            workspace.create_attempt(state())
        self.assertFalse(workspace.attempts_directory.exists())


if __name__ == "__main__":
    unittest.main()
