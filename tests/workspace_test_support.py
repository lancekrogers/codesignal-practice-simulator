"""Shared fixtures for transactional workspace tests."""

from __future__ import annotations

import hashlib
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from codesignal_practice_simulator.filesystem import LocalFilesystem  # noqa: E402
from codesignal_practice_simulator.models import (  # noqa: E402
    ACTIVE,
    FULL_DURATION_SECONDS,
    FULL_MODE,
    FULL_PROFILE,
    SESSION_SCHEMA_VERSION,
    AssessmentMetadata,
    ModeProfile,
    SessionState,
)
from codesignal_practice_simulator.workspace import (  # noqa: E402
    CACHE_INPUTS,
    ValidatedFixtureCache,
    WorkspaceManager,
)


def session(attempt_id: str) -> SessionState:
    started = datetime(2026, 9, 8, 19, tzinfo=timezone.utc)
    return SessionState(
        schema_version=SESSION_SCHEMA_VERSION,
        attempt_id=attempt_id,
        assessment=AssessmentMetadata("file_storage", "File Storage"),
        profile=ModeProfile(FULL_MODE, FULL_PROFILE, FULL_DURATION_SECONDS),
        started_at=started,
        deadline_at=started + timedelta(seconds=FULL_DURATION_SECONDS),
        status=ACTIVE,
        revision=0,
    )


def make_cache(root: Path) -> ValidatedFixtureCache:
    cache = root / "cache"
    hashes: dict[str, str] = {}
    contents = {"vendor-readme.md": b"vendor readme\n"}
    contents.update(
        {
            f"assessment/file_storage/{name}": f"fixture {name}\n".encode()
            for name in CACHE_INPUTS
        }
    )
    for relative, data in contents.items():
        path = cache.joinpath(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        hashes[relative] = hashlib.sha256(data).hexdigest()
    return ValidatedFixtureCache(cache, hashes)


def tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and not path.name.endswith(".lock")
    }


def tree_snapshot(root: Path) -> dict[str, tuple[str, bytes | str | None]]:
    """Capture paths and bytes, including symlinks, for mutation assertions."""
    snapshot: dict[str, tuple[str, bytes | str | None]] = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            snapshot[relative] = ("symlink", os.readlink(path))
        elif path.is_dir():
            snapshot[relative] = ("directory", None)
        elif path.is_file():
            snapshot[relative] = ("file", path.read_bytes())
    return snapshot


class RecordingFilesystem(LocalFilesystem):
    """Records and optionally fails exactly one mutating filesystem call."""

    def __init__(self, fail_operation: str | None = None, fail_call: int = 0) -> None:
        self.fail_operation = fail_operation
        self.fail_call = fail_call
        self.calls: dict[str, int] = {}

    def _record(self, operation: str) -> None:
        self.calls[operation] = self.calls.get(operation, 0) + 1
        if operation == self.fail_operation and self.calls[operation] == self.fail_call:
            raise OSError(f"injected {operation} failure {self.fail_call}")

    def mkdir(self, path: Path, *, parents: bool = False, exist_ok: bool = False) -> None:
        self._record("mkdir")
        super().mkdir(path, parents=parents, exist_ok=exist_ok)

    def copyfile(self, source: Path, destination: Path) -> None:
        self._record("copyfile")
        super().copyfile(source, destination)

    def write_bytes(self, path: Path, data: bytes) -> None:
        self._record("write_bytes")
        super().write_bytes(path, data)

    def flush_file(self, path: Path) -> None:
        self._record("flush_file")
        super().flush_file(path)

    def flush_directory(self, path: Path) -> None:
        self._record("flush_directory")
        super().flush_directory(path)

    def replace(self, source: Path, destination: Path) -> None:
        self._record("replace")
        super().replace(source, destination)


class PublishThenReportFilesystem(LocalFilesystem):
    """Report a failure after publishing one transaction-owned attempt."""

    def __init__(self, attempt_id: str) -> None:
        self.attempt_id = attempt_id
        self.failed = False

    def replace(self, source: Path, destination: Path) -> None:
        super().replace(source, destination)
        if destination.name == self.attempt_id and not self.failed:
            self.failed = True
            raise OSError("injected publish failure after replacement")


class PointerFlushThenReportFilesystem(LocalFilesystem):
    """Report one pointer-directory flush failure after replacement."""

    def __init__(self, attempts: Path) -> None:
        self.attempts = attempts.resolve()
        self.failed = False

    def flush_directory(self, path: Path) -> None:
        super().flush_directory(path)
        if path.resolve() == self.attempts and not self.failed:
            self.failed = True
            raise OSError("injected pointer flush failure after replacement")


class PersistentPointerFailureFilesystem(LocalFilesystem):
    """Fail pointer publication and restoration with either durable outcome."""

    def __init__(self, attempts: Path, *, final_pointer: str) -> None:
        self.attempts = attempts.resolve()
        self.final_pointer = final_pointer
        self.pointer_temp_writes = 0

    def write_bytes(self, path: Path, data: bytes) -> None:
        if self._is_pointer_temporary(path):
            self.pointer_temp_writes += 1
            if self.final_pointer == "new" and self.pointer_temp_writes > 1:
                raise OSError("injected pointer restore write failure")
        super().write_bytes(path, data)

    def flush_directory(self, path: Path) -> None:
        super().flush_directory(path)
        if path.resolve() == self.attempts:
            raise OSError("injected pointer flush failure after replacement")

    def unlink(self, path: Path) -> None:
        if (
            self.final_pointer == "new"
            and path.parent.resolve() == self.attempts
            and path.name == "active.json"
        ):
            raise OSError("injected pointer restore unlink failure")
        super().unlink(path)

    def _is_pointer_temporary(self, path: Path) -> bool:
        return (
            path.parent.resolve() == self.attempts
            and path.name.startswith(".active.json.")
            and path.name.endswith(".tmp")
        )


def workspace_environment() -> (
    tuple[tempfile.TemporaryDirectory[str], Path, ValidatedFixtureCache]
):
    temporary = tempfile.TemporaryDirectory()
    root = Path(temporary.name) / "workspace"
    root.mkdir()
    return temporary, root, make_cache(Path(temporary.name))


def existing_attempt(
    root: Path, cache: ValidatedFixtureCache
) -> tuple[WorkspaceManager, Path]:
    manager = WorkspaceManager(root, cache)
    old = manager.create_attempt(session(str(uuid4())))
    return manager, old


__all__ = [
    "CACHE_INPUTS",
    "PersistentPointerFailureFilesystem",
    "PointerFlushThenReportFilesystem",
    "PublishThenReportFilesystem",
    "RecordingFilesystem",
    "ValidatedFixtureCache",
    "WorkspaceManager",
    "existing_attempt",
    "make_cache",
    "session",
    "tree_bytes",
    "tree_snapshot",
    "workspace_environment",
]
