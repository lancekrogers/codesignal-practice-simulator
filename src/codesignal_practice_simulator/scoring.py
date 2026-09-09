"""Isolated, per-level scoring of copied candidate assessment inputs."""

from __future__ import annotations

import os
import selectors
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from .assessments import AssessmentDefinition, DEFAULT_ASSESSMENT_REGISTRY
from .errors import InvalidInputError
from .models import ERROR, FAILED, PASSED, LevelResult, ScoreSummary


RUNNER_DIRECTORY = ".scoring"
RUNNER_FILENAME = "run_group.py"
BOOTSTRAP_FILENAME = "bootstrap.py"
MAX_OUTPUT_BYTES = 8 * 1024
DEFAULT_TIMEOUT_SECONDS = 10.0
_POST_KILL_WAIT_SECONDS = 0.1
_PROCESS_POLL_SECONDS = 0.05
_PROCESS_SNAPSHOT_SECONDS = 0.1
_PROCESS_CREATION_AUDIT_EVENTS = frozenset(
    {
        "os.fork",
        "os.forkpty",
        "os.exec",
        "os.posix_spawn",
        "os.spawn",
        "os.startfile",
        "os.startfile/2",
        "os.system",
        "subprocess.Popen",
    }
)
_POSIX_PS = next(
    (
        path
        for path in (Path("/bin/ps"), Path("/usr/bin/ps"))
        if path.is_file() and os.access(path, os.X_OK)
    ),
    None,
)

_RUNNER_SOURCE = r'''"""Attempt-local entry point for one isolated assessment group."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    runner = Path(__file__).resolve()
    scoring_directory = runner.parent
    attempt = scoring_directory.parent
    if (
        runner.name != "run_group.py"
        or scoring_directory.name != ".scoring"
        or not attempt.is_dir()
        or Path.cwd().resolve() != attempt
    ):
        print("isolation failure: runner is not executing from its attempt", file=sys.stderr)
        return 2
    bootstrap = scoring_directory / "bootstrap.py"
    if not bootstrap.is_file() or bootstrap.is_symlink():
        print("isolation failure: attempt bootstrap is unavailable", file=sys.stderr)
        return 2

    namespace = {"__name__": "_attempt_scoring_bootstrap", "__file__": str(bootstrap)}
    try:
        exec(compile(bootstrap.read_bytes(), str(bootstrap), "exec"), namespace)
        return namespace["run"](attempt, sys.argv[1:])
    except Exception as error:
        print(f"isolation failure: {error}", file=sys.stderr)
        return 2


raise SystemExit(main())
'''

_BOOTSTRAP_SOURCE = r'''"""Attempt-local stdlib-only bootstrap for one assessment group."""

from __future__ import annotations

import sys
import sysconfig
import unittest
from pathlib import Path


_PROCESS_CREATION_AUDIT_EVENTS = frozenset(
    {
        "os.fork",
        "os.forkpty",
        "os.exec",
        "os.posix_spawn",
        "os.spawn",
        "os.startfile",
        "os.startfile/2",
        "os.system",
        "subprocess.Popen",
    }
)


def _standard_library_roots() -> tuple[Path, ...]:
    roots: list[Path] = []
    configured = sysconfig.get_paths()
    for key in ("stdlib", "platstdlib"):
        value = configured.get(key)
        if not value:
            continue
        root = Path(value).resolve()
        for path in (root, root / "lib-dynload"):
            if path.is_dir() and path not in roots:
                roots.append(path)
    if not roots:
        raise RuntimeError("interpreter standard-library paths are unavailable")
    return tuple(roots)


def _configure_imports(attempt: Path) -> tuple[Path, ...]:
    candidate = attempt / "simulation.py"
    tests = attempt / "test_simulation.py"
    for path in (candidate, tests):
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"copied input is unavailable: {path.name}")

    roots = (attempt.resolve(), *_standard_library_roots())
    allowed = [str(root) for root in roots]
    sys.dont_write_bytecode = True
    sys.path[:] = allowed
    if sys.path != allowed:
        raise RuntimeError("could not enforce the isolated import path")
    return roots


def _install_execution_audit_hook(roots: tuple[Path, ...]) -> None:
    """Reject code loaded outside the copied attempt or interpreter stdlib.

    Audit hooks installed with ``sys.addaudithook`` cannot be removed by
    Python code. This prevents accidental path restoration through
    ``site.main()`` and executable ``.pth`` files, and prevents Python-level
    child-process creation from escaping the scoring process group. Process
    containment is defense in depth, not a general security sandbox against a
    same-user process with native-code capabilities.
    """
    def permitted(filename: object) -> None:
        if (
            isinstance(filename, str)
            and filename.startswith("<frozen ")
            and filename.endswith(">")
        ):
            return
        if not isinstance(filename, str) or not filename:
            raise RuntimeError("unsafe code execution without a real filename")
        path = Path(filename)
        if not path.is_absolute():
            raise RuntimeError(f"unsafe dynamic code execution: {filename}")
        try:
            resolved = path.resolve(strict=True)
        except OSError as error:
            raise RuntimeError(f"unsafe code execution: {filename}") from error
        if any(resolved == root or root in resolved.parents for root in roots):
            return
        raise RuntimeError(f"unsafe code execution outside isolated roots: {filename}")

    def audit(event: str, arguments: tuple[object, ...]) -> None:
        if event in _PROCESS_CREATION_AUDIT_EVENTS:
            raise RuntimeError("unsafe child process creation during scoring")
        if event == "exec":
            code = arguments[0] if arguments else None
            permitted(getattr(code, "co_filename", None))
        elif event == "import" and len(arguments) > 1 and arguments[1] is not None:
            permitted(arguments[1])

    sys.addaudithook(audit)


def run(attempt: Path, arguments: list[str]) -> int:
    if len(arguments) != 1 or arguments[0] not in {"1", "2", "3", "4"}:
        print("invalid level group", file=sys.stderr)
        return 2
    roots = _configure_imports(attempt)
    _install_execution_audit_hook(roots)
    group = arguments[0]
    suite = unittest.defaultTestLoader.loadTestsFromName(
        f"test_simulation.TestSimulateCodingFramework.test_group_{group}"
    )
    result = unittest.TextTestRunner(verbosity=0).run(suite)
    if result.wasSuccessful():
        return 0
    return 2 if result.errors else 1
'''


