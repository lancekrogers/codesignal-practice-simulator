"""Setuptools hooks for packaging the simulator."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re

from setuptools import setup
from setuptools.command.build_py import build_py


PACKAGE = "codesignal_practice_simulator"
ASSET_SUFFIXES = {".css", ".html", ".js", ".json", ".svg", ".ttf", ".txt"}
SAFE_MEMBER = re.compile(r"^[A-Za-z0-9._-]+$")


class CleanStaticBuildPy(build_py):
    """Prevent removed hashed assets from surviving incremental builds."""

    def run(self) -> None:
        self._clean_stale_members()
        super().run()

    def _clean_stale_members(self) -> None:
        source_static = Path(__file__).resolve().parent / "src" / PACKAGE / "web" / "static"
        manifest = _read_manifest(source_static / "manifest.json")
        output_static = Path(self.build_lib) / PACKAGE / "web" / "static"
        _validate_output_path(output_static, source_static)
        if not output_static.exists() and not output_static.is_symlink():
            return
        if output_static.is_symlink() or not output_static.is_dir():
            raise RuntimeError("refusing to clean an unsafe static build output")
        _remove_manifest_members(output_static, manifest)


def _read_manifest(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RuntimeError("static asset manifest is unavailable") from error
    if not isinstance(value, dict) or not value:
        raise RuntimeError("static asset manifest is invalid")
    for name in value:
        if (
            not isinstance(name, str)
            or not SAFE_MEMBER.fullmatch(name)
            or name in {".", ".."}
            or Path(name).suffix not in ASSET_SUFFIXES
        ):
            raise RuntimeError("static asset manifest contains an unsafe member")
    return value


def _validate_output_path(output: Path, source_static: Path) -> None:
    output = Path(os.path.abspath(output))
    source = source_static.resolve()
    if _overlaps(output, source) or _overlaps(output.resolve(), source):
        raise RuntimeError("refusing to clean a build output overlapping source")
    _assert_no_symlink_ancestors(output)


def _assert_no_symlink_ancestors(path: Path) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            if current.is_symlink():
                raise RuntimeError("refusing to clean through a symlinked build path")
        except OSError as error:
            raise RuntimeError("unable to validate build output path") from error


def _overlaps(first: Path, second: Path) -> bool:
    try:
        return first.is_relative_to(second) or second.is_relative_to(first)
    except ValueError:
        return False


def _remove_manifest_members(output_static: Path, manifest: dict[str, object]) -> None:
    managed_suffixes = {Path(name).suffix for name in manifest}
    for member in output_static.iterdir():
        if member.is_symlink():
            raise RuntimeError("refusing to clean a symlinked static member")
        if member.name == "__init__.py" or member.name in manifest:
            continue
        if not SAFE_MEMBER.fullmatch(member.name):
            continue
        if member.is_file() and member.suffix in managed_suffixes:
            member.unlink()


setup(cmdclass={"build_py": CleanStaticBuildPy})
