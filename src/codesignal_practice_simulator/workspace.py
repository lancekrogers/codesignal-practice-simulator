"""Transactional creation, deterministic selection, and recovery of attempts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from .assessments import (
    AssessmentRegistry,
    DEFAULT_ASSESSMENT_REGISTRY,
    FILE_STORAGE,
)
from .errors import (
    FixtureSetupRequiredError,
    InvalidInputError,
    SessionCorruptError,
    SessionUnavailableError,
)
from .filesystem import Filesystem, LocalFilesystem
from .models import ACTIVE_POINTER_SCHEMA_VERSION, ActivePointer, SessionState
from .rendering import refresh_status
from .persistence import ACTIVE_FILENAME, Persistence, initial_event
from .scoring import install_attempt_runner


ATTEMPTS_DIRECTORY = "attempts"
CREATION_MARKER = ".creation-owner.json"
CACHE_INPUTS = FILE_STORAGE.copied_filenames
_CACHE_README = "vendor-readme.md"
_MARKER_SCHEMA_VERSION = "attempt-creation/v1"
_EXPECTED_CACHE_PATHS = frozenset(
    (_CACHE_README, *(f"assessment/file_storage/{name}" for name in CACHE_INPUTS))
)

_COACHING = """# Coaching

Candidate-owned, non-executable collaboration notes.

Use this file for candidate-approved goals, questions, and high-level hints.
Do not put candidate code, test output, or answers here.
"""
_AGENTS = """# Live attempt instructions

Read `codesignal-sim context` or `STATUS.md` before acting.

- Edit `COACHING.md` by default. It is candidate-owned, non-executable text.
- Read or edit candidate code only after an explicit candidate request.
- Never manually edit structured or generated state: `session.json`,
  `events.jsonl`, locks, `active.json`, or `STATUS.md`.
- During timed work, never use assessment reference/solution/stages/walkthrough/
  study answers as hints or expose their contents.

