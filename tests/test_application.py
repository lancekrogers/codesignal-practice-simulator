"""Composition tests for the shared runtime application graph."""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from codesignal_practice_simulator.assessments import AssessmentDefinition
from codesignal_practice_simulator.application import (
    RuntimeApplication,
    create_application,
)
from codesignal_practice_simulator.errors import InvalidInputError
from codesignal_practice_simulator.filesystem import LocalFilesystem
from codesignal_practice_simulator.lifecycle import LifecycleService, Scorer
from codesignal_practice_simulator.models import LevelResult, ScoreSummary
from codesignal_practice_simulator.persistence import Persistence
from codesignal_practice_simulator.evaluation import EvaluationService
from codesignal_practice_simulator.prompts import PromptService
from codesignal_practice_simulator.rendering import (
    AttemptContextService,
    DerivedStatusService,
)
from codesignal_practice_simulator.workspace import (
    CACHE_INPUTS,
    ValidatedFixtureCache,
    WorkspaceManager,
)


START = datetime(2026, 9, 8, 19, 0, tzinfo=timezone.utc)


class FakeClock:
    def now(self) -> datetime:
        return START


class ControlledClock:
    def __init__(self, *values: datetime) -> None:
        self.values = list(values)

    def now(self) -> datetime:
        if not self.values:
            raise AssertionError("controlled clock was observed unexpectedly")
        return self.values.pop(0)


