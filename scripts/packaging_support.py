"""Shared discovery for interpreters that can build and install this project."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def discover_packaging_interpreter(*, require_build: bool = False) -> Path | None:
    """Return the first usable interpreter, or ``None`` if none is installed."""
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
        if _probe(executable, require_build=require_build):
            return executable
    return None


def _probe(interpreter: Path, *, require_build: bool) -> bool:
    modules = ["setuptools", "pip", "venv"]
    if require_build:
        modules.append("build")
    probe = subprocess.run(
        [
            str(interpreter),
            "-W",
            "ignore",
            "-c",
            "import " + ", ".join(modules),
        ],
        cwd=tempfile.gettempdir(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return probe.returncode == 0


__all__ = ["discover_packaging_interpreter"]
