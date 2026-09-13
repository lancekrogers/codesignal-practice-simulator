"""Run the real-browser offline smoke test against an installed wheel."""

from __future__ import annotations

import hashlib
import json
import os
import queue
import re
import signal
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_assets import check_static_root  # noqa: E402
from packaging_support import (  # noqa: E402
    discover_packaging_interpreter,
    packaging_prerequisite_error,
)


PROJECT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "codesignal_practice_simulator"
STATIC = PROJECT / "src" / "codesignal_practice_simulator" / "web" / "static"
STATIC_PREFIX = f"{PACKAGE_NAME}/web/static/"
DECLARED_RUNTIME_RESOURCES = frozenset({"resources/fixture-manifest.json"})
# Bundled original exercises live at resources/assessments/<id>/ and may contain
# exactly the candidate-facing files plus their content manifest. Anything else
# under that prefix (a solution, a note, a nested directory) fails the archive.
# Development oracle filenames, wherever they might appear in an archive.
FORBIDDEN_ARCHIVE_SUFFIXES = ("_reference.py", "_solution.py", "_oracle.py")
PACKAGED_ASSESSMENTS_PREFIX = "resources/assessments/"
# Same shape the registry enforces on input directory segments: no dots, no
# uppercase, so ".." or "Records_Demo" never match.
PACKAGED_ASSESSMENT_DIRECTORY = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")
PACKAGED_ASSESSMENT_MEMBERS = frozenset(
    {
        "level1.md",
        "level2.md",
        "level3.md",
        "level4.md",
        "simulation.py",
        "test_simulation.py",
        "content-manifest.json",
    }
)
FORBIDDEN_ARCHIVE_PARTS = frozenset(
    {
        ".cache",
        ".npm",
        ".pytest_cache",
        ".playwright",
        ".tmp",
        "__pycache__",
        "attempts",
        "build",
        "dist",
        "fixture-cache",
        "node_modules",
        "npm-cache",
        "npm_cache",
        "oracles",
        "playwright-report",
        "playwright-reports",
        "playwright-cache",
        "reference",
        "references",
        "solution",
        "solutions",
        "study",
        "test-results",
        "vendor",
    }
)


def run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        text=capture,
        capture_output=capture,
    )
    if completed.returncode:
        raise SystemExit(completed.returncode)
    return completed


def inspect_archives(
    wheel: Path,
    source: Path,
    expected_hashes: dict[str, str],
) -> dict[str, int]:
    expected = set(expected_hashes) | {"__init__.py"}
    with zipfile.ZipFile(wheel) as archive:
        wheel_members = archive.namelist()
        _assert_archive_paths(wheel_members)
        _assert_runtime_package_resources(
            [member.filename for member in archive.infolist() if not member.is_dir()],
            prefix=f"{PACKAGE_NAME}/",
            static_prefix=STATIC_PREFIX,
        )
        wheel_static = _static_members(wheel_members, STATIC_PREFIX)
        if wheel_static != expected:
            raise RuntimeError("wheel static members do not match manifest")
        for name, digest in expected_hashes.items():
            body = archive.read(f"{STATIC_PREFIX}{name}")
            if hashlib.sha256(body).hexdigest() != digest:
                raise RuntimeError(f"wheel asset digest mismatch: {name}")
    with tarfile.open(source, "r:gz") as archive:
        source_members = archive.getnames()
        _assert_archive_paths(source_members)
        source_prefix = "/src/" + STATIC_PREFIX
        _assert_runtime_package_resources(
            [member.name for member in archive.getmembers() if member.isfile()],
            prefix="/src/" + f"{PACKAGE_NAME}/",
            static_prefix=source_prefix,
        )
        source_static = _static_members(source_members, source_prefix)
        if source_static != expected:
            raise RuntimeError("sdist static members do not match manifest")
        for name, digest in expected_hashes.items():
            member = next(
                item
                for item in archive.getmembers()
                if item.name.endswith(source_prefix + name)
            )
            body = archive.extractfile(member).read()
            if hashlib.sha256(body).hexdigest() != digest:
                raise RuntimeError(f"sdist asset digest mismatch: {name}")
    _assert_package_data_rules(expected_hashes)
    return {
        "sdist_members": len(source_members),
        "wheel_members": len(wheel_members),
        "static_members": len(expected),
    }


