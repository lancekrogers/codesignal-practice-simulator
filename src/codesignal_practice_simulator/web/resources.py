"""Manifest-bound package resources for the loopback browser shell."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Mapping


STATIC_PACKAGE = "codesignal_practice_simulator.web.static"
MANIFEST_NAME = "manifest.json"
MAX_ASSET_BYTES = 4 * 1024 * 1024
MEDIA_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ttf": "font/ttf",
    ".txt": "text/plain; charset=utf-8",
}
HASHED_ASSET = re.compile(
    r"^(?:app-[A-Za-z0-9_-]+\.js|app-[A-Za-z0-9_-]+\.css"
    r"|styles-[A-Za-z0-9_-]+\.css|editor\.worker-[A-Za-z0-9_-]+\.js"
    r"|language\.worker-[A-Za-z0-9_-]+\.js"
    r"|[A-Za-z0-9_-]+-[A-Za-z0-9_-]+\.ttf)$"
)
HASHED_ASSET_PATTERNS = (
    re.compile(r"^app-[A-Za-z0-9_-]+\.js$"),
    re.compile(r"^app-[A-Za-z0-9_-]+\.css$"),
    re.compile(r"^styles-[A-Za-z0-9_-]+\.css$"),
    re.compile(r"^editor\.worker-[A-Za-z0-9_-]+\.js$"),
    re.compile(r"^language\.worker-[A-Za-z0-9_-]+\.js$"),
    re.compile(r"^[A-Za-z0-9_-]+-[A-Za-z0-9_-]+\.ttf$"),
)
REQUIRED_STABLE_ASSETS = frozenset(
    {
        "ASSET_PROVENANCE.txt",
        "NOTICE.txt",
        "app.js",
        "favicon.svg",
        "index.html",
        "manifest.json",
        "styles.css",
    }
)
SAFE_ASSET_NAME = re.compile(r"^[A-Za-z0-9._-]+$")
_PUBLICATION_LOCK_SUFFIX = ".publish.lock"
_PUBLICATION_RECLAIMER_SUFFIX = ".reclaimer"
_READER_WAIT_SECONDS = 10.0
_READER_POLL_SECONDS = 0.02
_STALE_LOCK_SECONDS = 30.0
_STALE_RECLAIMER_SECONDS = 30.0


@dataclass(frozen=True, slots=True)
class StaticResource:
    """A validated packaged asset and its explicit delivery policy."""

    name: str
    media_type: str
    cache_control: str
    body: bytes
    sha256: str | None = None
    size: int | None = None


def read_asset(name: str) -> StaticResource:
    """Read one allowlisted asset without accepting a filesystem path."""
    with _resource_read_context() as root:
        manifest = _load_manifest(root)
        record = manifest.get(name)
        if record is None:
            raise FileNotFoundError(name)
        resource = root.joinpath(name)
        if (
            "/" in name
            or name in (".", "..")
            or _is_symlink(resource)
            or not resource.is_file()
        ):
            raise FileNotFoundError(name)
        body = resource.read_bytes()
        if len(body) > MAX_ASSET_BYTES:
            raise OSError("packaged asset is too large")
        expected_size = record.get("size")
        expected_hash = record.get("sha256")
        if expected_size is not None and len(body) != expected_size:
            raise OSError("packaged asset size does not match manifest")
        if expected_hash is not None and hashlib.sha256(body).hexdigest() != expected_hash:
            raise OSError("packaged asset hash does not match manifest")
        return StaticResource(
            name=name,
            media_type=record["media_type"],
            cache_control=record["cache_control"],
            body=body,
            sha256=expected_hash,
            size=expected_size,
        )


def asset_names() -> tuple[str, ...]:
    """Return the sorted explicit asset names for diagnostics and tests."""
    with _resource_read_context() as root:
        if _local_path(root) is not None and not _is_complete_generation(root):
            raise OSError("packaged static generation is incomplete")
        return tuple(sorted(_load_manifest(root)))


def _load_manifest(root: object | None = None) -> dict[str, dict[str, object]]:
    root = _resource_root() if root is None else root
    resource = root.joinpath(MANIFEST_NAME)
    try:
        if _is_symlink(resource):
            raise OSError("manifest is a symlink")
        value = json.loads(
            resource.read_text(encoding="utf-8"),
            object_pairs_hook=_manifest_pairs,
        )
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise OSError("packaged static manifest is unavailable") from error
    if not isinstance(value, Mapping):
        raise OSError("packaged static manifest is invalid")
    manifest: dict[str, dict[str, object]] = {}
    for name, record in value.items():
        if (
            not isinstance(name, str)
            or not name
            or "/" in name
            or "\\" in name
            or name in (".", "..")
            or not name.isascii()
            or not isinstance(record, Mapping)
            or set(record) - {"media_type", "cache_control", "sha256", "size"}
            or not {"media_type", "cache_control"} <= set(record)
            or not isinstance(record.get("media_type"), str)
            or not isinstance(record.get("cache_control"), str)
            or not _safe_header_value(record["media_type"])
            or not _safe_header_value(record["cache_control"])
            or (
                name == MANIFEST_NAME
                and set(record) != {"media_type", "cache_control"}
            )
            or (
                name != MANIFEST_NAME
                and set(record) != {"media_type", "cache_control", "sha256", "size"}
            )
            or (
                "sha256" in record
                and (
                    not isinstance(record["sha256"], str)
                    or len(record["sha256"]) != 64
                    or any(
                        character not in "0123456789abcdef"
                        for character in record["sha256"]
                    )
                )
            )
            or (
                "size" in record
                and (
                    isinstance(record["size"], bool)
                    or not isinstance(record["size"], int)
                    or record["size"] < 0
                )
            )
        ):
            raise OSError("packaged static manifest is invalid")
        suffix = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
        expected_media_type = MEDIA_TYPES.get(suffix)
        expected_cache = (
            "public, max-age=31536000, immutable"
            if HASHED_ASSET.fullmatch(name)
            else "no-store"
        )
        if (
            name != MANIFEST_NAME
            and (
                expected_media_type is None
                or record["media_type"] != expected_media_type
                or record["cache_control"] != expected_cache
            )
        ):
            raise OSError("packaged static manifest is invalid")
        if (
            name == MANIFEST_NAME
            and (
                record["media_type"] != MEDIA_TYPES[".json"]
                or record["cache_control"] != "no-store"
            )
        ):
            raise OSError("packaged static manifest is invalid")
        asset = root.joinpath(name)
        if _is_symlink(asset) or not asset.is_file():
            raise OSError("packaged static manifest is invalid")
        manifest[name] = dict(record)
    if MANIFEST_NAME not in manifest:
        raise OSError("packaged static manifest is invalid")
    return manifest


def _manifest_pairs(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate manifest key")
        result[key] = value
    return result


def _safe_header_value(value: object) -> bool:
    return isinstance(value, str) and value.isascii() and not any(
        ord(character) < 32 or ord(character) == 127 for character in value
    )


def _is_symlink(resource: object) -> bool:
    checker = getattr(resource, "is_symlink", None)
    return bool(checker()) if callable(checker) else False


@contextmanager
def _resource_read_context():
    root = _resource_root()
    with _publication_reader_lock(root):
        root = _resource_root()
        selected = _publication_read_root(root)
        if selected is None:
            raise OSError("packaged static generation is unavailable")
        root = selected
        yield root


def _resource_root() -> object:
    """Resolve filesystem assets without importing a swapped-out subpackage."""
    parent_name, separator, child_name = STATIC_PACKAGE.rpartition(".")
    if separator:
        parent = sys.modules.get(parent_name)
        parent_paths = getattr(parent, "__path__", None)
        if parent_paths is not None:
            for parent_path in parent_paths:
                path = _local_path(parent_path)
                if path is not None and path.is_dir():
                    return path / child_name
    return resources.files(STATIC_PACKAGE)


@contextmanager
def _publication_reader_lock(root: object):
    path = _local_path(root)
    if path is None:
        yield
        return
    lock = path.parent / f".{path.name}{_PUBLICATION_LOCK_SUFFIX}"
    reclaimer = Path(f"{lock}{_PUBLICATION_RECLAIMER_SUFFIX}")
    token = f"{os.getpid()}-{time.time_ns()}"
    owner = {
        "version": 1,
        "kind": "reader",
        "pid": os.getpid(),
        "created_at": time.time(),
        "token": token,
    }
    deadline = time.monotonic() + _READER_WAIT_SECONDS
    acquired = False
    while not acquired:
        _recover_stale_reclaimer(reclaimer)
        if _lstat_state(reclaimer)["exists"]:
            if time.monotonic() >= deadline:
                raise OSError("asset publication lock did not become available")
            time.sleep(_READER_POLL_SECONDS)
            continue
        try:
            acquired = _try_create_lock(lock, owner)
        except FileExistsError:
            snapshot = _lock_snapshot(lock)
            if _stale_lock(lock, snapshot["owner"]):
                elected = _elect_reclaimer(reclaimer)
                if elected is not None:
                    acquired = _reclaim_and_acquire(
                        lock,
                        reclaimer,
                        elected,
                        owner,
                    )
                    if acquired:
                        break
            if time.monotonic() >= deadline:
                raise OSError("asset publication lock did not become available")
            time.sleep(_READER_POLL_SECONDS)
        except PermissionError:
            if not lock.exists():
                # Installed wheels may be read-only and never publish assets.
                yield
                return
            raise
    try:
        yield
    finally:
        _remove_owned_path(lock, token)


def _publication_fallback(root: object) -> object | None:
    path = _local_path(root)
    if path is None:
        return None
    fallback = path.parent / f".{path.name}.previous"
    if _is_complete_generation(fallback):
        return fallback
    return None


def _publication_read_root(root: object) -> object | None:
    path = _local_path(root)
    if path is None:
        return root
    marker = path.parent / f".{path.name}.publish.json"
    marker_state = _lstat_state(marker)
    if marker_state["exists"] and marker_state["safe"] and marker_state["is_file"]:
        previous = _publication_fallback(path)
        if previous is not None:
            return previous
        previous_state = _lstat_state(path.parent / f".{path.name}.previous")
        if previous_state["exists"]:
            return None
    if _is_complete_generation(path):
        return path
    state = _lstat_state(path)
    if state["safe"] and state["is_dir"]:
        return path
    return _publication_fallback(path)


def _is_complete_generation(root: object) -> bool:
    path = _local_path(root)
    if path is None:
        return True
    state = _lstat_state(path)
    if not state["safe"] or not state["is_dir"]:
        return False
    try:
        manifest = _load_manifest(path)
        names = set(manifest)
        if not _complete_asset_name_contract(names):
            return False
        actual = _generation_files(path)
        if actual is None or actual not in (names, names | {"__init__.py"}):
            return False
        for name, record in manifest.items():
            if name == MANIFEST_NAME:
                continue
            asset = path / name
            expected_size = record["size"]
            if asset.stat().st_size > MAX_ASSET_BYTES:
                return False
            if asset.stat().st_size != expected_size:
                return False
            body = asset.read_bytes()
            if (
                len(body) != expected_size
                or record["sha256"] != hashlib.sha256(body).hexdigest()
            ):
                return False
        return True
    except (OSError, UnicodeDecodeError, ValueError):
        return False


def _complete_asset_name_contract(names: set[str]) -> bool:
    if not all(
        isinstance(name, str)
        and name.isascii()
        and SAFE_ASSET_NAME.fullmatch(name)
        and name not in (".", "..")
        for name in names
    ):
        return False
    if not REQUIRED_STABLE_ASSETS <= names:
        return False
    if any(
        sum(bool(pattern.fullmatch(name)) for name in names) != 1
        for pattern in HASHED_ASSET_PATTERNS
    ):
        return False
    expected = REQUIRED_STABLE_ASSETS | {
        name
        for name in names
        if any(pattern.fullmatch(name) for pattern in HASHED_ASSET_PATTERNS)
    }
    return names == expected


def _generation_files(root: Path) -> set[str] | None:
    actual: set[str] = set()
    try:
        with os.scandir(root) as entries:
            for entry in entries:
                if not SAFE_ASSET_NAME.fullmatch(entry.name):
                    return None
                if entry.is_symlink():
                    return None
                if entry.is_dir(follow_symlinks=False):
                    if entry.name != "__pycache__" or not _valid_pycache(entry.path):
                        return None
                elif entry.is_file(follow_symlinks=False):
                    actual.add(entry.name)
                else:
                    return None
    except OSError:
        return None
    return actual


def _valid_pycache(path: str) -> bool:
    try:
        with os.scandir(path) as entries:
            for entry in entries:
                if (
                    not SAFE_ASSET_NAME.fullmatch(entry.name)
                    or entry.is_symlink()
                    or not entry.name.endswith(".pyc")
                    or not entry.is_file(follow_symlinks=False)
                ):
                    return False
    except OSError:
        return False
    return True


def _lstat_state(path: "Path") -> dict[str, bool]:
    try:
        state = path.lstat()
    except FileNotFoundError:
        return {"exists": False, "safe": True, "is_dir": False, "is_file": False}
    return {
        "exists": True,
        "safe": not stat.S_ISLNK(state.st_mode),
        "is_dir": stat.S_ISDIR(state.st_mode),
        "is_file": stat.S_ISREG(state.st_mode),
    }


def _local_path(resource: object) -> "Path | None":
    if isinstance(resource, Path):
        return resource
    try:
        candidate = os.fspath(resource)
    except TypeError:
        return None
    return Path(candidate) if isinstance(candidate, (str, bytes)) else None


def _read_lock_owner(path: "Path") -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _try_create_lock(path: "Path", owner: Mapping[str, object]) -> bool:
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        _write_all(descriptor, (json.dumps(owner) + "\n").encode("utf-8"))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return True


def _write_all(descriptor: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            raise OSError("publication lock metadata write made no progress")
        view = view[written:]


def _elect_reclaimer(path: "Path") -> dict[str, object] | None:
    owner = {
        "version": 1,
        "kind": "reclaimer",
        "pid": os.getpid(),
        "created_at": time.time(),
        "token": f"{os.getpid()}-{time.time_ns()}",
    }
    try:
        _try_create_lock(path, owner)
    except FileExistsError:
        return None
    return owner


def _reclaim_and_acquire(
    lock: "Path",
    reclaimer: "Path",
    elected: Mapping[str, object],
    owner: Mapping[str, object],
) -> bool:
    try:
        if _read_lock_owner(reclaimer).get("token") != elected.get("token"):
            return False
        observed = _lock_snapshot(lock)
        if observed["exists"] and not _stale_lock(lock, observed["owner"]):
            return False
        current = _lock_snapshot(lock)
        if observed["identity"] != current["identity"]:
            return False
        observed_token = observed["owner"].get("token")
        if observed_token and current["owner"].get("token") != observed_token:
            return False
        if current["exists"]:
            lock.unlink()
        try:
            _try_create_lock(lock, owner)
        except FileExistsError:
            return False
        return True
    finally:
        _remove_owned_path(reclaimer, str(elected["token"]))


def _recover_stale_reclaimer(path: "Path") -> None:
    current = _lock_snapshot(path)
    if not current["exists"] or not _stale_reclaimer(path, current["owner"]):
        return
    token = current["owner"].get("token")
    if isinstance(token, str):
        _remove_owned_path(path, token)
    else:
        replacement = _lock_snapshot(path)
        if current["identity"] == replacement["identity"]:
            try:
                path.unlink()
            except FileNotFoundError:
                pass


def _stale_reclaimer(path: "Path", owner: Mapping[str, object]) -> bool:
    pid = owner.get("pid")
    if isinstance(pid, int) and not isinstance(pid, bool) and pid > 0:
        return not _process_is_alive(pid)
    try:
        return time.time() - path.stat().st_mtime >= _STALE_RECLAIMER_SECONDS
    except OSError:
        return False


def _remove_owned_path(path: "Path", token: str) -> None:
    current = _lock_snapshot(path)
    if current["owner"].get("token") != token:
        return
    replacement = _lock_snapshot(path)
    if current["identity"] != replacement["identity"]:
        return
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _lock_snapshot(path: "Path") -> dict[str, object]:
    try:
        state = path.lstat()
    except FileNotFoundError:
        return {"exists": False, "owner": {}, "identity": None}
    return {
        "exists": True,
        "owner": _read_lock_owner(path),
        "identity": (
            state.st_dev,
            state.st_ino,
            state.st_mtime_ns,
            state.st_size,
        ),
    }


def _process_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _stale_lock(path: "Path", owner: Mapping[str, object]) -> bool:
    pid = owner.get("pid")
    if isinstance(pid, int) and not isinstance(pid, bool) and pid > 0:
        return not _process_is_alive(pid)
    try:
        return time.time() - path.stat().st_mtime >= _STALE_LOCK_SECONDS
    except OSError:
        return False


__all__ = [
    "MAX_ASSET_BYTES",
    "MANIFEST_NAME",
    "STATIC_PACKAGE",
    "StaticResource",
    "asset_names",
    "read_asset",
]
