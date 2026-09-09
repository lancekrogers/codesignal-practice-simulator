"""Run the real-browser offline smoke test against an installed wheel."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_assets import check_static_root  # noqa: E402
from packaging_support import discover_packaging_interpreter  # noqa: E402


PROJECT = Path(__file__).resolve().parents[1]


def run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    completed = subprocess.run(command, cwd=cwd, env=env, check=False)
    if completed.returncode:
        raise SystemExit(completed.returncode)


def main() -> int:
    python = discover_packaging_interpreter()
    if python is None:
        print("a Python interpreter with setuptools is required", file=sys.stderr)
        return 2
    npm = shutil.which("npm")
    if npm is None:
        print("npm is required for the packaged browser check", file=sys.stderr)
        return 2
    check_static_root(
        PROJECT
        / "src"
        / "codesignal_practice_simulator"
        / "web"
        / "static"
    )
    with tempfile.TemporaryDirectory(prefix="codesignal-browser-wheel-") as directory:
        root = Path(directory)
        wheel_dir = root / "wheel"
        run(
            [
                str(python),
                "-m",
                "pip",
                "wheel",
                "--no-deps",
                "--no-build-isolation",
                "--wheel-dir",
                str(wheel_dir),
                str(PROJECT),
            ],
            cwd=root,
        )
        wheel = next(wheel_dir.glob("*.whl"))
        environment = root / "environment"
        run([str(python), "-m", "venv", str(environment)], cwd=root)
        executable_dir = environment / ("Scripts" if os.name == "nt" else "bin")
        environment_python = executable_dir / (
            "python.exe" if os.name == "nt" else "python"
        )
        environment_pip = executable_dir / ("pip.exe" if os.name == "nt" else "pip")
        run(
            [
                str(environment_pip),
                "install",
                "--no-deps",
                str(wheel),
            ],
            cwd=root,
        )
        probe_environment = os.environ.copy()
        probe_environment.pop("PYTHONPATH", None)
        probe_environment["SIMULATOR_SOURCE_ROOT"] = str(PROJECT)
        run(
            [
                str(environment_python),
                "-c",
                (
                    "from pathlib import Path; import sys; "
                    "import codesignal_practice_simulator as package; "
                    "from codesignal_practice_simulator.web import resources; "
                    "checkout = Path(__import__('os').environ['SIMULATOR_SOURCE_ROOT']).resolve(); "
                    "prefix = Path(sys.prefix).resolve(); "
                    "origins = [Path(package.__file__).resolve(), "
                    "Path(resources.__file__).resolve()]; "
                    "assert all(origin.is_relative_to(prefix) for origin in origins); "
                    "assert all(not origin.is_relative_to(checkout) for origin in origins)"
                ),
            ],
            cwd=root,
            env=probe_environment,
        )
        output = root / "playwright-output"
        browser_environment = os.environ.copy()
        browser_environment.update(
            {
                "SIMULATOR_PYTHON": str(environment_python),
                "SIMULATOR_SERVER_SCRIPT": "webui/tests/installed_fixture_server.py",
                "SIMULATOR_SOURCE_ROOT": str(PROJECT),
                "PYTHONPATH": "",
            }
        )
        run(
            [
                npm,
                "--prefix",
                str(PROJECT / "webui"),
                "run",
                "test:browser",
                "--",
                "--reporter=line",
                "--output",
                str(output),
            ],
            cwd=PROJECT,
            env=browser_environment,
        )
        if output.exists():
            shutil.rmtree(output)
    print(f"packaged wheel browser smoke test passed with {python}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