This is operational policy, not a security sandbox: a same-user process can
bypass it.
"""


class PublishInterrupted(RuntimeError):
    """Test-only crash boundary: publish completed but pointer publication did not."""


@dataclass(frozen=True, slots=True)
class ValidatedFixtureCache:
    """The complete seven-file cache contract used before workspace mutation."""

    root: Path
    hashes: dict[str, str]

    @classmethod
    def from_manifest(cls, manifest_path: Path) -> ValidatedFixtureCache:
        """Build a cache contract from the project's fetch-only manifest."""
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            cache_relative = manifest["fixture_cache_root"]
            fetches = manifest["fetches"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
            raise FixtureSetupRequiredError(
                f"fixture setup is required: cannot read manifest {manifest_path}"
            ) from error
        if not isinstance(cache_relative, str) or not isinstance(fetches, list):
            raise FixtureSetupRequiredError("fixture setup is required: invalid manifest")

        hashes: dict[str, str] = {}
        for record in fetches:
            if not isinstance(record, dict):
                raise FixtureSetupRequiredError("fixture setup is required: invalid manifest")
            path = record.get("cache_path")
            digest = record.get("sha256")
            if (
                not isinstance(path, str)
                or not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
                or path in hashes
            ):
                raise FixtureSetupRequiredError("fixture setup is required: invalid manifest")
            hashes[path] = digest

        if set(hashes) != _EXPECTED_CACHE_PATHS:
            raise FixtureSetupRequiredError(
                "fixture setup is required: manifest does not define seven cache records"
            )
        project_root = manifest_path.resolve().parent.parent
        root = (project_root / cache_relative).resolve()
        if root != project_root and project_root not in root.parents:
            raise FixtureSetupRequiredError("fixture setup is required: cache escapes project")
        return cls(root=root, hashes=hashes)

    def validate(self, filesystem: Filesystem) -> None:
        """Verify the complete cache and all hashes before any attempt write."""
        if set(self.hashes) != _EXPECTED_CACHE_PATHS:
            raise FixtureSetupRequiredError(
                "fixture setup is required: cache contract lacks seven records"
            )
        if not self.root.is_dir() or self.root.is_symlink():
            raise FixtureSetupRequiredError(
                f"fixture setup is required: cache is absent at {self.root}"
            )
        actual: set[str] = set()
        try:
            for path in self.root.rglob("*"):
                if path.is_symlink():
                    raise FixtureSetupRequiredError(
                        f"fixture setup is required: cache contains symlink {path}"
                    )
                if path.is_file():
                    actual.add(path.relative_to(self.root).as_posix())
        except OSError as error:
            raise FixtureSetupRequiredError(
                f"fixture setup is required: cannot inspect cache {self.root}"
            ) from error
        if actual != set(self.hashes):
            raise FixtureSetupRequiredError(
                "fixture setup is required: cache does not contain exactly seven files"
            )
        for relative, expected_hash in self.hashes.items():
            path = self.root.joinpath(*relative.split("/"))
            try:
                actual_hash = hashlib.sha256(filesystem.read_bytes(path)).hexdigest()
            except OSError as error:
                raise FixtureSetupRequiredError(
                    f"fixture setup is required: cannot read cache file {relative}"
                ) from error
            if actual_hash != expected_hash:
                raise FixtureSetupRequiredError(
                    f"fixture setup is required: cache hash mismatch for {relative}"
                )


class WorkspaceManager:
    """Create and resolve attempts without ever inferring selection from recency."""

    def __init__(
        self,
        workspace_root: Path,
        cache: ValidatedFixtureCache,
        *,
        filesystem: Filesystem | None = None,
        persistence: Persistence | None = None,
        registry: AssessmentRegistry = DEFAULT_ASSESSMENT_REGISTRY,
    ) -> None:
        self.workspace_root = workspace_root.resolve()
        self.cache = cache
        self.filesystem = filesystem or LocalFilesystem()
        self.persistence = persistence or Persistence(self.filesystem)
        self.registry = registry

    @classmethod
    def for_project(
        cls, project_root: Path, *, filesystem: Filesystem | None = None
    ) -> WorkspaceManager:
        """Create a manager for a project's manifest, cache, and ``attempts`` root."""
        filesystem = filesystem or LocalFilesystem()
        return cls(
            project_root,
            ValidatedFixtureCache.from_manifest(project_root / "docs/migration-manifest.json"),
            filesystem=filesystem,
        )

    @property
    def attempts_directory(self) -> Path:
        return self.workspace_root / ATTEMPTS_DIRECTORY

    def create_attempt(
        self, state: SessionState, *, interrupt_after_publish: bool = False
    ) -> Path:
        """Build an attempt in staging, publish it, then atomically select it."""
        definition = self.registry.require(state.assessment.assessment_id)
        if state.assessment != definition.metadata:
            raise InvalidInputError(
                "assessment metadata does not match its registry entry"
            )
        if not definition.supports_profile(state.profile.profile_id):
            raise InvalidInputError("assessment does not support the selected profile")
        self.cache.validate(self.filesystem)
        attempts = self.attempts_directory
        self.filesystem.mkdir(attempts, parents=True, exist_ok=True)
        with self.persistence.workspace_lock(attempts):
            self._reconcile_locked(attempts)
            destination = attempts / state.attempt_id
            if destination.exists() or destination.is_symlink():
                raise InvalidInputError(f"attempt already exists: {state.attempt_id}")

            token = str(uuid4())
            staging = attempts / f".{state.attempt_id}.staging-{token}"
            published = False
            try:
                self.filesystem.mkdir(staging)
                self._populate_staging(staging, state, token)
                self.filesystem.replace(staging, destination)
                published = True
                if interrupt_after_publish:
                    raise PublishInterrupted("attempt published before active pointer update")
                self.persistence.write_active_pointer_locked(
                    attempts,
                    ActivePointer(ACTIVE_POINTER_SCHEMA_VERSION, state.attempt_id),
                )
                self._remove_marker_best_effort(destination)
                return destination
            except PublishInterrupted:
                raise
            except Exception:
                self._rollback_new_attempt(staging, destination if published else None)
                raise

    def reconcile(self) -> list[str]:
        """Recover only marker-owned attempts unpublished by an interrupted create."""
        attempts = self.attempts_directory
        if not attempts.exists():
            return []
        with self.persistence.workspace_lock(attempts):
            return self._reconcile_locked(attempts)

    def resolve_attempt(self, explicit_attempt_id: str | None = None) -> Path:
        """Resolve explicit selection first, otherwise the validated active pointer."""
        attempts = self.attempts_directory
        if explicit_attempt_id is not None:
            attempt_id = self._require_attempt_id(explicit_attempt_id)
        else:
            pointer = self.persistence.read_active_pointer(attempts)
            if pointer is None:
                raise SessionUnavailableError(
                    "no active attempt; provide --attempt or start a new attempt"
                )
            attempt_id = pointer.attempt_id
        attempt = attempts / attempt_id
        if not attempt.is_dir() or attempt.is_symlink():
            raise SessionUnavailableError(f"selected attempt is unavailable: {attempt_id}")
        self.persistence.read_session(attempt)
        return attempt

    def _populate_staging(self, staging: Path, state: SessionState, token: str) -> None:
        definition = self.registry.require(state.assessment.assessment_id)
        source_directory = self.cache.root.joinpath(
            *definition.cache_directory.split("/")
        )
        with self.persistence.attempt_lock(staging):
            for filename in definition.copied_filenames:
                self.filesystem.copyfile(source_directory / filename, staging / filename)
            install_attempt_runner(
                staging,
                self.filesystem.write_bytes,
                self.filesystem.flush_file,
                self.filesystem.mkdir,
            )

            self._write_flushed(staging / "COACHING.md", _COACHING)
            self._write_flushed(staging / "AGENTS.md", _AGENTS)
            self.persistence.write_session_locked(staging, state)
            event = initial_event(state)
            self._write_flushed(
                staging / "events.jsonl",
                json.dumps(
                    event.to_dict(),
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n",
            )
            refresh_status(
                staging,
                self.persistence,
                filesystem=self.filesystem,
            )
            self._write_flushed(
                staging / CREATION_MARKER,
                json.dumps(
                    {
                        "schema_version": _MARKER_SCHEMA_VERSION,
                        "attempt_id": state.attempt_id,
                        "creation_token": token,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n",
            )

    def _write_flushed(self, path: Path, text: str) -> None:
        self.filesystem.write_bytes(path, text.encode("utf-8"))
        self.filesystem.flush_file(path)

    def _reconcile_locked(self, attempts: Path) -> list[str]:
        pointer = self.persistence.read_active_pointer(attempts)
        selected = None if pointer is None else pointer.attempt_id
        removed: list[str] = []
        try:
            children = tuple(attempts.iterdir())
        except OSError as error:
            raise SessionUnavailableError(f"cannot inspect attempts directory: {attempts}") from error
        for attempt in children:
            if not attempt.is_dir() or attempt.is_symlink() or attempt.name.startswith("."):
                continue
            marker = self._read_valid_marker(attempt)
            if marker is None:
                continue
            if marker.attempt_id != attempt.name:
                continue
            with self.persistence.attempt_lock(attempt):
                if marker.attempt_id == selected:
                    self._remove_marker_best_effort(attempt)
                else:
                    self.filesystem.remove_tree(attempt)
                    removed.append(attempt.name)
        return removed

    def _rollback_new_attempt(self, staging: Path, published: Path | None) -> None:
        for path in (staging, published):
            if path is None:
                continue
            try:
                if path.exists() or path.is_symlink():
                    self.filesystem.remove_tree(path)
            except OSError:
                pass

    def _remove_marker_best_effort(self, attempt: Path) -> None:
        try:
            self.filesystem.unlink(attempt / CREATION_MARKER)
        except OSError:
            pass

    def _read_valid_marker(self, attempt: Path) -> _CreationMarker | None:
        path = attempt / CREATION_MARKER
        if not path.is_file() or path.is_symlink():
            return None
        try:
            data = json.loads(self.filesystem.read_bytes(path).decode("utf-8"))
            if not isinstance(data, dict) or set(data) != {
                "schema_version",
                "attempt_id",
                "creation_token",
            }:
                return None
            if data["schema_version"] != _MARKER_SCHEMA_VERSION:
                return None
            return _CreationMarker(
                attempt_id=self._require_attempt_id(data["attempt_id"]),
                creation_token=self._require_attempt_id(data["creation_token"]),
            )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, InvalidInputError):
            return None

    @staticmethod
    def _require_attempt_id(value: object) -> str:
        if not isinstance(value, str):
            raise InvalidInputError("attempt ID must be a canonical UUID")
        try:
            parsed = UUID(value)
        except ValueError as error:
            raise InvalidInputError("attempt ID must be a canonical UUID") from error
        if str(parsed) != value:
            raise InvalidInputError("attempt ID must be a canonical UUID")
        return value


@dataclass(frozen=True, slots=True)
class _CreationMarker:
    attempt_id: str
    creation_token: str


__all__ = [
    "ATTEMPTS_DIRECTORY",
    "CACHE_INPUTS",
    "CREATION_MARKER",
    "PublishInterrupted",
    "ValidatedFixtureCache",
    "WorkspaceManager",
]
