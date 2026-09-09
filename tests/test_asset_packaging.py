"""Regression tests for incremental setuptools asset packaging."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from packaging_support import discover_packaging_interpreter


PROJECT = Path(__file__).resolve().parents[1]
STATIC = PROJECT / "src" / "codesignal_practice_simulator" / "web" / "static"
STATIC_PREFIX = "codesignal_practice_simulator/web/static/"


def _manifest() -> dict[str, dict[str, object]]:
    return json.loads((STATIC / "manifest.json").read_text(encoding="utf-8"))


def _run(
    command: list[str], *, cwd: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=os.environ.copy(),
        text=True,
        capture_output=True,
        check=False,
        timeout=180,
    )


def _copy_minimal_checkout(checkout: Path) -> None:
    for name in ("README.md", "pyproject.toml", "setup.py"):
        shutil.copy2(PROJECT / name, checkout / name)
    shutil.copytree(
        PROJECT / "src",
        checkout / "src",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )


def _static_members(names: list[str]) -> set[str]:
    return {
        name.removeprefix(STATIC_PREFIX)
        for name in names
        if name.startswith(STATIC_PREFIX) and not name.endswith("/")
    }


class IncrementalPackagingTests(unittest.TestCase):
    def test_source_overlap_fails_without_deleting_source_members(self) -> None:
        builder = discover_packaging_interpreter()
        if builder is None:
            self.skipTest("a Python interpreter with setuptools and pip is required")

        with tempfile.TemporaryDirectory(prefix="codesignal-package-overlap-") as directory:
            checkout = Path(directory) / "checkout"
            checkout.mkdir()
            _copy_minimal_checkout(checkout)
            sentinel = (
                checkout
                / "src"
                / "codesignal_practice_simulator"
                / "web"
                / "static"
                / "source-sentinel.txt"
            )
            sentinel.write_text("must remain\n", encoding="utf-8")
            built = _run(
                [
                    str(builder),
                    "setup.py",
                    "build_py",
                    "--build-lib",
                    str(checkout / "src"),
                ],
                cwd=checkout,
            )
            self.assertNotEqual(built.returncode, 0)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "must remain\n")

    def test_symlinked_build_output_fails_without_touching_outside(self) -> None:
        builder = discover_packaging_interpreter()
        if builder is None:
            self.skipTest("a Python interpreter with setuptools and pip is required")

        with tempfile.TemporaryDirectory(prefix="codesignal-package-symlink-") as directory:
            root = Path(directory)
            checkout = root / "checkout"
            outside = root / "outside"
            checkout.mkdir()
            outside.mkdir()
            _copy_minimal_checkout(checkout)
            sentinel = outside / "outside-sentinel.txt"
            sentinel.write_text("must remain\n", encoding="utf-8")
            build = checkout / "build"
            build.mkdir()
            (build / "lib").symlink_to(outside, target_is_directory=True)
            built = _run(
                [
                    str(builder),
                    "setup.py",
                    "build_py",
                    "--build-lib",
                    str(build / "lib"),
                ],
                cwd=checkout,
            )
            self.assertNotEqual(built.returncode, 0)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "must remain\n")

    def test_symlinked_static_member_fails_without_touching_target(self) -> None:
        builder = discover_packaging_interpreter()
        if builder is None:
            self.skipTest("a Python interpreter with setuptools and pip is required")

        with tempfile.TemporaryDirectory(prefix="codesignal-package-member-") as directory:
            root = Path(directory)
            checkout = root / "checkout"
            checkout.mkdir()
            _copy_minimal_checkout(checkout)
            target = root / "member-sentinel.txt"
            target.write_text("must remain\n", encoding="utf-8")
            static_root = (
                checkout
                / "build"
                / "lib"
                / "codesignal_practice_simulator"
                / "web"
                / "static"
            )
            static_root.mkdir(parents=True)
            (static_root / "stale.txt").symlink_to(target)
            built = _run(
                [
                    str(builder),
                    "setup.py",
                    "build_py",
                    "--build-lib",
                    str(checkout / "build" / "lib"),
                ],
                cwd=checkout,
            )
            self.assertNotEqual(built.returncode, 0)
            self.assertEqual(target.read_text(encoding="utf-8"), "must remain\n")

    def test_stale_hashed_assets_are_not_wheel_or_install_members(self) -> None:
        builder = discover_packaging_interpreter()
        if builder is None:
            self.skipTest("a Python interpreter with setuptools and pip is required")

        with tempfile.TemporaryDirectory(prefix="codesignal-package-cache-") as directory:
            root = Path(directory)
            checkout = root / "checkout"
            checkout.mkdir()
            _copy_minimal_checkout(checkout)
            stale_root = (
                checkout
                / "build"
                / "lib"
                / "codesignal_practice_simulator"
                / "web"
                / "static"
            )
            stale_root.mkdir(parents=True)
            for name in ("app-OLDHASH.js", "styles-OLDHASH.css", "unlisted.txt"):
                (stale_root / name).write_bytes(b"stale hashed asset")

            wheel_directory = root / "wheel"
            built = _run(
                [
                    str(builder),
                    "-m",
                    "pip",
                    "wheel",
                    "--no-deps",
                    "--no-build-isolation",
                    "--wheel-dir",
                    str(wheel_directory),
                    str(checkout),
                ],
                cwd=root,
            )
            self.assertEqual(built.returncode, 0, built.stderr)
            wheel = next(wheel_directory.glob("*.whl"))
            expected = _manifest()
            expected_members = set(expected) | {"__init__.py"}

            with zipfile.ZipFile(wheel) as archive:
                static_members = _static_members(archive.namelist())
                self.assertEqual(static_members, expected_members)
                for name in expected:
                    self.assertEqual(
                        archive.read(f"{STATIC_PREFIX}{name}"),
                        (STATIC / name).read_bytes(),
                        name,
                    )

            installed = root / "installed"
            result = _run(
                [
                    str(builder),
                    "-m",
                    "pip",
                    "install",
                    "--no-deps",
                    "--target",
                    str(installed),
                    str(wheel),
                ],
                cwd=root,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            installed_static = (
                installed
                / "codesignal_practice_simulator"
                / "web"
                / "static"
            )
            self.assertEqual(
                {
                    path.name
                    for path in installed_static.iterdir()
                    if path.is_file()
                },
                expected_members,
            )
            for name in expected:
                self.assertEqual(
                    (installed_static / name).read_bytes(),
                    (STATIC / name).read_bytes(),
                    name,
                )


if __name__ == "__main__":
    unittest.main()
