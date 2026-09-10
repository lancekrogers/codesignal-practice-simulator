"""Transactional creation, deterministic selection, and recovery of attempts."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from .assessments import (
    AssessmentDefinition,
    AssessmentRegistry,
    DEFAULT_ASSESSMENT_REGISTRY,
)
from .candidate_documents import write_initial_source_baseline
from .errors import (
    InvalidInputError,
    SessionCorruptError,
    SessionUnavailableError,
)
from .filesystem import Filesystem, LocalFilesystem
from .models import ACTIVE_POINTER_SCHEMA_VERSION, ActivePointer, SessionState
from .persistence import ACTIVE_FILENAME, Persistence, initial_event
from .scoring import install_attempt_runner
from .workspace_cache import CACHE_INPUTS, ValidatedFixtureCache


ATTEMPTS_DIRECTORY = "attempts"
CREATION_MARKER = ".creation-owner.json"
_MARKER_SCHEMA_VERSION = "attempt-creation/v1"

_COACHING = """# Coaching

Candidate-owned, non-executable notes for candidate-approved goals, questions,
and high-level hints. Do not put source, history, test output, answers, or
hidden-test claims here, and never import or execute these notes in
`simulation.py`. During timed work, do not copy reference, study, vendor, or
fixture cache material here. After submission or an explicit end, post-attempt
learning remains opt-in.
"""
_AGENTS = """# Live attempt instructions

Read derived `STATUS.md` first, or run
`codesignal-sim context --workspace-root PATH`.
Browser UI and CLI are two views of the same attempt; server timer, scoring,
and lifecycle state are authoritative.

- Use candidate-owned `COACHING.md` for candidate-approved notes by default.
- Ask explicit permission before reading candidate source or source history;
  ask separately before editing source.
- During timed work, never read or use reference, solution, stages, walkthrough,
  study, vendor, fixture cache, copied tests, or hidden-test material.
- Never import or execute coaching in `simulation.py`, make hidden-test claims,
  or manually edit `session.json`, `events.jsonl`, `STATUS.md`, locks, or
  `active.json`.
- After submission or an explicit end, post-attempt learning is opt-in.

