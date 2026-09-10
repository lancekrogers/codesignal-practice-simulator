"""Shared discovery for interpreters that can build and install this project."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


_BASE_PACKAGING_MODULES = ("setuptools", "pip", "venv", "wheel")


def discover_packaging_interpreter(*, require_build: bool = False) -> Path | None:
    """Return the first usable interpreter, or ``None`` if none is installed."""
    required_modules = _required_modules(require_build=require_build)
    candidates: list[str] = []
    configured = os.environ.get("ASSET_BUILDER")
    if configured:
        candidates.append(configured)
    candidates.append(sys.executable)
    candidates.extend(
        name
        for name in ("python3.12", "python3.11", "python3.10")
        if (resolved := shutil.which(name)) is not None
    )
    seen: set[Path] = set()
    for candidate in candidates:
        executable = Path(shutil.which(candidate) or candidate).absolute()
        if executable in seen or not executable.is_file():
            continue
        seen.add(executable)
        if _probe(executable, required_modules=required_modules):
            return executable
    return None


def _required_modules(*, require_build: bool) -> tuple[str, ...]:
    if require_build:
        return (*_BASE_PACKAGING_MODULES, "build")
    return _BASE_PACKAGING_MODULES


def packaging_prerequisite_error(*, require_build: bool = False) -> str:
    """Explain how to select an interpreter capable of the requested check."""
    required = ", ".join(_required_modules(require_build=require_build))
    return (
        f"no Python interpreter satisfies packaging prerequisites: {required}. "
        "Set ASSET_BUILDER to a capable interpreter. To provision one, run "
        "`<python> -m ensurepip --upgrade` if pip is missing, then "
        "`<python> -m pip install --upgrade setuptools wheel"
        f"{' build' if require_build else ''}`."
    )


def _probe(interpreter: Path, *, required_modules: tuple[str, ...]) -> bool:
    probe = subprocess.run(
        [
            str(interpreter),
            "-W",
            "ignore",
            "-c",
            "import " + ", ".join(required_modules),
        ],
        cwd=tempfile.gettempdir(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return probe.returncode == 0


__all__ = [
    "discover_packaging_interpreter",
    "packaging_prerequisite_error",
]
