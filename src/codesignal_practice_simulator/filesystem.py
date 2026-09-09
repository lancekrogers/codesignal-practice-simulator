"""Small injectable filesystem surface used by durable runtime services."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import BinaryIO, Protocol


class Filesystem(Protocol):
    """Filesystem operations that may fail during a workspace transaction."""

    def mkdir(self, path: Path, *, parents: bool = False, exist_ok: bool = False) -> None:
        """Create a directory."""

    def copyfile(self, source: Path, destination: Path) -> None:
        """Copy a regular file without interpreting its contents."""

    def read_bytes(self, path: Path) -> bytes:
        """Read a file's bytes."""

    def write_bytes(self, path: Path, data: bytes) -> None:
        """Write complete bytes to an already-created file path."""

    def append_bytes(self, path: Path, data: bytes) -> None:
        """Append bytes to a file."""

    def flush_file(self, path: Path) -> None:
        """Flush a file's content to local storage."""

    def replace(self, source: Path, destination: Path) -> None:
        """Atomically replace a sibling destination."""

    def unlink(self, path: Path) -> None:
        """Remove a file."""

    def remove_tree(self, path: Path) -> None:
        """Remove a transaction-owned directory tree."""

    def open_lock(self, path: Path) -> BinaryIO:
        """Open a lock file, creating it if necessary."""


class LocalFilesystem:
    """Production implementation backed exclusively by the standard library."""

    def mkdir(self, path: Path, *, parents: bool = False, exist_ok: bool = False) -> None:
        path.mkdir(parents=parents, exist_ok=exist_ok)

    def copyfile(self, source: Path, destination: Path) -> None:
        shutil.copyfile(source, destination)

    def read_bytes(self, path: Path) -> bytes:
        return path.read_bytes()

    def write_bytes(self, path: Path, data: bytes) -> None:
        with path.open("wb") as stream:
            stream.write(data)
            stream.flush()

    def append_bytes(self, path: Path, data: bytes) -> None:
        with path.open("ab") as stream:
            stream.write(data)
            stream.flush()

    def flush_file(self, path: Path) -> None:
        with path.open("rb") as stream:
            os.fsync(stream.fileno())

    def replace(self, source: Path, destination: Path) -> None:
        os.replace(source, destination)

    def unlink(self, path: Path) -> None:
        path.unlink()

    def remove_tree(self, path: Path) -> None:
        shutil.rmtree(path)

    def open_lock(self, path: Path) -> BinaryIO:
        return path.open("a+b")
