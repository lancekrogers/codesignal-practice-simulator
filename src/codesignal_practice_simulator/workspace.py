"""Transactional creation, deterministic selection, and recovery of attempts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from .assessments import (
    AssessmentDefinition,
    AssessmentRegistry,
    DEFAULT_ASSESSMENT_REGISTRY,
)
from .candidate_documents import write_initial_source_baseline
from .errors import (
    AssessmentVersionUnavailableError,
    FixtureSetupRequiredError,
    IllegalLifecycleError,
    InvalidInputError,
    LockUnavailableError,
    RestartConflictError,
    RestartRecoveryPendingError,
    SessionCorruptError,
    SessionUnavailableError,
    StaleRevisionError,
)
from .filesystem import Filesystem, LocalFilesystem
from .input_providers import InputProvider, InputProviders
from .models import (
    ACTIVE,
    ACTIVE_POINTER_SCHEMA_VERSION,
    RESTART_REASON,
    SESSION_SCHEMA_VERSION_V2,
    ActivePointer,
    AssessmentMetadata,
    EventRecordUnion,
    PinnedAssessment,
    RestartCompletion,
    RestartJournal,
    RestartRequest,
    SessionRecord,
    SessionState,
    SessionStateV2,
    abandoned_record,
    session_event,
)
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


@dataclass(frozen=True, slots=True)
class RestartResult:
    """The durable outcome of one restart operation.

    ``replayed`` is true when an identical earlier request already completed;
    the states are then ``None`` because nothing was read or written for them.
    """

    operation_id: str
    old_attempt_id: str
    replacement_attempt_id: str
    committed_at: datetime
    replayed: bool
    abandoned_state: SessionStateV2 | None = None
    replacement_state: SessionStateV2 | None = None

    def to_dict(self) -> dict[str, object]:
        """The transport document shared by the CLI envelope and the web API."""
        return {
            "operation_id": self.operation_id,
            "old_attempt_id": self.old_attempt_id,
            "replacement_attempt_id": self.replacement_attempt_id,
            "committed_at": self.committed_at.isoformat(),
            "replayed": self.replayed,
            "session": (
                None if self.replacement_state is None else self.replacement_state.to_dict()
            ),
            "abandoned_session": (
                None if self.abandoned_state is None else self.abandoned_state.to_dict()
            ),
        }


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
        providers: InputProviders | None = None,
    ) -> None:
        self.workspace_root = workspace_root.resolve()
        self.cache = cache
        # Providers own input validation, identity and staging per definition
        # kind (D003). The default set wraps this cache for fetched content and
        # adds installed originals when the package bundles any.
        self.providers = InputProviders.default(cache) if providers is None else providers
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

    def pinned_assessment(self, assessment: AssessmentMetadata) -> PinnedAssessment:
        """Return the content identity a new attempt of ``assessment`` must pin."""
        if not isinstance(assessment, AssessmentMetadata):
            raise InvalidInputError("assessment is invalid")
        definition = self.registry.require(assessment.assessment_id)
        if assessment != definition.metadata:
            raise InvalidInputError(
                "assessment metadata does not match its registry entry"
            )
        return self._provider(definition).pinned_assessment(definition)

    def validate_inputs(self, definition: AssessmentDefinition) -> None:
        """Fail before any mutation when a definition's inputs are missing or tampered.

        Only the selected definition's provider is consulted: an original
        exercise never requires the fetched File Storage cache, and File Storage
        keeps its complete-cache validation unchanged.
        """
        self._provider(definition).validate(definition, self.filesystem)

    def _provider(self, definition: AssessmentDefinition) -> InputProvider:
        return self.providers.for_definition(definition)

    def create_attempt(
        self,
        state: SessionRecord,
        *,
        interrupt_after_publish: bool = False,
        before_publish: Callable[[Path, ActivePointer | None], None] | None = None,
    ) -> Path:
        """Build an attempt, optionally checking selection before publication."""
        definition = self._validate_creation_state(state)
        self.validate_inputs(definition)
        attempts = self.attempts_directory
        self.filesystem.mkdir(attempts, parents=True, exist_ok=True)
        with self.persistence.workspace_lock(attempts):
            return self._create_attempt_locked(
                attempts,
                state,
                interrupt_after_publish=interrupt_after_publish,
                before_publish=before_publish,
            )

    def _validate_creation_state(self, state: SessionRecord) -> AssessmentDefinition:
        """Validate either schema; LifecycleService creates only session/v2.

        session/v1 creation remains for callers that stage legacy fixtures. A v2
        identity must equal the one its provider computes from declared hashes,
        so callers cannot pin content that the staged bytes were not verified
        against.
        """
        if isinstance(state, SessionStateV2):
            if not isinstance(state.assessment, PinnedAssessment):
                # The legacy-identity variant records an abandonment that
                # already happened; it is never the state a new attempt starts in.
                raise InvalidInputError(
                    "a new attempt requires a pinned content identity"
                )
            definition = self.registry.require(state.assessment.assessment_id)
            if state.assessment != self._provider(definition).pinned_assessment(definition):
                raise InvalidInputError(
                    "assessment identity does not match the installed content"
                )
        elif isinstance(state, SessionState):
            definition = self.registry.require(state.assessment.assessment_id)
            if state.assessment != definition.metadata:
                raise InvalidInputError(
                    "assessment metadata does not match its registry entry"
                )
        else:
            raise InvalidInputError("session is invalid")
        if not definition.supports_profile(state.profile.profile_id):
            raise InvalidInputError("assessment does not support the selected profile")
        return definition

    def _create_attempt_locked(
        self,
        attempts: Path,
        state: SessionRecord,
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

    # Restart transaction (D001). Lock order: workspace, then the old attempt,
    # then the transaction-owned replacement staging. The durable journal is the
    # commit point; everything after it rolls forward and never rolls back.

    def restart_attempt(
        self,
        request: RestartRequest,
        *,
        now: datetime,
        reason: str = RESTART_REASON,
    ) -> RestartResult:
        """Abandon one active attempt and create its replacement, exactly once.

        Before the commit intent is durable, any failure leaves the old attempt
        active and selected. After it, the same operation is completed by this
        call or by a later recovery; a duplicate identical request returns the
        original replacement without touching the current selection.
        """
        if not isinstance(request, RestartRequest):
            raise InvalidInputError("restart request is invalid")
        attempts = self.attempts_directory
        if not attempts.exists():
            raise SessionUnavailableError(
                f"selected attempt is unavailable: {request.old_attempt_id}"
            )
        # The replacement's inputs are validated before the old attempt is
        # touched or any commit intent exists (D003: failure before mutation).
        self.validate_inputs(self.registry.require(request.assessment.assessment_id))
        with self.persistence.workspace_lock(attempts):
            self._reconcile_locked(attempts)
            completed = self.persistence.read_restart_completion(
                attempts, request.operation_id
            )
            if completed is not None:
                return self._replay_completed(completed, request)
            old = attempts / request.old_attempt_id
            if not old.is_dir() or old.is_symlink():
                raise SessionUnavailableError(
                    f"selected attempt is unavailable: {request.old_attempt_id}"
                )
            with self.persistence.attempt_lock(old):
                self.persistence.recover_attempt_locked(old)
                old_state = self._validated_restart_source(old, request, now)
                journal = self._plan_restart(attempts, request, old_state, now, reason)
                self._stage_and_commit_locked(attempts, journal)
                return self._roll_forward_locked(attempts, journal, old_locked=True)

    def _validated_restart_source(
        self, old: Path, request: RestartRequest, now: datetime
    ) -> SessionRecord:
        state = self.persistence.read_session(old)
        if state.attempt_id != old.name:
            raise SessionCorruptError(f"attempt identity does not match: {old.name}")
        # A terminal state is the more actionable answer than a revision
        # mismatch: refreshing cannot make a submitted attempt restartable.
        if state.status != ACTIVE:
            raise IllegalLifecycleError(
                f"cannot restart an attempt in {state.status} state"
            )
        if state.revision != request.expected_revision:
            raise StaleRevisionError(
                "attempt changed since it was read; refresh and retry "
                f"(expected revision {request.expected_revision}, "
                f"current {state.revision})"
            )
        if now >= state.deadline_at:
            raise IllegalLifecycleError(
                "cannot restart an attempt at or after its deadline; "
                "submit it or start a new attempt"
            )
        return state

    def _plan_restart(
        self,
        attempts: Path,
        request: RestartRequest,
        old_state: SessionRecord,
        now: datetime,
        reason: str,
    ) -> RestartJournal:
        replacement = SessionStateV2(
            schema_version=SESSION_SCHEMA_VERSION_V2,
            attempt_id=str(uuid4()),
            assessment=request.assessment,
            profile=request.profile,
            started_at=now,
            deadline_at=now + timedelta(seconds=request.profile.duration_seconds),
            status=ACTIVE,
            revision=0,
        )
        # The target must be the installed content and a supported profile
        # before anything is staged; this is the same check every creation runs.
        self._validate_creation_state(replacement)
        abandoned = abandoned_record(old_state, ended_at=now, reason=reason)
        old_event = session_event(
            abandoned,
            event_id=str(uuid4()),
            occurred_at=now,
            name="abandoned",
            outcome="succeeded",
            arguments={
                "operation_id": request.operation_id,
                "replacement_attempt_id": replacement.attempt_id,
            },
        )
        replacement_event = session_event(
            replacement,
            event_id=str(uuid4()),
            occurred_at=now,
            name="started",
            outcome="succeeded",
            arguments={
                "operation_id": request.operation_id,
                "replaces_attempt_id": old_state.attempt_id,
            },
        )
        pointer = self.persistence.read_active_pointer(attempts)
        token = str(uuid4())
        return RestartJournal(
            request=request,
            old_prior_state=old_state,
            old_final_state=abandoned,
            old_event=old_event,  # type: ignore[arg-type]
            replacement_state=replacement,
            replacement_event=replacement_event,  # type: ignore[arg-type]
            staging_name=f".{replacement.attempt_id}.staging-{token}",
            creation_token=token,
            expected_pointer=None if pointer is None else pointer.attempt_id,
            committed_at=now,
        )

    def _stage_and_commit_locked(self, attempts: Path, journal: RestartJournal) -> None:
        """Stage the replacement, then make the commit intent durable."""
        staging = attempts / journal.staging_name
        try:
            self.filesystem.mkdir(staging)
            self._populate_staging(
                staging,
                journal.replacement_state,
                journal.creation_token,
                event=journal.replacement_event,
            )
        except Exception:
            self._rollback_new_attempt(staging, None)
            raise
        try:
            self.persistence.write_restart_journal_locked(attempts, journal)
        except Exception:
            # A replace can succeed and its directory flush still report failure
            # (OSError). Only a journal that is provably absent lets the staging
            # be removed; any other failure before the write leaves no journal
            # and must not orphan the staging directory either.
            if self._journal_is_durable(attempts, journal):
                return
            self._rollback_new_attempt(staging, None)
            raise

    def _journal_is_durable(self, attempts: Path, journal: RestartJournal) -> bool:
        try:
            return (
                self.persistence.read_restart_journal(attempts, journal.operation_id)
                == journal
            )
        except SessionUnavailableError:
            return False

    def _roll_forward_locked(
        self, attempts: Path, journal: RestartJournal, *, old_locked: bool
    ) -> RestartResult:
        """Publish a committed operation; every step tolerates having already run.

        Order: old abandoned state and event, replacement directory, active
        pointer, completion receipt, then journal and marker residue. Storage
        failures leave the journal in place and report recovery as pending.
        Unexpected records fail closed and preserve everything for repair.
        """
        old = attempts / journal.old_prior_state.attempt_id
        destination = attempts / journal.replacement_state.attempt_id
        try:
            with nullcontext() if old_locked else self.persistence.attempt_lock(old):
                # Every record is checked against its allowed prior or target
                # state before the first write, so an unexpected record fails
                # closed with nothing changed and all evidence in place.
                self._verify_restart_targets_locked(attempts, journal, old, destination)
                self.persistence.publish_transition_locked(
                    old,
                    journal.old_prior_state,
                    journal.old_final_state,
                    journal.old_event,
                )
            self._publish_replacement_locked(attempts, journal, destination)
            self._publish_restart_pointer_locked(attempts, journal, destination)
            self.persistence.write_restart_completion_locked(
                attempts, RestartCompletion.from_journal(journal)
            )
            self.persistence.remove_restart_journal_locked(
                attempts, journal.operation_id
            )
        except SessionCorruptError:
            raise
        except (OSError, SessionUnavailableError, LockUnavailableError) as error:
            # A busy old-attempt lock during recovery is not corruption and not
            # a lifecycle rule: the commit is durable and will roll forward.
            raise RestartRecoveryPendingError(
                "restart is committed but not fully published; recovery is "
                f"pending for operation {journal.operation_id}"
            ) from error
        self._remove_marker_best_effort(destination)
        return RestartResult(
            operation_id=journal.operation_id,
            old_attempt_id=journal.old_prior_state.attempt_id,
            replacement_attempt_id=journal.replacement_state.attempt_id,
            committed_at=journal.committed_at,
            replayed=False,
            abandoned_state=journal.old_final_state,
            replacement_state=journal.replacement_state,
        )

    def _verify_restart_targets_locked(
        self, attempts: Path, journal: RestartJournal, old: Path, destination: Path
    ) -> None:
        current = self.persistence.read_session(old)
        if current not in (journal.old_prior_state, journal.old_final_state):
            raise SessionCorruptError(
                f"recorded transition does not match its session: {old.name}"
            )
        self._replacement_is_staged(attempts, journal, destination)
        self._pointer_awaits_replacement(attempts, journal, destination)

    def _replacement_is_staged(
        self, attempts: Path, journal: RestartJournal, destination: Path
    ) -> bool:
        """Return whether the replacement still waits in staging; verify otherwise."""
        staging = attempts / journal.staging_name
        staged = staging.is_dir() and not staging.is_symlink()
        published = destination.is_dir() and not destination.is_symlink()
        if staged and published:
            raise SessionCorruptError(
                f"restart replacement exists twice: {destination.name}"
            )
        if staged:
            return True
        if not published:
            raise SessionCorruptError(
                f"restart replacement is missing: {destination.name}"
            )
        if self.persistence.read_session(destination) != journal.replacement_state:
            raise SessionCorruptError(
                f"restart replacement does not match its journal: {destination.name}"
            )
        return False

    def _pointer_awaits_replacement(
        self, attempts: Path, journal: RestartJournal, destination: Path
    ) -> bool:
        """Return whether the pointer still needs publishing; verify otherwise."""
        pointer = self.persistence.read_active_pointer(attempts)
        current = None if pointer is None else pointer.attempt_id
        if current == destination.name:
            return False
        if current != journal.expected_pointer:
            # Selection mutations reconcile journals first, so a third selection
            # here means something else wrote the pointer: do not overwrite it.
            raise SessionCorruptError(
                "active pointer changed during restart: "
                f"{journal.operation_id}"
            )
        return True

    def _publish_replacement_locked(
        self, attempts: Path, journal: RestartJournal, destination: Path
    ) -> None:
        if self._replacement_is_staged(attempts, journal, destination):
            self.filesystem.replace(attempts / journal.staging_name, destination)

    def _publish_restart_pointer_locked(
        self, attempts: Path, journal: RestartJournal, destination: Path
    ) -> None:
        if self._pointer_awaits_replacement(attempts, journal, destination):
            self.persistence.write_active_pointer_locked(
                attempts, ActivePointer(ACTIVE_POINTER_SCHEMA_VERSION, destination.name)
            )

    def _replay_completed(
        self, completed: RestartCompletion, request: RestartRequest
    ) -> RestartResult:
        self._require_same_request(completed.request, request)
        return RestartResult(
            operation_id=completed.operation_id,
            old_attempt_id=completed.request.old_attempt_id,
            replacement_attempt_id=completed.replacement_attempt_id,
            committed_at=completed.committed_at,
            replayed=True,
        )

    @staticmethod
    def _require_same_request(recorded: RestartRequest, request: RestartRequest) -> None:
        if recorded != request or recorded.fingerprint != request.fingerprint:
            raise RestartConflictError(
                "operation ID was already used with different arguments: "
                f"{request.operation_id}"
            )

    def _recover_restarts_locked(self, attempts: Path) -> list[str]:
        """Finish every pending journal before any selection mutation proceeds."""
        recovered: list[str] = []
        for journal in self.persistence.read_restart_journals(attempts):
            completed = self.persistence.read_restart_completion(
                attempts, journal.operation_id
            )
            if completed is None:
                self._roll_forward_locked(attempts, journal, old_locked=False)
            else:
                # The receipt was durable before the journal could be pruned.
                if completed != RestartCompletion.from_journal(journal):
                    raise SessionCorruptError(
                        "restart completion does not match its journal: "
                        f"{journal.operation_id}"
                    )
                self.persistence.remove_restart_journal_locked(
                    attempts, journal.operation_id
                )
                self._remove_marker_best_effort(
                    attempts / journal.replacement_state.attempt_id
                )
            recovered.append(journal.operation_id)
        return recovered

    def reconcile(self) -> list[str]:
        """Roll forward pending restarts, then remove interrupted creations.

        Returns the marker-owned attempt IDs that were removed. Pending restart
        journals are recovered first so a committed replacement that has not
        reached the active pointer yet is never mistaken for an abandoned create.
        """
        attempts = self.attempts_directory
        if not attempts.exists():
            return []
        with self.persistence.workspace_lock(attempts):
            return self._reconcile_locked(attempts)

    def recover_restarts(self) -> list[str]:
        """Explicit recovery entrypoint: finish every committed restart.

        Returns the operation IDs that were rolled forward or pruned. Metadata
        and history reads never call this; lifecycle mutations and server
        startup do.
        """
        attempts = self.attempts_directory
        if not attempts.exists():
            return []
        with self.persistence.workspace_lock(attempts):
            return self._recover_restarts_locked(attempts)

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
            # A committed restart decides what is selected and which attempt is
            # still live; it must finish before any command acts on either.
            self._recover_restarts_locked(attempts)
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
            self._recover_restarts_locked(attempts)
            attempt = self._select_attempt_path(attempts, explicit_attempt_id)
            with self.persistence.attempt_lock(attempt):
                # A write-ahead submission or abandonment belongs to this attempt
                # and must finish before any reader can treat the old state as live.
                self.persistence.recover_attempt_locked(attempt)
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
        self, state: SessionRecord
    ) -> AssessmentDefinition:
        """Validate persisted registry references before a caller uses them.

        Registry lookup failures caused by saved session data are corruption,
        not invalid command input.  Keeping this conversion at the workspace
        boundary makes every lifecycle command report the same safe exit.
        Read-only review and history must not depend on this lookup.
        """
        if not isinstance(state, (SessionState, SessionStateV2)):
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
        self, state: SessionRecord
    ) -> AssessmentDefinition:
        if isinstance(state, SessionStateV2) and isinstance(
            state.assessment, PinnedAssessment
        ):
            return self._definition_for_pinned_session(state)
        # Legacy identity adapter: session/v1 recorded only metadata, and so does
        # the abandoned v2 record an explicit upgrade left behind. Both are
        # matched against today's definition and never given a content version.
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

    def _definition_for_pinned_session(
        self, state: SessionStateV2
    ) -> AssessmentDefinition:
        """Require the installed definition to be the exact content the attempt pinned."""
        unavailable = (
            "attempt content version is not installed; "
            "stored results remain reviewable"
        )
        try:
            definition = self.registry.require(state.assessment.assessment_id)
            installed = self._provider(definition).pinned_assessment(definition)
        except (InvalidInputError, FixtureSetupRequiredError) as error:
            raise AssessmentVersionUnavailableError(unavailable) from error
        if (
            state.assessment.content_version != installed.content_version
            or state.assessment.content_digest != installed.content_digest
            or state.assessment.level_count != installed.level_count
            or not definition.supports_profile(state.profile.profile_id)
        ):
            raise AssessmentVersionUnavailableError(unavailable)
        return definition

    def _populate_staging(
        self,
        staging: Path,
        state: SessionRecord,
        token: str,
        *,
        event: EventRecordUnion | None = None,
    ) -> None:
        definition = self.registry.require(state.assessment.assessment_id)
        provider = self._provider(definition)
        with self.persistence.attempt_lock(staging):
            for filename in definition.copied_filenames:
                provider.stage_file(definition, filename, staging / filename, self.filesystem)
            self._verify_staged_inputs(staging, definition)
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
            if event is None:
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

    def _verify_staged_inputs(
        self, staging: Path, definition: AssessmentDefinition
    ) -> None:
        """Prove staged copies are the declared bytes an identity describes.

        The provider's source was validated before staging, but it can change
        before the copy. Checking the transaction-owned copies closes that gap
        for this attempt; a mismatch aborts creation through the normal rollback.
        """
        provider = self._provider(definition)
        for filename in definition.copied_filenames:
            expected = provider.declared_hash(definition, filename)
            try:
                actual = hashlib.sha256(
                    self.filesystem.read_bytes(staging / filename)
                ).hexdigest()
            except OSError as error:
                raise FixtureSetupRequiredError(
                    f"fixture setup is required: cannot verify staged {filename}"
                ) from error
            if actual != expected:
                raise FixtureSetupRequiredError(
                    "fixture setup is required: staged input does not match "
                    f"its declared hash: {filename}"
                )

    def _write_flushed(self, path: Path, text: str) -> None:
        self.filesystem.write_bytes(path, text.encode("utf-8"))
        self.filesystem.flush_file(path)

    def _reconcile_locked(self, attempts: Path) -> list[str]:
        # Journals first: a committed replacement may already be published but
        # not yet selected, and the marker scan below would otherwise remove it.
        self._recover_restarts_locked(attempts)
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
    "RestartResult",
    "ValidatedFixtureCache",
    "WorkspaceManager",
]