def _assert_archive_paths(members: list[str]) -> None:
    if len(members) != len(set(members)):
        raise RuntimeError("archive contains duplicate paths")
    for member in members:
        parts = {part.lower() for part in member.replace("\\", "/").split("/")}
        if parts & FORBIDDEN_ARCHIVE_PARTS:
            raise RuntimeError(f"archive contains forbidden path: {member}")
        if member.lower().endswith(FORBIDDEN_ARCHIVE_SUFFIXES):
            raise RuntimeError(f"archive contains a development oracle: {member}")


def _static_members(members: list[str], prefix: str) -> set[str]:
    return {
        member.split(prefix, 1)[1]
        for member in members
        if prefix in member and not member.endswith("/")
    }


def _assert_runtime_package_resources(
    members: list[str],
    *,
    prefix: str,
    static_prefix: str,
) -> None:
    for member in members:
        if prefix not in member:
            continue
        relative = member.split(prefix, 1)[1]
        if relative.startswith(PACKAGED_ASSESSMENTS_PREFIX):
            # Checked before the generic .py rule so a bundled solution.py can
            # never ride along as ordinary package code.
            parts = relative[len(PACKAGED_ASSESSMENTS_PREFIX):].split("/")
            if (
                len(parts) != 2
                or PACKAGED_ASSESSMENT_DIRECTORY.fullmatch(parts[0]) is None
                or parts[1] not in PACKAGED_ASSESSMENT_MEMBERS
            ):
                raise RuntimeError(
                    "archive contains unexpected packaged assessment member: "
                    f"{relative}"
                )
            continue
        if (
            relative.endswith(".py")
            or static_prefix in member
            or relative in DECLARED_RUNTIME_RESOURCES
        ):
            continue
        raise RuntimeError(
            "archive contains unexpected non-static package resource member: "
            f"{relative}"
        )


def _assert_package_data_rules(expected_hashes: dict[str, str]) -> None:
    configuration = (PROJECT / "pyproject.toml").read_text(encoding="utf-8")
    suffixes = {Path(name).suffix for name in expected_hashes}
    missing = sorted(
        suffix
        for suffix in suffixes
        if f'"web/static/*{suffix}"' not in configuration
    )
    if missing:
        raise RuntimeError(f"pyproject package-data rules omit: {missing}")


def _runtime_environment(executable_dir: Path) -> dict[str, str]:
    environment = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH"):
        environment.pop(name, None)
    environment.update(
        {
            "PATH": str(executable_dir),
            "PYTHONNOUSERSITE": "1",
            "SIMULATOR_DENY_EXTERNAL_NETWORK": "1",
            "SIMULATOR_REQUIRE_ISOLATION": "1",
            "SIMULATOR_RUNTIME_PATH": str(executable_dir),
            "SIMULATOR_SOURCE_ROOT": str(PROJECT),
        }
    )
    return environment


def probe_installation(
    python: Path,
    console: Path,
    root: Path,
    environment: dict[str, str],
    expected_hashes: dict[str, str],
) -> dict[str, object]:
    probe_environment = environment.copy()
    probe_environment["EXPECTED_HASHES"] = json.dumps(expected_hashes)
    script = (
        "import hashlib, importlib, json, os, shutil, sys; "
        "from pathlib import Path; "
        "import codesignal_practice_simulator as package; "
        "from codesignal_practice_simulator import cli; "
        "from codesignal_practice_simulator.web import resources; "
        "static = importlib.import_module(resources.STATIC_PACKAGE); "
        "expected = json.loads(os.environ['EXPECTED_HASHES']); "
        "origins = [Path(item.__file__).resolve() "
        "for item in (package, cli, resources, static)]; "
        "prefix = Path(sys.prefix).resolve(); "
        "checkout = Path(os.environ['SIMULATOR_SOURCE_ROOT']).resolve(); "
        "assert all(path.is_relative_to(prefix) for path in origins), origins; "
        "assert all(not path.is_relative_to(checkout) for path in origins), origins; "
        "assert all(not Path(value).resolve().is_relative_to(checkout) "
        "for value in sys.path if value), sys.path; "
        "assert 'PYTHONHOME' not in os.environ; "
        "assert 'PYTHONPATH' not in os.environ; "
        "assert not any(shutil.which(name) for name in ('node', 'npm', 'npx')); "
        "actual = {name: hashlib.sha256(resources.read_asset(name).body).hexdigest() "
        "for name in resources.asset_names()}; "
        "assert actual == expected, (actual, expected); "
        "print(json.dumps({'origins': [str(path) for path in origins], "
        "'assets': len(actual)}, sort_keys=True))"
    )
    completed = run(
        [str(python), "-c", script],
        cwd=root,
        env=probe_environment,
        capture=True,
    )
    run([str(console), "--version"], cwd=root, env=environment, capture=True)
    run(
        [str(python), "-m", "codesignal_practice_simulator", "--version"],
        cwd=root,
        env=environment,
        capture=True,
    )
    return json.loads(completed.stdout)