def make_cache(root: Path) -> ValidatedFixtureCache:
    cache = root / "cache"
    contents = {"vendor-readme.md": b"synthetic vendor fixture\n"}
    contents.update(
        {
            f"assessment/file_storage/{name}": f"synthetic {name}\n".encode()
            for name in CACHE_INPUTS
        }
    )
    hashes: dict[str, str] = {}
    for relative, data in contents.items():
        path = cache.joinpath(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        hashes[relative] = hashlib.sha256(data).hexdigest()
    return ValidatedFixtureCache(cache, hashes)


class ApplicationCompositionTests(unittest.TestCase):
    def test_factory_forwards_scorer_factory(self) -> None:
        def scorer_factory(_definition: AssessmentDefinition) -> Scorer:
            def score(_attempt: Path) -> ScoreSummary:
                raise AssertionError("test scorer should not run")

            return score

        workspace_root = Path("workspace")

        with patch(
            "codesignal_practice_simulator.application.RuntimeApplication"
        ) as runtime:
            result = create_application(
                workspace_root,
                scorer_factory=scorer_factory,
            )

        self.assertIs(result, runtime.return_value)
        runtime.assert_called_once_with(
            workspace_root,
            clock=None,
            filesystem=None,
            persistence=None,
            scorer_factory=scorer_factory,
        )

    def test_factory_injects_filesystem_persistence_and_clock_into_one_graph(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace_root = Path(directory) / "workspace"
            workspace_root.mkdir()
            filesystem = LocalFilesystem()
            persistence = Persistence(filesystem)
            clock = FakeClock()

            application = create_application(
                workspace_root,
                clock=clock,
                filesystem=filesystem,
                persistence=persistence,
            )

            self.assertIsInstance(application, RuntimeApplication)
            self.assertIs(application.workspace.filesystem, filesystem)
            self.assertIs(application.workspace.persistence, persistence)
            self.assertIs(application.lifecycle, application.evaluation.lifecycle)
            self.assertIs(application.lifecycle.workspace, application.workspace)
            self.assertIs(application.lifecycle.clock, clock)
            self.assertIsInstance(application.workspace, WorkspaceManager)
            self.assertIsInstance(application.lifecycle, LifecycleService)
            self.assertIsInstance(application.evaluation, EvaluationService)
            self.assertIsInstance(application.prompts, PromptService)
            self.assertIsInstance(application.contexts, AttemptContextService)
            self.assertIsInstance(application.derived_status, DerivedStatusService)

    def test_rejects_mismatched_filesystem_and_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace_root = Path(directory) / "workspace"
            workspace_root.mkdir()
            filesystem = LocalFilesystem()
            persistence = Persistence(LocalFilesystem())

            with self.assertRaisesRegex(InvalidInputError, "same filesystem"):
                RuntimeApplication(
                    workspace_root,
                    filesystem=filesystem,
                    persistence=persistence,
                    cache=make_cache(Path(directory)),
                )

    def test_rejects_a_dangling_workspace_root_without_target_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target_parent = root / "unowned-target"
            target_parent.mkdir()
            sentinel = target_parent / "sentinel.txt"
            sentinel.write_text("keep\n", encoding="utf-8")
            target = target_parent / "workspace"
            workspace_root = root / "workspace-alias"
            workspace_root.symlink_to(target, target_is_directory=True)

            with self.assertRaisesRegex(
                InvalidInputError, "must be a non-symlink directory"
            ):
                RuntimeApplication(
                    workspace_root,
                    cache=make_cache(root),
                )

            self.assertFalse(target.exists())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")
            self.assertTrue(workspace_root.is_symlink())

    def test_scorer_factory_uses_persisted_registry_definition_and_refreshes_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace_root = root / "workspace"
            workspace_root.mkdir()
            expected = ScoreSummary(
                tuple(LevelResult(level, "passed") for level in range(1, 5))
            )
            scorer_calls: list[tuple[object, Path]] = []

            def scorer_factory(definition):
                def score(attempt: Path) -> ScoreSummary:
                    scorer_calls.append((definition, attempt))
                    return expected

                return score

            application = RuntimeApplication(
                workspace_root,
                clock=FakeClock(),
                filesystem=LocalFilesystem(),
                scorer_factory=scorer_factory,
                cache=make_cache(root),
            )

            state = application.start(
                assessment="file_storage",
                mode="full",
                drill_duration_seconds=None,
            )
            attempt = workspace_root / "attempts" / state.attempt_id
            self.assertTrue((attempt / "STATUS.md").is_file())

            tested = application.test(attempt_id=state.attempt_id)

            self.assertEqual(tested.score, expected)
            self.assertEqual(len(scorer_calls), 1)
            self.assertEqual(scorer_calls[0][1], attempt.resolve())
            self.assertIn("tested", (attempt / "STATUS.md").read_text())

    def test_success_snapshot_refreshes_status_after_final_deadline_observation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            deadline = START + timedelta(seconds=1)
            score = ScoreSummary(tuple(LevelResult(level, "passed") for level in range(1, 5)))
            application = self._snapshot_application(
                root,
                ControlledClock(START, START, START, deadline),
                score,
            )
            started = application.start(
                assessment="file_storage",
                mode="drill",
                drill_duration_seconds=1,
            )

            snapshot = application.test_snapshot(attempt_id=started.attempt_id)

            self._assert_expired_snapshot(
                application,
                snapshot,
                started.attempt_id,
                ["started", "tested", "expired"],
            )

    def test_candidate_failure_snapshot_refreshes_status_after_final_deadline_observation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            deadline = START + timedelta(seconds=1)
            score = ScoreSummary(tuple(LevelResult(level, "failed") for level in range(1, 5)))
            application = self._snapshot_application(
                root,
                ControlledClock(START, START, START, START, START, deadline),
                score,
            )
            started = application.start(
                assessment="file_storage",
                mode="drill",
                drill_duration_seconds=1,
            )

            snapshot = application.test_snapshot(attempt_id=started.attempt_id)

            self._assert_expired_snapshot(
                application,
                snapshot,
                started.attempt_id,
                ["started", "tested", "expired"],
            )

    def _snapshot_application(
        self, root: Path, clock: ControlledClock, score: ScoreSummary
    ) -> RuntimeApplication:
        workspace_root = root / "workspace"
        workspace_root.mkdir()
        return RuntimeApplication(
            workspace_root,
            clock=clock,
            cache=make_cache(root),
            scorer_factory=lambda _definition: lambda _attempt: score,
        )

    def _assert_expired_snapshot(
        self,
        application: RuntimeApplication,
        snapshot,
        attempt_id: str,
        event_names: list[str],
    ) -> None:
        self.assertEqual(snapshot.state.status, "expired")
        self.assertEqual(snapshot.time.state.status, "expired")
        attempt = application.workspace.attempts_directory / attempt_id
        self.assertIn("- Status: `expired`", (attempt / "STATUS.md").read_text())
        context = application.context(
            attempt_id=attempt_id,
            output_format="json",
        ).to_dict()["context"]
        self.assertEqual(context["lifecycle"]["status"], "expired")
        self.assertEqual([event["name"] for event in context["events"]], event_names)


if __name__ == "__main__":
    unittest.main()
