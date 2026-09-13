"""Shared dependency-injected application graph for simulator transports."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
import threading
from typing import Literal

from .assessments import (
    AssessmentDefinition,
    DEFAULT_ASSESSMENT_REGISTRY,
)
from .attempt_history import AttemptHistoryService, HistoryFilters, HistoryPage
from .attempt_reviews import AttemptReview, AttemptReviewService
from .candidate_document_storage import read_source, safe_candidate_path
from .candidate_documents import (
    CandidateDocument,
    CandidateDocumentError,
    CandidateDocumentReadOnlyError,
    CandidateDocumentService,
    SourceHistory,
    etag_for,
)
from .clock import Clock, UTCClock
from .errors import (
    CandidateFailureError,
    FixtureSetupRequiredError,
    InvalidInputError,
)
from .evaluation_results import (
    PracticeResult,
    practice_result_from_score,
)
from .evaluation import EvaluationService
from .filesystem import Filesystem, LocalFilesystem
from .fixture_setup import FixtureSetupError, populate_runtime_fixture
from .lifecycle import (
    AbandonResult,
    LifecycleService,
    RestartResult,
    Scorer,
    SubmissionResult,
    TimeObservation,
)
from .models import ACTIVE, SUBMITTED, ScoreSummary, SessionRecord
from .persistence import Persistence
from .prompts import PromptResult, PromptService
from .rendering import AttemptContextService, ContextResult, DerivedStatusService
from .scoring import IsolatedAttemptScorer
from .workspace import (
    ATTEMPTS_DIRECTORY,
    ValidatedFixtureCache,
    WorkspaceManager,
)


ScorerFactory = Callable[[AssessmentDefinition], Scorer]


@dataclass(frozen=True, slots=True)
class EvaluationSnapshot:
    """One immutable web evaluation view assembled inside the action boundary."""

    state: SessionRecord
    time: TimeObservation
    source: CandidateDocument
    practice: PracticeResult | None = None
    newly_submitted: bool = False


class RuntimeApplication:
    """Compose the authoritative services used by CLI and web transports."""

    def __init__(
        self,
        workspace_root: Path,
        *,
        clock: Clock | None = None,
        filesystem: Filesystem | None = None,
        persistence: Persistence | None = None,
        scorer_factory: ScorerFactory | None = None,
        cache: ValidatedFixtureCache | None = None,
    ) -> None:
        _validate_root(workspace_root, "workspace root")
        resolved_workspace = workspace_root.resolve()
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
        if cache is None:
            cache = ValidatedFixtureCache.from_runtime_manifest(resolved_workspace)

        self.workspace = WorkspaceManager(
            resolved_workspace,
            cache,
            filesystem=filesystem,
            persistence=persistence,
        )
        self.registry = DEFAULT_ASSESSMENT_REGISTRY
        self.clock = UTCClock() if clock is None else clock
        self.scorer_factory = (
            _default_scorer_factory if scorer_factory is None else scorer_factory
        )
        self.lifecycle = LifecycleService(
            self.workspace,
            self.clock,
            self._score_selected_attempt,
        )
        self.candidate_documents = CandidateDocumentService(self.workspace, self.clock)
        self.evaluation = EvaluationService(self.lifecycle)
        self.prompts = PromptService(self.workspace)
        self.contexts = AttemptContextService(self.workspace)
        self.derived_status = DerivedStatusService(self.workspace)
        self.history = AttemptHistoryService(
            resolved_workspace / ATTEMPTS_DIRECTORY,
            persistence=persistence,
            clock=self.clock,
        )
        self.reviews = AttemptReviewService(
            resolved_workspace / ATTEMPTS_DIRECTORY, persistence=persistence
        )
        self._action_lock = threading.RLock()
        self._practice_results: dict[str, PracticeResult] = {}

    def _score_selected_attempt(self, attempt: Path) -> ScoreSummary:
        """Build the registered assessment scorer for one selected attempt."""
        state = self.workspace.persistence.read_session(attempt)
        definition = self.workspace.definition_for_persisted_session(state)
        scorer = self.scorer_factory(definition)
        score = scorer(attempt)
        self._practice_results[state.attempt_id] = practice_result_from_score(score)
        return score

    def fetch(self, *, source: Path | None) -> dict[str, object]:
        """Populate this workspace's ignored fixture cache from packaged metadata."""
        with self._action_lock:
            try:
                cache_root = populate_runtime_fixture(
                    self.workspace.workspace_root, source_root=source
                )
            except FixtureSetupError as error:
                raise FixtureSetupRequiredError(
                    f"fixture setup is required: {error}"
                ) from error
            return {"fixture_cache": str(cache_root)}

    def start(
        self,
        *,
        assessment: str,
        mode: Literal["full", "drill"],
        drill_duration_seconds: int | None,
    ) -> SessionRecord:
        with self._action_lock:
            return self._start_locked(assessment, mode, drill_duration_seconds)

    def start_snapshot(
        self,
        *,
        assessment: str,
        mode: Literal["full", "drill"],
        drill_duration_seconds: int | None,
    ) -> EvaluationSnapshot:
        """Create an attempt and return its complete initial web view."""
        with self._action_lock:
            state = self._start_locked(assessment, mode, drill_duration_seconds)
            return self._evaluation_snapshot_locked(state)

    def start_web_snapshot(
        self,
        *,
        assessment: str,
        mode: Literal["full", "drill"],
        drill_duration_seconds: int | None,
    ) -> EvaluationSnapshot:
        """Create the browser attempt and return its complete initial view."""
        with self._action_lock:
            state = self._start_locked(assessment, mode, drill_duration_seconds)
            return self._evaluation_snapshot_locked(state)

    def abandon(self, *, attempt_id: str | None, expected_revision: int) -> AbandonResult:
        """End the selected attempt explicitly; shared by CLI and web."""
        with self._action_lock:
            result = self.lifecycle.abandon(
                attempt_id, expected_revision=expected_revision
            )
            self._refresh_derived_status(result.state.attempt_id)
            return result

    def restart(
        self,
        *,
        attempt_id: str | None,
        operation_id: str,
        expected_revision: int,
        mode: Literal["full", "drill"] | None = None,
        drill_duration_seconds: int | None = None,
    ) -> RestartResult:
        """Abandon the selected attempt and create its replacement; shared by CLI and web."""
        with self._action_lock:
            result = self.lifecycle.restart(
                attempt_id,
                operation_id=operation_id,
                expected_revision=expected_revision,
                mode=mode,
                drill_duration_seconds=drill_duration_seconds,
            )
            if not result.replayed:
                self._refresh_derived_status(result.old_attempt_id)
                self._refresh_derived_status(result.replacement_attempt_id)
            return result

    def bootstrap(self) -> dict[str, object]:
        """Return browser entry metadata and the currently selected session."""
        with self._action_lock:
            selected: SessionRecord | None = None
            selected_time: TimeObservation | None = None
            pointer = self.workspace.persistence.read_active_pointer(
                self.workspace.attempts_directory
            )
            if pointer is not None:
                selected = self.status(attempt_id=pointer.attempt_id)
                selected_time = self.time(attempt_id=pointer.attempt_id)
            definition = self.registry.require("file_storage")
            return {
            "assessment": definition.metadata.to_dict(),
            "levels": [
                {"level": level, "label": f"Level {level}"}
                for level in definition.level_groups
            ],
            "profiles": [
                {
                    "mode": "full",
                    "profile_id": "full-90m",
                    "duration_seconds": 5400,
                },
                {
                    "mode": "drill",
                    "profile_id": "drill-30m",
                    "duration_seconds": 1800,
                },
            ],
            "rules": [
                "The timer is authoritative and cannot be paused.",
                "Source changes are saved with optimistic concurrency.",
                "Test and submit use the latest saved source.",
            ],
            "session": None if selected is None else selected.to_dict(),
            "time": None if selected_time is None else {
                "observed_at": selected_time.observed_at.isoformat(),
                "remaining_seconds": selected_time.remaining_seconds,
            },
            }

    def resume(self, *, attempt_id: str | None) -> SessionRecord:
        with self._action_lock:
            state = self.lifecycle.resume(attempt_id)
            self._refresh_derived_status(state.attempt_id)
            return state

    def status(self, *, attempt_id: str | None) -> SessionRecord:
        with self._action_lock:
            state = self.lifecycle.status(attempt_id)
            self._refresh_derived_status(state.attempt_id)
            return state

    def time(self, *, attempt_id: str | None) -> TimeObservation:
        with self._action_lock:
            observation = self.lifecycle.time(attempt_id)
            self._refresh_derived_status(observation.state.attempt_id)
            return observation

    def task(self, *, attempt_id: str | None, level: int) -> PromptResult:
        with self._action_lock:
            result = self.prompts.read_prompt(attempt_id=attempt_id, level=level)
            self._refresh_derived_status(result.attempt_id)
            return result

    def source(self, *, attempt_id: str | None) -> CandidateDocument:
        """Read the registered candidate source through its document service."""
        with self._action_lock:
            return self.candidate_documents.read(attempt_id)

    def source_history(self, *, attempt_id: str | None) -> SourceHistory:
        """Read bounded candidate-only history through its document service."""
        with self._action_lock:
            return self.candidate_documents.list_history(attempt_id)

    def save_source(
        self, *, attempt_id: str | None, content: str, if_match: str
    ) -> CandidateDocument:
        """Replace candidate source with the document service's CAS contract."""
        with self._action_lock:
            return self.candidate_documents.save(attempt_id, content, if_match)

    def reset_source(
        self, *, attempt_id: str | None, if_match: str
    ) -> CandidateDocument:
        """Reset candidate source to its attempt-owned baseline."""
        with self._action_lock:
            return self.candidate_documents.reset(attempt_id, if_match)

    def restore_source(
        self, *, attempt_id: str | None, snapshot_id: str, if_match: str
    ) -> CandidateDocument:
        """Restore one validated attempt-local source snapshot."""
        with self._action_lock:
            return self.candidate_documents.restore(attempt_id, snapshot_id, if_match)

    def test(
        self,
        *,
        attempt_id: str | None,
        source_content: str | None = None,
        if_match: str | None = None,
    ) -> SessionRecord:
        with self._action_lock:
            return self._test_locked(attempt_id, source_content, if_match)

    def test_snapshot(
        self,
        *,
        attempt_id: str | None,
        source_content: str | None = None,
        if_match: str | None = None,
    ) -> EvaluationSnapshot:
        """Evaluate and assemble the web response without crossing an action."""
        with self._action_lock:
            try:
                state = self._test_locked(attempt_id, source_content, if_match)
            except CandidateFailureError:
                state = self.lifecycle.status(attempt_id)
            return self._evaluation_snapshot_locked(
                state,
                practice=self._practice_for_state(state),
            )

    def submit(
        self,
        *,
        attempt_id: str | None,
        source_content: str | None = None,
        if_match: str | None = None,
    ) -> SubmissionResult:
        with self._action_lock:
            return self._submit_locked(attempt_id, source_content, if_match)

    def submit_snapshot(
        self,
        *,
        attempt_id: str | None,
        source_content: str | None = None,
        if_match: str | None = None,
    ) -> EvaluationSnapshot:
        """Submit and assemble the web response without crossing an action."""
        with self._action_lock:
            result = self._submit_locked(attempt_id, source_content, if_match)
            return self._evaluation_snapshot_locked(
                result.state,
                practice=self._practice_for_state(result.state),
                newly_submitted=result.newly_submitted,
            )

    def _test_locked(
        self,
        attempt_id: str | None,
        source_content: str | None,
        if_match: str | None,
    ) -> SessionRecord:
        self._save_before_evaluation(attempt_id, source_content, if_match)
        try:
            state = self.evaluation.test(attempt_id)
        except CandidateFailureError:
            # Scoring has already persisted its authoritative transition when
            # EvaluationService reports candidate failure.
            state = self.lifecycle.status(attempt_id)
            self._refresh_derived_status(state.attempt_id)
            raise
        self._refresh_derived_status(state.attempt_id)
        return state

    def _start_locked(
        self,
        assessment: str,
        mode: Literal["full", "drill"],
        drill_duration_seconds: int | None,
    ) -> SessionRecord:
        definition = self.registry.require(assessment)
        # ``create_attempt`` validates the same complete cache again immediately
        # before it creates any workspace path, closing the validation-to-write gap.
        try:
            self.workspace.cache.validate(self.workspace.filesystem)
        except FixtureSetupRequiredError as error:
            raise FixtureSetupRequiredError(
                f"{error.message}; run "
                "`codesignal-sim fetch --workspace-root "
                f"{self.workspace.workspace_root}`"
            ) from error
        # CLI and browser share one policy: a selected live attempt is never
        # replaced silently by a plain start (D001).
        state = self.lifecycle.start_exclusive(
            definition.metadata,
            mode=mode,  # type: ignore[arg-type]
            drill_duration_seconds=drill_duration_seconds,
        )
        self._refresh_derived_status(state.attempt_id)
        return state

    def _submit_locked(
        self,
        attempt_id: str | None,
        source_content: str | None,
        if_match: str | None,
    ) -> SubmissionResult:
        self._save_before_evaluation(attempt_id, source_content, if_match)
        result = self.evaluation.submit(attempt_id)
        if result.newly_submitted:
            self._refresh_derived_status(result.state.attempt_id)
        return result

    def _refresh_derived_status(self, attempt_id: str) -> None:
        """Refresh derived context without changing an operation's outcome."""
        try:
            self.derived_status.refresh(attempt_id)
        except Exception:
            # The built-in renderer swallows its own filesystem/state failures.
            # Keep this outer guard for injected replacement services so their
            # failure cannot change an authoritative CLI or web result.
            pass

    def _evaluation_snapshot_locked(
        self,
        state: SessionRecord,
        *,
        practice: PracticeResult | None = None,
        newly_submitted: bool = False,
    ) -> EvaluationSnapshot:
        observation = self.lifecycle.time(state.attempt_id)
        self._refresh_derived_status(observation.state.attempt_id)
        source = self.candidate_documents.read(state.attempt_id)
        return EvaluationSnapshot(
            state=observation.state,
            time=observation,
            source=source,
            practice=practice,
            newly_submitted=newly_submitted,
        )

    def _practice_for_state(self, state: SessionRecord) -> PracticeResult | None:
        if state.score is None:
            return None
        return self._practice_results.get(state.attempt_id) or practice_result_from_score(
            state.score,
        )

    def _save_before_evaluation(
        self,
        attempt_id: str | None,
        source_content: str | None,
        if_match: str | None,
    ) -> None:
        if source_content is None and if_match is None:
            return
        if source_content is None or if_match is None:
            raise InvalidInputError("source content and If-Match must be supplied together")
        status = self.status(attempt_id=attempt_id).status
        if status == ACTIVE:
            self.save_source(
                attempt_id=attempt_id,
                content=source_content,
                if_match=if_match,
            )
            return
        if status == SUBMITTED:
            # A repeat request returns the committed result. The payload is never
            # applied, so it cannot replace the immutable submitted source.
            return
        self._reject_terminal_source_mutation(attempt_id, source_content)

    def _reject_terminal_source_mutation(
        self, attempt_id: str | None, source_content: str
    ) -> None:
        """Refuse a payload that would change an expired or abandoned attempt.

        Silently dropping it hid real edits (D002). A payload identical to the
        saved source is not a mutation, so an expired submit still finalizes the
        saved revision.
        """
        if self.status(attempt_id=attempt_id).status == SUBMITTED:
            # Another writer finalized between the observation above and here; a
            # repeat request returns the committed result rather than an error.
            return
        try:
            saved = self._saved_source_digest(attempt_id)
            supplied = etag_for(source_content)
        except CandidateDocumentError:
            saved, supplied = None, ""
        if saved is None or saved != supplied:
            raise CandidateDocumentReadOnlyError(
                "candidate source is read-only after expiry or submission"
            )

    def _saved_source_digest(self, attempt_id: str | None) -> str | None:
        """Read the saved source without creating baselines or history."""
        with self.workspace.selected_attempt(attempt_id) as attempt:
            state = self.workspace.persistence.read_session(attempt)
            definition = self.workspace.definition_for_persisted_session(state)
            path = safe_candidate_path(attempt, definition.candidate_filename)
            return etag_for(read_source(self.workspace.filesystem, path))

    def list_attempts(
        self,
        *,
        filters: HistoryFilters | Mapping[str, object] | None = None,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> HistoryPage:
        """List stored attempts from metadata only; never selects or repairs."""
        with self._action_lock:
            return self.history.list_attempts(filters=filters, cursor=cursor, limit=limit)

    def review(self, *, attempt_id: str, include_source: bool = True) -> AttemptReview:
        """Read one attempt's stored review by explicit ID; never selects or repairs."""
        with self._action_lock:
            return self.reviews.get_review(attempt_id, include_source=include_source)

    def context(
        self,
        *,
        attempt_id: str | None,
        output_format: Literal["markdown", "json"],
    ) -> ContextResult:
        with self._action_lock:
            return self.contexts.read(
                attempt_id=attempt_id,
                output_format=output_format,  # type: ignore[arg-type]
            )


def create_application(
    workspace_root: Path,
    *,
    clock: Clock | None = None,
    filesystem: Filesystem | None = None,
    persistence: Persistence | None = None,
    scorer_factory: ScorerFactory | None = None,
) -> RuntimeApplication:
    """Create the production application graph with testable seams."""
    return RuntimeApplication(
        workspace_root,
        clock=clock,
        filesystem=filesystem,
        persistence=persistence,
        scorer_factory=scorer_factory,
    )


def _default_scorer_factory(definition: AssessmentDefinition) -> Scorer:
    return IsolatedAttemptScorer(definition).score


def _validate_root(path: Path, label: str) -> None:
    """Reject invalid filesystem destinations before any service can mutate them."""
    try:
        resolved = path.resolve()
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            raise InvalidInputError(f"{label} must be a non-symlink directory")
        ancestor = resolved
        while not ancestor.exists() and ancestor != ancestor.parent:
            ancestor = ancestor.parent
        if not ancestor.is_dir():
            raise InvalidInputError(f"{label} parent must be a directory")
        destination = resolved / ATTEMPTS_DIRECTORY
        if destination == resolved or resolved not in destination.parents:
            raise InvalidInputError(f"{label} attempts destination is invalid")
    except OSError as error:
        raise InvalidInputError(f"{label} must be a valid path") from error


__all__ = [
    "EvaluationSnapshot",
    "RuntimeApplication",
    "ScorerFactory",
    "create_application",
]
