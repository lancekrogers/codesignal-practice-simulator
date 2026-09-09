"""Packaged FETCH_ONLY fixture setup for installed simulator runtimes."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from importlib import resources
from pathlib import Path, PurePosixPath
from typing import Any, Callable
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen
from uuid import uuid4


RUNTIME_MANIFEST_PACKAGE = "codesignal_practice_simulator.resources"
RUNTIME_MANIFEST_NAME = "fixture-manifest.json"
Download = Callable[[str], bytes]


class FixtureSetupError(Exception):
    """The packaged fixture metadata or setup operation is invalid."""


def load_runtime_manifest() -> dict[str, Any]:
    """Return the small, non-vendor manifest shipped with the wheel."""
    try:
        resource = resources.files(RUNTIME_MANIFEST_PACKAGE).joinpath(
            RUNTIME_MANIFEST_NAME
        )
        data = json.loads(resource.read_text(encoding="utf-8"))
    except (
        FileNotFoundError,
        ModuleNotFoundError,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as error:
        raise FixtureSetupError("installed fixture metadata is unavailable") from error
    _validate_manifest(data)
    return data


def runtime_cache_root(
    workspace_root: Path, manifest: dict[str, Any] | None = None
) -> Path:
    """Return the workspace-local cache location declared by packaged metadata."""
    manifest = load_runtime_manifest() if manifest is None else manifest
    try:
        relative = _relative_path(
            manifest["fixture_cache_root"], "fixture_cache_root"
        )
        _reject_lexical_symlinks(workspace_root, relative)
        workspace = Path(workspace_root).resolve()
        cache = workspace.joinpath(*relative.parts).resolve()
    except (KeyError, OSError) as error:
        raise FixtureSetupError("workspace fixture cache path is invalid") from error
    if workspace != cache and workspace not in cache.parents:
        raise FixtureSetupError("workspace fixture cache escapes its root")
    return cache


def _reject_lexical_symlinks(
    workspace_root: Path, relative: PurePosixPath
) -> None:
    """Reject symlink traversal before resolving the cache destination."""
    lexical_workspace = Path(os.path.abspath(workspace_root))
    current = lexical_workspace
    components = relative.parts
    try:
        if current.is_symlink():
            raise FixtureSetupError(
                "workspace fixture cache path must not traverse symlinks"
            )
        for component in components:
            current /= component
            if current.is_symlink():
                raise FixtureSetupError(
                    "workspace fixture cache path must not traverse symlinks"
                )
    except OSError as error:
        raise FixtureSetupError("workspace fixture cache path is invalid") from error


def populate_runtime_fixture(
    workspace_root: Path,
    *,
    source_root: Path | None = None,
    downloader: Download | None = None,
) -> Path:
    """Fetch, hash-validate, and atomically publish the runtime fixture cache."""
    manifest = load_runtime_manifest()
    cache_root = runtime_cache_root(workspace_root, manifest)
    _validate_cache_destination(workspace_root, cache_root)
    downloader = _download if downloader is None else downloader
    try:
        cache_root.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(
            tempfile.mkdtemp(
                prefix=f".{cache_root.name}.staging-", dir=cache_root.parent
            )
        )
    except OSError as error:
        raise FixtureSetupError("cannot create fixture setup staging directory") from error

    try:
        for record in manifest["fetches"]:
            destination = staging.joinpath(
                *_relative_path(record["cache_path"], "cache_path").parts
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            data = (
                _read_source_file(source_root, record["upstream_path"])
                if source_root is not None
                else downloader(_download_url(manifest, record["repository_path"]))
            )
            destination.write_bytes(data)
            if _sha256(data) != record["sha256"]:
                raise FixtureSetupError(
                    f"fixture hash mismatch for {record['upstream_path']}"
                )
        _verify_staging(manifest, staging)
        _publish(staging, cache_root)
    except FixtureSetupError:
        _remove_path(staging)
        raise
    except OSError as error:
        _remove_path(staging)
        raise FixtureSetupError("cannot populate fixture setup staging directory") from error
    except Exception:
        _remove_path(staging)
        raise
    return cache_root


def _validate_cache_destination(workspace_root: Path, cache_root: Path) -> None:
    """Keep fixture setup from replacing an attempts root through a symlink."""
    try:
        workspace = Path(workspace_root).resolve()
        attempts = (workspace / "attempts").resolve()
    except OSError as error:
        raise FixtureSetupError("workspace attempts path is invalid") from error
    if _paths_overlap(attempts, cache_root):
        raise FixtureSetupError("attempts directory must not overlap the fixture cache")
    lexical_attempts = workspace / "attempts"
    if lexical_attempts.is_symlink() or (
        lexical_attempts.exists() and not lexical_attempts.is_dir()
    ):
        raise FixtureSetupError("attempts directory must be a non-symlink directory")


def _validate_manifest(data: object) -> None:
    if not isinstance(data, dict):
        raise FixtureSetupError("installed fixture metadata is invalid")
    try:
        _relative_path(data["fixture_cache_root"], "fixture_cache_root")
        upstream = data["upstream"]
        fetches = data["fetches"]
    except KeyError as error:
        raise FixtureSetupError("installed fixture metadata is invalid") from error
    if not isinstance(upstream, dict) or not isinstance(
        upstream.get("repository"), str
    ):
        raise FixtureSetupError("installed fixture metadata is invalid")
    if not isinstance(upstream.get("commit"), str) or not isinstance(fetches, list):
        raise FixtureSetupError("installed fixture metadata is invalid")
    if len(fetches) != 7:
        raise FixtureSetupError("installed fixture metadata is invalid")
    cache_paths: set[str] = set()
    for record in fetches:
        if not isinstance(record, dict):
            raise FixtureSetupError("installed fixture metadata is invalid")
        for key in ("upstream_path", "repository_path", "cache_path"):
            _relative_path(record.get(key), key)
        digest = record.get("sha256")
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise FixtureSetupError("installed fixture metadata is invalid")
        cache_path = record["cache_path"]
        if cache_path in cache_paths:
            raise FixtureSetupError("installed fixture metadata is invalid")
        cache_paths.add(cache_path)


def _relative_path(value: object, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value:
        raise FixtureSetupError(f"{label} must be a normalized relative path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or "." in path.parts
        or ".." in path.parts
        or str(path) != value
    ):
        raise FixtureSetupError(f"{label} must be a normalized relative path")
    return path


def _read_source_file(source_root: Path, upstream_path: object) -> bytes:
    source = Path(source_root).resolve()
    if not source.is_dir():
        raise FixtureSetupError(f"offline source is not a directory: {source}")
    candidate = source.joinpath(
        *_relative_path(upstream_path, "upstream_path").parts
    )
    try:
        resolved = candidate.resolve(strict=True)
        if (
            candidate.is_symlink()
            or not candidate.is_file()
            or source not in resolved.parents
        ):
            raise FixtureSetupError(f"offline source file is unavailable: {upstream_path}")
        return candidate.read_bytes()
    except OSError as error:
        raise FixtureSetupError(f"offline source file is unavailable: {upstream_path}") from error


def _download_url(manifest: dict[str, Any], repository_path: object) -> str:
    repository = manifest["upstream"]["repository"]
    commit = manifest["upstream"]["commit"]
    return (
        f"https://raw.githubusercontent.com/{repository}/{commit}/"
        f"{quote(str(repository_path))}"
    )


def _download(url: str) -> bytes:
    try:
        with urlopen(url, timeout=30) as response:
            return response.read()
    except (OSError, URLError) as error:
        raise FixtureSetupError(f"fixture download failed: {error}") from error


def _verify_staging(manifest: dict[str, Any], staging: Path) -> None:
    expected = {record["cache_path"] for record in manifest["fetches"]}
    actual: set[str] = set()
    for path in staging.rglob("*"):
        if path.is_symlink():
            raise FixtureSetupError("fixture staging contains a symlink")
        if path.is_file():
            actual.add(path.relative_to(staging).as_posix())
    if actual != expected:
        raise FixtureSetupError("fixture staging is incomplete")


def _publish(staging: Path, cache_root: Path) -> None:
    if cache_root.is_symlink():
        raise FixtureSetupError(
            "workspace fixture cache path must not traverse symlinks"
        )
    backup = cache_root.with_name(f".{cache_root.name}.previous-{uuid4().hex}")
    moved_existing = False
    try:
        if cache_root.exists() or cache_root.is_symlink():
            os.replace(cache_root, backup)
            moved_existing = True
        os.replace(staging, cache_root)
    except OSError as error:
        if moved_existing and not (cache_root.exists() or cache_root.is_symlink()):
            os.replace(backup, cache_root)
        raise FixtureSetupError("could not publish validated fixture cache") from error
    if moved_existing:
        _remove_path(backup)


def _remove_path(path: Path) -> None:
    try:
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.exists():
            shutil.rmtree(path)
    except OSError:
        pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


__all__ = [
    "FixtureSetupError",
    "load_runtime_manifest",
    "populate_runtime_fixture",
    "runtime_cache_root",
]
