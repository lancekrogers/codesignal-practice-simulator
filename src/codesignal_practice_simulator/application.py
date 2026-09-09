"""Shared dependency-injected application graph for simulator transports."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Literal

from .assessments import (
    AssessmentDefinition,
    DEFAULT_ASSESSMENT_REGISTRY,
)
from .clock import Clock, UTCClock
from .errors import FixtureSetupRequiredError, InvalidInputError
from .evaluation import EvaluationService
from .filesystem import Filesystem, LocalFilesystem
from .fixture_setup import FixtureSetupError, populate_runtime_fixture
from .lifecycle import LifecycleService, Scorer, SubmissionResult, TimeObservation
from .models import ScoreSummary, SessionState
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
        self.evaluation = EvaluationService(self.lifecycle)
        self.prompts = PromptService(self.workspace)
        self.contexts = AttemptContextService(self.workspace)
        self.derived_status = DerivedStatusService(self.workspace)

    def _score_selected_attempt(self, attempt: Path) -> ScoreSummary:
        """Build the registered assessment scorer for one selected attempt."""
        state = self.workspace.persistence.read_session(attempt)
        definition = self.workspace.definition_for_persisted_session(state)
        return self.scorer_factory(definition)(attempt)

    def fetch(self, *, source: Path | None) -> dict[str, object]:
        """Populate this workspace's ignored fixture cache from packaged metadata."""
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
    ) -> SessionState:
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
        state = self.lifecycle.start(
            definition.metadata,
            mode=mode,  # type: ignore[arg-type]
            drill_duration_seconds=drill_duration_seconds,
        )
        self.derived_status.refresh(state.attempt_id)
        return state

    def resume(self, *, attempt_id: str | None) -> SessionState:
        state = self.lifecycle.resume(attempt_id)
        self.derived_status.refresh(state.attempt_id)
        return state

    def status(self, *, attempt_id: str | None) -> SessionState:
        state = self.lifecycle.status(attempt_id)
        self.derived_status.refresh(state.attempt_id)
        return state

    def time(self, *, attempt_id: str | None) -> TimeObservation:
        observation = self.lifecycle.time(attempt_id)
        self.derived_status.refresh(observation.state.attempt_id)
        return observation

    def task(self, *, attempt_id: str | None, level: int) -> PromptResult:
        result = self.prompts.read_prompt(attempt_id=attempt_id, level=level)
        self.derived_status.refresh(result.attempt_id)
        return result

    def test(self, *, attempt_id: str | None) -> SessionState:
        state = self.evaluation.test(attempt_id)
        self.derived_status.refresh(state.attempt_id)
        return state

    def submit(self, *, attempt_id: str | None) -> SubmissionResult:
        result = self.evaluation.submit(attempt_id)
        if result.newly_submitted:
            self.derived_status.refresh(result.state.attempt_id)
        return result

    def context(
        self,
        *,
        attempt_id: str | None,
        output_format: Literal["markdown", "json"],
    ) -> ContextResult:
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
        if path.exists() and (not path.is_dir() or path.is_symlink()):
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


__all__ = ["RuntimeApplication", "ScorerFactory", "create_application"]
