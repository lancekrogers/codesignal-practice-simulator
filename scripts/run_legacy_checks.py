#!/usr/bin/env python3
"""Run the canonical local checks for migrated compatibility material."""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "docs/migration-manifest.json"
FIXTURE_CACHE_PATH = Path(".cache/codesignal-fixtures/6aab304")


def commands(interpreter: str) -> list[list[str]]:
    """Return the ordered, user-authored compatibility checks."""
    command_list = [
        [
            interpreter,
            "scripts/verify_manifest.py",
            "--manifest",
            MANIFEST,
            "--scope",
            scope,
        ]
        for scope in ("tracked", "fixture-cache", "git-boundary")
    ]
    command_list.extend(
        [
            [interpreter, "solution/test_spec.py"],
            [interpreter, "solution/test_stages.py"],
        ]
    )
    command_list.extend(
        [
            [interpreter, "study/check.py", str(level), f"study/level{level}.py"]
            for level in range(1, 5)
        ]
    )
    return command_list


def fixture_cache_guidance(project_root: Path) -> str:
    """Return the recovery instruction for any fixture-cache verification failure."""
    return (
        "Rerun `python3 scripts/fetch_fixture.py --manifest "
        f"{MANIFEST}`: Validated fixture cache: {project_root / FIXTURE_CACHE_PATH}"
    )


def run_checks(
    project_root: Path = PROJECT_ROOT, interpreter: str | None = None
) -> int:
    """Run each check from the project root and stop at the first failure."""
    interpreter = interpreter or sys.executable
    for command in commands(interpreter):
        print(f"+ {shlex.join(command)}", flush=True)
        completed = subprocess.run(command, cwd=project_root, check=False)
        if completed.returncode:
            if command[-1] == "fixture-cache":
                print(fixture_cache_guidance(project_root), file=sys.stderr)
            return completed.returncode
    print("Canonical legacy checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_checks())