def copy_fixture_driver(root: Path) -> Path:
    driver = root / "fixture-driver"
    driver.mkdir()
    for name in ("installed_fixture_server.py", "fixture_controls.py"):
        shutil.copy2(PROJECT / "webui" / "tests" / name, driver / name)
    return driver / "installed_fixture_server.py"


def prepare_workspace(
    python: Path,
    fixture: Path,
    workspace: Path,
    root: Path,
    environment: dict[str, str],
) -> int:
    fixture_environment = environment.copy()
    fixture_environment.update(
        {
            "SIMULATOR_PREPARE_ONLY": "1",
            "SIMULATOR_WORKSPACE": str(workspace),
        }
    )
    completed = run(
        [str(python), str(fixture)],
        cwd=root,
        env=fixture_environment,
        capture=True,
    )
    records = json.loads(completed.stdout)["synthetic_records"]
    if records != 7:
        raise RuntimeError("installed fixture did not prepare seven records")
    return records


def probe_web_entrypoint(
    command: list[str],
    workspace: Path,
    root: Path,
    environment: dict[str, str],
    expected_hashes: dict[str, str],
) -> dict[str, object]:
    process = subprocess.Popen(
        [
            *command,
            "web",
            "--workspace-root",
            str(workspace),
            "--port",
            "0",
            "--no-open",
            "--json",
        ],
        cwd=root,
        env=environment,
        text=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        document = json.loads(_readline(process))
        url = urllib.parse.urlsplit(document["result"]["url"])
        if not document.get("ok") or url.hostname not in {"127.0.0.1", "::1"}:
            raise RuntimeError("installed web entry point did not bind loopback")
        origin = f"{url.scheme}://{url.netloc}"
        for name, digest in expected_hashes.items():
            with urllib.request.urlopen(f"{origin}/{name}", timeout=5) as response:
                if hashlib.sha256(response.read()).hexdigest() != digest:
                    raise RuntimeError(f"served asset digest mismatch: {name}")
        process.send_signal(signal.SIGINT)
        if process.wait(timeout=10) != 0:
            raise RuntimeError("installed web entry point exited unsuccessfully")
        return {"assets": len(expected_hashes), "origin": origin}
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)


def _readline(process: subprocess.Popen[str]) -> str:
    if process.stdout is None:
        raise RuntimeError("installed web entry point has no stdout")
    lines: queue.Queue[str] = queue.Queue(maxsize=1)
    thread = threading.Thread(
        target=lambda: lines.put(process.stdout.readline()),
        daemon=True,
    )
    thread.start()
    try:
        line = lines.get(timeout=10)
    except queue.Empty as error:
        raise RuntimeError("installed web entry point did not become ready") from error
    if not line:
        raise RuntimeError("installed web entry point exited before readiness")
    return line