@dataclass(frozen=True, slots=True)
class GroupRun:
    """Bounded diagnostic evidence from one independent child process."""

    group: int
    outcome: Literal["passed", "failed", "error"]
    returncode: int | None
    detail: str
    command: tuple[str, ...]


class IsolatedAttemptScorer:
    """Run each registered group in a fresh, path-isolated Python child."""

    def __init__(
        self,
        definition: AssessmentDefinition,
        *,
        interpreter: str | Path | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if definition is not DEFAULT_ASSESSMENT_REGISTRY.require(
            definition.metadata.assessment_id
        ):
            raise InvalidInputError("assessment definition is not registered")
        if timeout_seconds <= 0:
            raise InvalidInputError("scoring timeout must be positive")
        selected = Path(sys.executable if interpreter is None else interpreter).resolve()
        if not selected.is_absolute():
            raise InvalidInputError("scoring interpreter must be absolute")
        self.definition = definition
        self.interpreter = selected
        self.timeout_seconds = timeout_seconds
        self.last_runs: tuple[GroupRun, ...] = ()

    def __call__(self, attempt: Path) -> ScoreSummary:
        return self.score(attempt)

    def score(self, attempt: Path) -> ScoreSummary:
        """Score all four groups, retaining bounded evidence without writing state."""
        attempt = Path(attempt).resolve()
        runs = tuple(
            self.run_group(attempt, group) for group in self.definition.level_groups
        )
        self.last_runs = runs
        return ScoreSummary(
            tuple(LevelResult(run.group, run.outcome) for run in runs)
        )

    def run_group(self, attempt: Path, group: int) -> GroupRun:
        """Run one supported group with the exact isolated child command."""
        if group not in self.definition.level_groups:
            raise InvalidInputError(f"invalid level group: {group}")
        runner = attempt / RUNNER_DIRECTORY / RUNNER_FILENAME
        command = (
            str(self.interpreter),
            "-I",
            "-S",
            str(runner),
            str(group),
        )
        try:
            process = subprocess.Popen(
                command,
                cwd=attempt,
                env={},
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        except OSError as error:
            return GroupRun(group, ERROR, None, f"launch error: {error}", command)

        output, timed_out = _collect_bounded_output(process, self.timeout_seconds)
        if timed_out:
            return GroupRun(group, ERROR, None, "timeout", command)
        if process.returncode == 0:
            return GroupRun(group, PASSED, process.returncode, "", command)
        if process.returncode == 1:
            return GroupRun(group, FAILED, process.returncode, output, command)
        return GroupRun(
            group,
            ERROR,
            process.returncode,
            output or f"child exited with status {process.returncode}",
            command,
        )


def install_attempt_runner(
    attempt: Path,
    write_bytes: Callable[[Path, bytes], None],
    flush_file: Callable[[Path], None],
    mkdir: Callable[[Path], None],
) -> None:
    """Install the authored runner and bootstrap while an attempt is staged."""
    scoring_directory = attempt / RUNNER_DIRECTORY
    mkdir(scoring_directory)
    for filename, source in (
        (RUNNER_FILENAME, _RUNNER_SOURCE),
        (BOOTSTRAP_FILENAME, _BOOTSTRAP_SOURCE),
    ):
        path = scoring_directory / filename
        write_bytes(path, source.encode("utf-8"))
        flush_file(path)


def _collect_bounded_output(
    process: subprocess.Popen[bytes], timeout_seconds: float
) -> tuple[str, bool]:
    """Drain output until the wall-clock deadline without blocking on EOF."""
    assert process.stdout is not None
    stream = process.stdout
    descriptor = stream.fileno()
    os.set_blocking(descriptor, False)
    output = bytearray()
    truncated = False

    def drain() -> bool:
        nonlocal truncated
        while True:
            try:
                block = os.read(descriptor, 4096)
            except BlockingIOError:
                return True
            except OSError:
                return False
            if not block:
                return False
            remaining = MAX_OUTPUT_BYTES - len(output)
            if remaining > 0:
                output.extend(block[:remaining])
            if len(block) > remaining:
                truncated = True

    timed_out = False
    selector = selectors.DefaultSelector()
    try:
        selector.register(stream, selectors.EVENT_READ)
        deadline = time.monotonic() + timeout_seconds
        stream_open = True
        while process.poll() is None:
            if stream_open:
                stream_open = drain()
                if not stream_open:
                    selector.unregister(stream)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                descendants = _snapshot_descendant_pids(process.pid)
                _stop_process_tree(process, descendants)
                if stream_open:
                    selector.unregister(stream)
                    stream_open = False
                stream.close()
                _poll_cleanup(process, descendants)
                break
            if stream_open:
                selector.select(remaining)
            else:
                try:
                    process.wait(timeout=min(remaining, _PROCESS_POLL_SECONDS))
                except subprocess.TimeoutExpired:
                    pass
        else:
            if stream_open:
                drain()
    finally:
        selector.close()
        if not stream.closed:
            stream.close()
    text = output.decode("utf-8", errors="replace")
    if truncated:
        text += "\n[output truncated]"
    return text, timed_out


def _snapshot_descendant_pids(root_pid: int) -> tuple[int, ...]:
    """Return current descendants deepest-first from one bounded ``ps`` snapshot."""
    if os.name != "posix" or _POSIX_PS is None:
        return ()
    try:
        completed = subprocess.run(
            (_POSIX_PS, "-e", "-o", "pid=", "-o", "ppid="),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=_PROCESS_SNAPSHOT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ()

    children: dict[int, list[int]] = {}
    for line in completed.stdout.splitlines():
        try:
            pid, parent = (int(value) for value in line.split())
        except ValueError:
            continue
        children.setdefault(parent, []).append(pid)

    depths: dict[int, int] = {root_pid: 0}
    pending = [root_pid]
    while pending:
        parent = pending.pop()
        depth = depths[parent]
        for pid in children.get(parent, ()):
            if pid not in depths:
                depths[pid] = depth + 1
                pending.append(pid)
    return tuple(
        pid
        for pid, _ in sorted(
            ((pid, depth) for pid, depth in depths.items() if pid != root_pid),
            key=lambda item: (-item[1], item[0]),
        )
    )


def _stop_process_tree(
    process: subprocess.Popen[bytes], descendants: tuple[int, ...]
) -> None:
    """Kill the immediate snapshot deepest-first, then the original process group."""
    for pid in descendants:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            continue
    _stop_process_group(process)


def _stop_process_group(process: subprocess.Popen[bytes]) -> None:
    """Kill the original isolated process group without following later ancestry."""
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return


def _poll_cleanup(process: subprocess.Popen[bytes], descendants: tuple[int, ...]) -> None:
    """Give the fixed cleanup targets a short, bounded opportunity to exit."""
    deadline = time.monotonic() + _POST_KILL_WAIT_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None and not _pids_are_alive(descendants):
            return
        time.sleep(_PROCESS_POLL_SECONDS)
    process.poll()


def _pids_are_alive(pids: tuple[int, ...]) -> bool:
    for pid in pids:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            continue
        except PermissionError:
            return True
        return True
    return False


__all__ = [
    "BOOTSTRAP_FILENAME",
    "DEFAULT_TIMEOUT_SECONDS",
    "GroupRun",
    "IsolatedAttemptScorer",
    "MAX_OUTPUT_BYTES",
    "RUNNER_DIRECTORY",
    "RUNNER_FILENAME",
    "install_attempt_runner",
]