This is operational policy, not a security sandbox: a same-user process can
bypass it.
"""


class PublishInterrupted(RuntimeError):
    """Test-only crash boundary: publish completed but pointer publication did not."""


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
        if persistence is not None:
            if filesystem is None:
                filesystem = persistence.filesystem
            elif persistence.filesystem is not filesystem:
                raise InvalidInputError(
                    "filesystem and persistence must use the same filesystem"
                )
        if filesystem is None:
            filesystem = LocalFilesystem()
        if persistence is None:
            persistence = Persistence(filesystem)
        self.filesystem = filesystem
        self.persistence = persistence
        self.registry = registry

    @classmethod
    def for_project(
        cls, project_root: Path, *, filesystem: Filesystem | None = None
    ) -> WorkspaceManager:
        """Create a manager for a project's manifest, cache, and ``attempts`` root."""
        if filesystem is None:
            filesystem = LocalFilesystem()
        return cls(
            project_root,
            ValidatedFixtureCache.from_manifest(project_root / "docs/migration-manifest.json"),
            filesystem=filesystem,
        )

    @property
    def attempts_directory(self) -> Path:
        """Return the only safe root for workspace-owned mutations."""
        return self._validated_attempts_directory()

    def create_attempt(
        self,
        state: SessionState,
        *,
        interrupt_after_publish: bool = False,
        before_publish: Callable[[Path, ActivePointer | None], None] | None = None,
    ) -> Path:
        """Build an attempt, optionally checking selection before publication."""
        self._validate_creation_state(state)
        self.cache.validate(self.filesystem)
        attempts = self.attempts_directory
        self.filesystem.mkdir(attempts, parents=True, exist_ok=True)
        with self.persistence.workspace_lock(attempts):
            return self._create_attempt_locked(
                attempts,
                state,
                interrupt_after_publish=interrupt_after_publish,
                before_publish=before_publish,
            )

    def _validate_creation_state(self, state: SessionState) -> None:
        definition = self.registry.require(state.assessment.assessment_id)
        if state.assessment != definition.metadata:
            raise InvalidInputError(
                "assessment metadata does not match its registry entry"
            )
        if not definition.supports_profile(state.profile.profile_id):
            raise InvalidInputError("assessment does not support the selected profile")

    def _create_attempt_locked(
        self,
        attempts: Path,
        state: SessionState,
        *,
        interrupt_after_publish: bool,
        before_publish: Callable[[Path, ActivePointer | None], None] | None,
    ) -> Path:
        self._reconcile_locked(attempts)
        prior_pointer = self.persistence.read_active_pointer(attempts)
        destination = attempts / state.attempt_id
        if destination.exists() or destination.is_symlink():
            raise InvalidInputError(f"attempt already exists: {state.attempt_id}")
        if before_publish is not None:
            before_publish(attempts, prior_pointer)
        token = str(uuid4())
        staging = attempts / f".{state.attempt_id}.staging-{token}"
        published = False
        pointer_publish_started = False
        try:
            self.filesystem.mkdir(staging)
            self._populate_staging(staging, state, token)
            # A filesystem operation can report failure after publishing.
            # Mark this transaction-owned destination first so rollback
            # handles either outcome safely.
            published = True
            self.filesystem.replace(staging, destination)
            if interrupt_after_publish:
                raise PublishInterrupted("attempt published before active pointer update")
            pointer_publish_started = True
            self.persistence.write_active_pointer_locked(
                attempts,
                ActivePointer(ACTIVE_POINTER_SCHEMA_VERSION, state.attempt_id),
            )
            self._remove_marker_best_effort(destination)
            return destination
        except PublishInterrupted:
            raise
        except Exception:
            self._rollback_failed_create(
                attempts,
                prior_pointer,
                staging,
                destination,
                published,
                pointer_publish_started,
            )
            raise

    def _rollback_failed_create(
        self,
        attempts: Path,
        prior_pointer: ActivePointer | None,
        staging: Path,
        destination: Path,
        published: bool,
        pointer_publish_started: bool,
    ) -> None:
        restored_prior_pointer = True
        if pointer_publish_started:
            restored_prior_pointer = self._restore_active_pointer_best_effort(
                attempts, prior_pointer
            )
        rollback_published = (
            destination
            if published and (not pointer_publish_started or restored_prior_pointer)
            else None
        )
        self._rollback_new_attempt(staging, rollback_published)

    def reconcile(self) -> list[str]:
        """Recover only marker-owned attempts unpublished by an interrupted create."""
        attempts = self.attempts_directory
        if not attempts.exists():
            return []
        with self.persistence.workspace_lock(attempts):
            return self._reconcile_locked(attempts)

    def resolve_attempt(self, explicit_attempt_id: str | None = None) -> Path:
        """Take a stable selection snapshot without holding it during later work.

        Commands that score an attempt must not hold the workspace-wide lock for
        the duration of subprocess execution. They acquire this short selection
        snapshot first, then use the selected attempt's lock for lifecycle work.
        """
        attempts = self.attempts_directory
        if not attempts.exists():
            self._select_attempt_path(attempts, explicit_attempt_id)
        with self.persistence.workspace_lock(attempts):
            attempt = self._select_attempt_path(attempts, explicit_attempt_id)
            self._definition_for_persisted_session(self.persistence.read_session(attempt))
        return attempt

    @contextmanager
    def selected_attempt(self, explicit_attempt_id: str | None = None) -> Iterator[Path]:
        """Lock workspace selection and the selected attempt as one operation.

        The project lock order is workspace then attempt.  Holding both locks
        prevents an active-pointer update from changing an implicit selection
        before a caller has read that selected attempt's session or prompt.
        """
        attempts = self.attempts_directory
        if not attempts.exists():
            # Read-only commands must not create a lock file merely to report
            # that no selection can exist yet.
            self._select_attempt_path(attempts, explicit_attempt_id)
        with self.persistence.workspace_lock(attempts):
            attempt = self._select_attempt_path(attempts, explicit_attempt_id)
            with self.persistence.attempt_lock(attempt):
                # A write-ahead submission belongs to this attempt and must finish
                # before any selected-attempt reader can treat the old state as live.
                self.persistence.recover_submission_locked(attempt)
                yield attempt

    def _select_attempt_path(
        self, attempts: Path, explicit_attempt_id: str | None
    ) -> Path:
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
        return attempt

    def definition_for_persisted_session(
        self, state: SessionState
    ) -> AssessmentDefinition:
        """Validate persisted registry references before a caller uses them.

        Registry lookup failures caused by saved session data are corruption,
        not invalid command input.  Keeping this conversion at the workspace
        boundary makes every lifecycle command report the same safe exit.
        """
        if not isinstance(state, SessionState):
            raise SessionCorruptError("selected attempt has an invalid session")
        return self._definition_for_persisted_session(state)

    def _validated_attempts_directory(self) -> Path:
        """Return the real attempts root only when it cannot reach the cache.

        ``Path.resolve()`` deliberately follows existing symlink ancestors and
        a final ``attempts`` symlink.  The comparison is symmetric because a
        writable attempts root is unsafe both inside the cache and around it.
        """
        attempts = self.workspace_root / ATTEMPTS_DIRECTORY
        try:
            resolved_attempts = attempts.resolve()
            resolved_cache = self.cache.root.resolve()
        except OSError as error:
            raise InvalidInputError("attempts directory must be a valid path") from error
        if _paths_overlap(resolved_attempts, resolved_cache):
            raise InvalidInputError(
                "attempts directory must not overlap the fixture cache"
            )
        if attempts.is_symlink() or (attempts.exists() and not attempts.is_dir()):
            raise InvalidInputError("attempts directory must be a non-symlink directory")
        return attempts

    def _definition_for_persisted_session(
        self, state: SessionState
    ) -> AssessmentDefinition:
        try:
            definition = self.registry.require(state.assessment.assessment_id)
        except InvalidInputError as error:
            raise SessionCorruptError(
                "selected attempt assessment is not registered"
            ) from error
        if state.assessment != definition.metadata:
            raise SessionCorruptError(
                "selected attempt assessment does not match the registry"
            )
        if not definition.supports_profile(state.profile.profile_id):
            raise SessionCorruptError(
                "selected attempt profile is not supported by its assessment"
            )
        return definition

    def _populate_staging(self, staging: Path, state: SessionState, token: str) -> None:
        definition = self.registry.require(state.assessment.assessment_id)
        source_directory = self.cache.root.joinpath(
            *definition.cache_directory.split("/")
        )
        with self.persistence.attempt_lock(staging):
            for filename in definition.copied_filenames:
                self.filesystem.copyfile(source_directory / filename, staging / filename)
            write_initial_source_baseline(
                self.filesystem,
                self.persistence,
                staging,
                filename=definition.candidate_filename,
            )
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

    def _restore_active_pointer_best_effort(
        self, attempts: Path, prior_pointer: ActivePointer | None
    ) -> bool:
        """Restore and verify the prior selection after pointer publication fails."""
        try:
            if prior_pointer is None:
                active_pointer = attempts / ACTIVE_FILENAME
                if active_pointer.exists() or active_pointer.is_symlink():
                    self.filesystem.unlink(active_pointer)
                    self.filesystem.flush_directory(attempts)
            else:
                self.persistence.write_active_pointer_locked(attempts, prior_pointer)
        except OSError:
            return False
        try:
            return self.persistence.read_active_pointer(attempts) == prior_pointer
        except SessionCorruptError:
            return False

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


def _paths_overlap(left: Path, right: Path) -> bool:
    """Return whether either resolved path contains the other."""
    return left == right or left in right.parents or right in left.parents


__all__ = [
    "ATTEMPTS_DIRECTORY",
    "CACHE_INPUTS",
    "CREATION_MARKER",
    "PublishInterrupted",
    "ValidatedFixtureCache",
    "WorkspaceManager",
]