def main() -> int:
    python = discover_packaging_interpreter(require_build=True)
    if python is None:
        print(packaging_prerequisite_error(require_build=True), file=sys.stderr)
        return 2
    npm = shutil.which("npm")
    if npm is None:
        print("npm is required for the packaged browser check", file=sys.stderr)
        return 2
    asset_report = check_static_root(STATIC)
    expected_hashes = dict(asset_report.asset_hashes)
    expected_hashes["manifest.json"] = asset_report.manifest_sha256
    summary: dict[str, object] = {
        "asset_count": len(expected_hashes),
        "builder": str(python),
    }
    with tempfile.TemporaryDirectory(prefix="codesignal-browser-wheel-") as directory:
        root = Path(directory)
        summary.update(
            verify_installed_package(
                python,
                Path(npm),
                root,
                expected_hashes,
            )
        )
    if root.exists():
        raise RuntimeError("packaged browser temporary root was not removed")
    summary["cleanup"] = "temporary wheel, venv, fixtures, attempts, and traces removed"
    print(json.dumps(summary, sort_keys=True))
    return 0


def verify_installed_package(
    builder: Path,
    npm: Path,
    root: Path,
    expected_hashes: dict[str, str],
) -> dict[str, object]:
    wheel, source = build_archives(builder, root)
    summary: dict[str, object] = {
        "archives": inspect_archives(wheel, source, expected_hashes)
    }
    python, pip, console, executable_dir = create_environment(builder, root)
    run(
        [
            str(pip),
            "install",
            "--no-index",
            "--no-deps",
            "--disable-pip-version-check",
            str(wheel),
        ],
        cwd=root,
    )
    environment = _runtime_environment(executable_dir)
    summary["installation"] = probe_installation(
        python, console, root, environment, expected_hashes
    )
    fixture = copy_fixture_driver(root)
    console_workspace = root / "console-workspace"
    console_workspace.mkdir()
    summary["console_web"] = probe_web_entrypoint(
        [str(console)], console_workspace, root, environment, expected_hashes
    )
    summary["module_web"] = probe_web_entrypoint(
        [str(python), "-m", "codesignal_practice_simulator"],
        console_workspace,
        root,
        environment,
        expected_hashes,
    )
    summary["synthetic_records"] = prepare_workspace(
        python,
        fixture,
        root / "fixture-workspace-proof",
        root,
        environment,
    )
    run_browser_suite(npm, python, console, fixture, executable_dir, root)
    summary["browser"] = {"reporters": "default", "status": "passed"}
    return summary


def build_archives(builder: Path, root: Path) -> tuple[Path, Path]:
    dist = root / "dist"
    run(
        [
            str(builder),
            "-m",
            "build",
            "--sdist",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(dist),
            str(PROJECT),
        ],
        cwd=root,
    )
    return next(dist.glob("*.whl")), next(dist.glob("*.tar.gz"))


def create_environment(
    builder: Path,
    root: Path,
) -> tuple[Path, Path, Path, Path]:
    environment = root / "environment"
    run([str(builder), "-m", "venv", str(environment)], cwd=root)
    executable_dir = environment / ("Scripts" if os.name == "nt" else "bin")
    suffix = ".exe" if os.name == "nt" else ""
    return (
        executable_dir / f"python{suffix}",
        executable_dir / f"pip{suffix}",
        executable_dir / f"codesignal-sim{suffix}",
        executable_dir,
    )


def run_browser_suite(
    npm: Path,
    python: Path,
    console: Path,
    fixture: Path,
    executable_dir: Path,
    root: Path,
) -> None:
    output = root / "playwright-output"
    environment = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH"):
        environment.pop(name, None)
    environment.update(
        {
            "SIMULATOR_CLI": str(console),
            "SIMULATOR_DENY_EXTERNAL_NETWORK": "1",
            "SIMULATOR_PYTHON": str(python),
            "SIMULATOR_REQUIRE_ISOLATION": "1",
            "SIMULATOR_RUNTIME_PATH": str(executable_dir),
            "SIMULATOR_SERVER_SCRIPT": str(fixture),
            "SIMULATOR_SOURCE_ROOT": str(PROJECT),
        }
    )
    run(
        [
            str(npm),
            "--prefix",
            str(PROJECT / "webui"),
            "run",
            "test:browser",
            "--",
            "--output",
            str(output),
        ],
        cwd=PROJECT,
        env=environment,
    )
    # The default cleanliness reporter has already rejected any residue other
    # than Playwright's allowed .last-run.json metadata before npm returns.
    if output.exists():
        shutil.rmtree(output)


if __name__ == "__main__":
    raise SystemExit(main())
