"""Shared abandon/restart actions, live-selection policy, and CLI wiring."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

from tests.workspace_test_support import (
    PROJECT,
    ValidatedFixtureCache,
    WorkspaceManager,
    make_cache,
    session,
    tree_bytes,
)

from codesignal_practice_simulator import cli
from codesignal_practice_simulator.application import RuntimeApplication
from codesignal_practice_simulator.assessments import FILE_STORAGE
from codesignal_practice_simulator.attempt_reviews import AttemptReviewService
from codesignal_practice_simulator.errors import (
    AssessmentVersionUnavailableError,
    IllegalLifecycleError,
    InvalidInputError,
    LiveSelectionError,
    LockUnavailableError,
    RestartConflictError,
    RestartRecoveryPendingError,
    ReviewPendingError,
    SessionCorruptError,
    StaleRevisionError,
)
from codesignal_practice_simulator.filesystem import LocalFilesystem
from codesignal_practice_simulator.lifecycle import (
    AbandonResult,
    LifecycleService,
    RestartResult,
)
from codesignal_practice_simulator.models import (
    ABANDONED,
    ACTIVE,
    CONTENT_IDENTITY_UNAVAILABLE,
    DRILL_DEFAULT_DURATION_SECONDS,
    DRILL_MODE,
    DRILL_PROFILE,
    EVENT_SCHEMA_VERSION,
    EVENT_SCHEMA_VERSION_V2,
    EXPIRED,
    FULL_DURATION_SECONDS,
    SESSION_SCHEMA_VERSION_V2,
    SUBMITTED,
    AssessmentMetadata,
    LevelResult,
    ModeProfile,
    ScoreSummary,
    SessionStateV2,
)
from codesignal_practice_simulator.persistence import (
    ABANDONMENT_RECOVERY_FILENAME,
    Persistence,
)


LEGACY_START = datetime(2026, 9, 8, 19, tzinfo=timezone.utc)
FILE_STORAGE_METADATA = AssessmentMetadata("file_storage", "File Storage")


class FakeClock:
    def __init__(self, value: datetime = LEGACY_START) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


class RecordingScorer:
    def __init__(self) -> None:
        self.calls: list[Path] = []

    def __call__(self, attempt: Path) -> ScoreSummary:
        self.calls.append(attempt)
        return ScoreSummary(
            tuple(
                LevelResult(level, "passed" if level < 3 else "failed")
                for level in range(1, 5)
            )
        )


class FailOnceFilesystem(LocalFilesystem):
    """Fail one durable operation on one filename inside one attempt directory."""

    def __init__(self, operation: str, filename: str, attempt_id: str) -> None:
        self.operation = operation
        self.filename = filename
        self.attempt_id = attempt_id
        self.failed = False

    def _hit(self, operation: str, path: Path) -> bool:
        if (
            self.failed
            or operation != self.operation
            or path.name != self.filename
            or path.parent.name != self.attempt_id
        ):
            return False
        self.failed = True
        return True

    def replace(self, source: Path, destination: Path) -> None:
        if self._hit("replace", destination):
            raise OSError("injected replace failure")
        super().replace(source, destination)

    def append_bytes(self, path: Path, data: bytes) -> None:
        if self._hit("append_bytes", path):
            raise OSError("injected append failure")
        super().append_bytes(path, data)


class EventsUnavailableFilesystem(LocalFilesystem):
    """Keep one attempt's event log unwritable so an append cannot be retried."""

    def __init__(self, attempt_id: str) -> None:
        self.attempt_id = attempt_id

    def _blocked(self, path: Path) -> bool:
        return path.name == "events.jsonl" and path.parent.name == self.attempt_id

    def append_bytes(self, path: Path, data: bytes) -> None:
        if self._blocked(path):
            raise OSError("injected append failure")
        super().append_bytes(path, data)

    def replace(self, source: Path, destination: Path) -> None:
        if self._blocked(destination):
            raise OSError("injected replace failure")
        super().replace(source, destination)


def _events(attempt: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in (attempt / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]


class ActionsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workspace_root = self.root / "workspace"
        self.workspace_root.mkdir()
        self.cache: ValidatedFixtureCache = make_cache(self.root)
        self.clock = FakeClock()
        self.scorer = RecordingScorer()
        self.manager = WorkspaceManager(self.workspace_root, self.cache)
        self.service = LifecycleService(self.manager, self.clock, self.scorer)
        self.attempts = self.workspace_root / "attempts"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def use_filesystem(self, filesystem: LocalFilesystem) -> None:
        persistence = Persistence(filesystem)
        self.manager.filesystem = filesystem
        self.manager.persistence = persistence
        self.service.persistence = persistence

    def upgraded_cache(self) -> ValidatedFixtureCache:
        """The same bytes published under a newer upstream commit."""
        return ValidatedFixtureCache(self.cache.root, dict(self.cache.hashes), "upstream-1111111")

    def attempt(self, attempt_id: str) -> Path:
        return self.attempts / attempt_id

    def pointer(self) -> str | None:
        pointer = Persistence().read_active_pointer(self.attempts)
        return None if pointer is None else pointer.attempt_id

    def application(self, **overrides: object) -> RuntimeApplication:
        options: dict[str, object] = {
            "clock": self.clock,
            "cache": self.cache,
            "scorer_factory": lambda _definition: self.scorer,
        }
        options.update(overrides)
        return RuntimeApplication(self.workspace_root, **options)  # type: ignore[arg-type]


class AbandonTests(ActionsTestCase):
    def test_abandon_ends_an_active_attempt_once_and_replays_at_the_same_revision(self) -> None:
        state = self.service.start(FILE_STORAGE_METADATA)
        tested = self.service.test(state.attempt_id)
        attempt = self.attempt(state.attempt_id)
        source_before = (attempt / "simulation.py").read_bytes()
        self.clock.value = LEGACY_START + timedelta(minutes=7)

        result = self.service.abandon(state.attempt_id, expected_revision=tested.revision)

        self.assertTrue(result.newly_abandoned)
        ended = result.state
        self.assertIsInstance(ended, SessionStateV2)
        self.assertEqual(ended.status, ABANDONED)
        self.assertEqual(ended.revision, tested.revision + 1)
        self.assertEqual(ended.started_at, state.started_at)
        self.assertEqual(ended.deadline_at, state.deadline_at)
        self.assertIsNone(ended.score)
        self.assertEqual(ended.abandonment.ended_at, self.clock.value)
        self.assertEqual(ended.abandonment.reason, "ended")
        self.assertEqual(ended.abandonment.practice_score, tested.score)
        self.assertEqual((attempt / "simulation.py").read_bytes(), source_before)
        last = _events(attempt)[-1]
        self.assertEqual((last["name"], last["arguments"]), ("abandoned", {"reason": "ended"}))
        self.assertFalse((attempt / ABANDONMENT_RECOVERY_FILENAME).exists())
        self.assertEqual(self.pointer(), state.attempt_id)
        after = tree_bytes(attempt)

        repeat = self.service.abandon(state.attempt_id, expected_revision=tested.revision)

        self.assertFalse(repeat.newly_abandoned)
        self.assertEqual(repeat.state, ended)
        self.assertEqual(tree_bytes(attempt), after)
        with self.assertRaisesRegex(StaleRevisionError, "refresh and retry"):
            self.service.abandon(state.attempt_id, expected_revision=tested.revision + 1)
        for command in (self.service.resume, self.service.test, self.service.submit):
            with self.subTest(command=command.__name__):
                with self.assertRaisesRegex(IllegalLifecycleError, "abandoned state"):
                    command(state.attempt_id)
        self.assertEqual(tree_bytes(attempt), after)
        self.assertEqual(len(self.scorer.calls), 1)

    def test_abandon_rejects_stale_terminal_and_overdue_attempts(self) -> None:
        state = self.service.start(FILE_STORAGE_METADATA)
        attempt = self.attempt(state.attempt_id)
        before = tree_bytes(attempt)

        with self.assertRaisesRegex(StaleRevisionError, "expected revision 3, current 0"):
            self.service.abandon(state.attempt_id, expected_revision=3)
        self.assertEqual(tree_bytes(attempt), before)
        for revision in (-1, True, "0"):
            with self.assertRaises(InvalidInputError):
                self.service.abandon(state.attempt_id, expected_revision=revision)  # type: ignore[arg-type]

        # An overdue attempt is expired first; expiry is the only mutation.
        self.clock.value = state.deadline_at
        with self.assertRaisesRegex(IllegalLifecycleError, "expired state"):
            self.service.abandon(state.attempt_id, expected_revision=0)
        self.assertEqual(self.manager.persistence.read_session(attempt).status, EXPIRED)
        self.assertEqual([event["name"] for event in _events(attempt)], ["started", "expired"])
        expired = tree_bytes(attempt)
        with self.assertRaisesRegex(IllegalLifecycleError, "expired state"):
            self.service.abandon(state.attempt_id, expected_revision=1)
        self.assertEqual(tree_bytes(attempt), expired)

        submitted = self.service.submit(state.attempt_id).state
        final = tree_bytes(attempt)
        with self.assertRaisesRegex(IllegalLifecycleError, "submitted state"):
            self.service.abandon(state.attempt_id, expected_revision=submitted.revision)
        self.assertEqual(tree_bytes(attempt), final)
        self.assertEqual(len(self.scorer.calls), 1)

    def test_legacy_v1_abandonment_is_a_recoverable_upgrade(self) -> None:
        legacy = session(str(uuid4()))
        self.manager.create_attempt(legacy)
        neighbor = session(str(uuid4()))
        self.manager.create_attempt(neighbor)
        neighbor_before = tree_bytes(self.attempt(neighbor.attempt_id))
        attempt = self.attempt(legacy.attempt_id)
        source_before = (attempt / "simulation.py").read_bytes()
        self.clock.value = LEGACY_START + timedelta(minutes=3)
        boundaries = {
            "session replace": lambda: FailOnceFilesystem(
                "replace", "session.json", legacy.attempt_id
            ),
            "event log unavailable": lambda: EventsUnavailableFilesystem(legacy.attempt_id),
        }
        for label, build in boundaries.items():
            with self.subTest(boundary=label):
                self.use_filesystem(build())
                with self.assertRaises((OSError, RestartRecoveryPendingError, Exception)) as failure:
                    self.service.abandon(legacy.attempt_id, expected_revision=0)
                self.assertNotIsInstance(failure.exception, AssertionError)
                self.assertTrue((attempt / ABANDONMENT_RECOVERY_FILENAME).is_file())
                self.assertEqual((attempt / "simulation.py").read_bytes(), source_before)
                # Read-only review reports the pending upgrade instead of guessing.
                with self.assertRaises(ReviewPendingError):
                    AttemptReviewService(self.attempts).get_review(legacy.attempt_id)

                self.use_filesystem(LocalFilesystem())
                recovered = self.service.status(legacy.attempt_id)

                self.assertIsInstance(recovered, SessionStateV2)
                self.assertEqual(recovered.status, ABANDONED)
                self.assertEqual(recovered.revision, 1)
                self.assertEqual(recovered.content_identity, CONTENT_IDENTITY_UNAVAILABLE)
                self.assertEqual(recovered.assessment, legacy.assessment)
                self.assertFalse((attempt / ABANDONMENT_RECOVERY_FILENAME).exists())
                raw = json.loads((attempt / "session.json").read_text("utf-8"))
                self.assertEqual(raw["schema_version"], SESSION_SCHEMA_VERSION_V2)
                self.assertNotIn("content_version", json.dumps(raw))
                self.assertEqual(
                    [(event["schema_version"], event["name"]) for event in _events(attempt)],
                    [(EVENT_SCHEMA_VERSION, "started"), (EVENT_SCHEMA_VERSION_V2, "abandoned")],
                )
                repeat = self.service.abandon(legacy.attempt_id, expected_revision=0)
                self.assertFalse(repeat.newly_abandoned)
                self.assertEqual(repeat.state, recovered)
                review = AttemptReviewService(self.attempts).get_review(legacy.attempt_id)
                self.assertEqual(review.status, ABANDONED)
                self.assertEqual(review.assessment.content_identity, CONTENT_IDENTITY_UNAVAILABLE)
                # Only the first boundary performs the upgrade; the second observes it.
                if label == "session replace":
                    self.manager.persistence.write_session(attempt, legacy)
                    (attempt / "events.jsonl").write_bytes(
                        (attempt / "events.jsonl").read_bytes().splitlines(keepends=True)[0]
                    )
        self.assertEqual(tree_bytes(self.attempt(neighbor.attempt_id)), neighbor_before)
        self.assertEqual(self.pointer(), neighbor.attempt_id)

    def test_abandon_does_not_require_the_pinned_content_to_still_be_installed(self) -> None:
        state = self.service.start(FILE_STORAGE_METADATA)
        upgraded = LifecycleService(
            WorkspaceManager(self.workspace_root, self.upgraded_cache()), self.clock, self.scorer
        )
        with self.assertRaises(AssessmentVersionUnavailableError):
            upgraded.resume(state.attempt_id)  # continuing still needs the content

        ended = upgraded.abandon(state.attempt_id, expected_revision=0)

        self.assertTrue(ended.newly_abandoned)
        self.assertEqual(ended.state.assessment, state.assessment)
        self.assertEqual(ended.state.content_identity, "pinned")

    def test_uninterpretable_legacy_record_blocks_abandon_but_not_review(self) -> None:
        legacy = session(str(uuid4()))
        attempt = self.manager.create_attempt(legacy)
        raw = json.loads((attempt / "session.json").read_text("utf-8"))
        raw["assessment"]["display_name"] = "Renamed Elsewhere"
        (attempt / "session.json").write_text(json.dumps(raw), encoding="utf-8")
        before = tree_bytes(attempt)

        with self.assertRaisesRegex(SessionCorruptError, "does not match the registry"):
            self.service.abandon(legacy.attempt_id, expected_revision=0)
        with self.assertRaisesRegex(SessionCorruptError, "does not match the registry"):
            self.service.restart(
                legacy.attempt_id, operation_id=str(uuid4()), expected_revision=0
            )

        self.assertEqual(tree_bytes(attempt), before)
        review = AttemptReviewService(self.attempts).get_review(legacy.attempt_id)
        self.assertEqual(review.assessment.display_name, "Renamed Elsewhere")


class RestartServiceTests(ActionsTestCase):
    def test_restart_defaults_to_the_old_assessment_and_profile_and_replays(self) -> None:
        state = self.service.start(
            FILE_STORAGE_METADATA, mode="drill", drill_duration_seconds=900
        )
        operation = str(uuid4())
        self.clock.value = LEGACY_START + timedelta(minutes=2)

        result = self.service.restart(
            state.attempt_id, operation_id=operation, expected_revision=0
        )

        self.assertIsInstance(result, RestartResult)
        self.assertFalse(result.replayed)
        self.assertEqual(result.replacement_state.profile, state.profile)
        self.assertEqual(result.replacement_state.assessment, state.assessment)
        self.assertEqual(result.replacement_state.started_at, self.clock.value)
        self.assertEqual(result.abandoned_state.abandonment.reason, "restarted")
        self.assertEqual(self.pointer(), result.replacement_attempt_id)

        # Implicit selection resolves to the replacement; a replay does nothing.
        self.assertEqual(self.service.status().attempt_id, result.replacement_attempt_id)
        replay = self.service.restart(
            state.attempt_id, operation_id=operation, expected_revision=0
        )
        self.assertTrue(replay.replayed)
        self.assertEqual(replay.replacement_attempt_id, result.replacement_attempt_id)
        with self.assertRaises(RestartConflictError):
            self.service.restart(
                state.attempt_id, operation_id=operation, expected_revision=0, mode="full"
            )
        # A stale tab still holding revision 0 of the live replacement gets a
        # stale-state conflict; one holding the abandoned attempt is told its
        # terminal state. Neither creates a second replacement.
        self.service.test(result.replacement_attempt_id)
        with self.assertRaisesRegex(StaleRevisionError, "refresh and retry"):
            self.service.restart(
                result.replacement_attempt_id, operation_id=str(uuid4()), expected_revision=0
            )
        with self.assertRaisesRegex(IllegalLifecycleError, "abandoned state"):
            self.service.restart(
                state.attempt_id, operation_id=str(uuid4()), expected_revision=0
            )
        self.assertEqual(
            len([child for child in self.attempts.iterdir() if child.is_dir() and not child.name.startswith(".")]),
            2,
        )
        with self.assertRaisesRegex(InvalidInputError, "requires drill mode"):
            self.service.restart(
                result.replacement_attempt_id,
                operation_id=str(uuid4()),
                expected_revision=0,
                drill_duration_seconds=300,
            )

    def test_restart_after_a_content_update_lands_on_the_installed_content(self) -> None:
        state = self.service.start(FILE_STORAGE_METADATA)
        upgraded_cache = self.upgraded_cache()
        upgraded = LifecycleService(
            WorkspaceManager(self.workspace_root, upgraded_cache), self.clock, self.scorer
        )
        self.clock.value = LEGACY_START + timedelta(minutes=1)

        result = upgraded.restart(
            state.attempt_id, operation_id=str(uuid4()), expected_revision=0
        )

        self.assertEqual(
            result.replacement_state.assessment,
            upgraded_cache.pinned_assessment(FILE_STORAGE),
        )
        self.assertEqual(result.replacement_state.assessment.content_version, "upstream-1111111")
        self.assertEqual(result.abandoned_state.assessment, state.assessment)
        self.assertEqual(upgraded.status().attempt_id, result.replacement_attempt_id)

    def test_restart_expires_an_overdue_attempt_and_then_refuses(self) -> None:
        state = self.service.start(FILE_STORAGE_METADATA)
        attempt = self.attempt(state.attempt_id)
        self.clock.value = state.deadline_at

        with self.assertRaisesRegex(IllegalLifecycleError, "expired state"):
            self.service.restart(
                state.attempt_id, operation_id=str(uuid4()), expected_revision=0
            )

        self.assertEqual(self.manager.persistence.read_session(attempt).status, EXPIRED)
        self.assertEqual(self.pointer(), state.attempt_id)
        self.assertEqual(
            [child.name for child in self.attempts.iterdir() if child.is_dir() and not child.name.startswith(".")],
            [state.attempt_id],
        )

    def test_restart_and_submit_are_serialized_by_the_old_attempt_lock(self) -> None:
        state = self.service.start(FILE_STORAGE_METADATA)
        attempt = self.attempt(state.attempt_id)
        before = tree_bytes(attempt)

        # Scoring in another process holds the attempt lock: bounded busy error.
        with self.manager.persistence.attempt_lock(attempt):
            with self.assertRaisesRegex(LockUnavailableError, "busy"):
                LifecycleService(
                    WorkspaceManager(self.workspace_root, self.cache), self.clock, self.scorer
                ).restart(state.attempt_id, operation_id=str(uuid4()), expected_revision=0)
        self.assertEqual(tree_bytes(attempt), before)

        # Submit won the race: the restart sees the terminal state, never a
        # second action, and nothing else is written. The terminal state is
        # reported even when the caller's revision is also stale.
        submitted = self.service.submit(state.attempt_id).state
        final = tree_bytes(attempt)
        with self.assertRaisesRegex(IllegalLifecycleError, "submitted state"):
            self.service.restart(
                state.attempt_id, operation_id=str(uuid4()), expected_revision=0
            )
        with self.assertRaisesRegex(IllegalLifecycleError, "submitted state"):
            self.service.restart(
                state.attempt_id,
                operation_id=str(uuid4()),
                expected_revision=submitted.revision,
            )
        self.assertEqual(tree_bytes(attempt), final)
        self.assertEqual(len(self.scorer.calls), 1)

    def test_retry_after_a_failed_response_replays_the_committed_operation(self) -> None:
        state = self.service.start(FILE_STORAGE_METADATA)
        operation = str(uuid4())
        self.clock.value = LEGACY_START + timedelta(minutes=1)
        self.use_filesystem(FailOnceFilesystem("replace", "active.json", "attempts"))

        with self.assertRaises(RestartRecoveryPendingError) as pending:
            self.service.restart(state.attempt_id, operation_id=operation, expected_revision=0)
        self.assertEqual(pending.exception.code, "recovery_pending")

        self.use_filesystem(LocalFilesystem())
        self.clock.value = LEGACY_START + timedelta(minutes=30)
        retried = self.service.restart(
            state.attempt_id, operation_id=operation, expected_revision=0
        )

        self.assertTrue(retried.replayed)
        replacements = [
            child.name
            for child in self.attempts.iterdir()
            if child.is_dir() and not child.name.startswith(".") and child.name != state.attempt_id
        ]
        self.assertEqual(replacements, [retried.replacement_attempt_id])
        self.assertEqual(self.pointer(), retried.replacement_attempt_id)
        replacement = self.manager.persistence.read_session(self.attempt(retried.replacement_attempt_id))
        self.assertEqual(replacement.started_at, LEGACY_START + timedelta(minutes=1))


class SelectionPolicyTests(ActionsTestCase):
    def test_plain_start_never_displaces_a_live_selected_attempt(self) -> None:
        application = self.application()
        first = application.start(assessment="file_storage", mode="full", drill_duration_seconds=None)
        before = tree_bytes(self.attempts)

        with self.assertRaises(LiveSelectionError) as refused:
            application.start(assessment="file_storage", mode="drill", drill_duration_seconds=60)
        self.assertEqual(refused.exception.code, "live_selection")
        self.assertIn(first.attempt_id, refused.exception.message)
        self.assertEqual(tree_bytes(self.attempts), before)
        self.assertEqual(self.pointer(), first.attempt_id)

        # Ending the live attempt is one explicit resolution; restarting is the other.
        ended = application.abandon(attempt_id=None, expected_revision=0)
        self.assertIsInstance(ended, AbandonResult)
        second = application.start(assessment="file_storage", mode="drill", drill_duration_seconds=60)
        self.assertEqual(self.pointer(), second.attempt_id)
        restarted = application.restart(
            attempt_id=None, operation_id=str(uuid4()), expected_revision=0
        )
        self.assertEqual(self.pointer(), restarted.replacement_attempt_id)
        self.assertEqual(restarted.replacement_state.profile, second.profile)
        self.assertTrue((self.attempt(restarted.replacement_attempt_id) / "STATUS.md").is_file())
        self.assertIn(
            "abandoned", (self.attempt(second.attempt_id) / "STATUS.md").read_text("utf-8")
        )

    def test_uninstalled_content_does_not_trap_the_user_in_a_live_attempt(self) -> None:
        old = self.application().start(assessment="file_storage", mode="full", drill_duration_seconds=None)
        upgraded = self.application(cache=self.upgraded_cache())

        # The old attempt is still live, so a plain start is still refused for
        # the right reason, and the resolution it names works.
        with self.assertRaises(LiveSelectionError):
            upgraded.start(assessment="file_storage", mode="full", drill_duration_seconds=None)
        ended = upgraded.abandon(attempt_id=old.attempt_id, expected_revision=0)
        self.assertEqual(ended.state.status, ABANDONED)
        fresh = upgraded.start(assessment="file_storage", mode="full", drill_duration_seconds=None)
        self.assertEqual(fresh.assessment.content_version, "upstream-1111111")

    def test_source_reset_is_not_a_restart(self) -> None:
        application = self.application()
        state = application.start(assessment="file_storage", mode="full", drill_duration_seconds=None)
        document = application.source(attempt_id=state.attempt_id)
        saved = application.save_source(
            attempt_id=state.attempt_id, content="print('edited')\n", if_match=document.etag
        )

        reset = application.reset_source(attempt_id=state.attempt_id, if_match=saved.etag)

        self.assertEqual(reset.attempt_id, state.attempt_id)
        self.assertEqual(reset.content, document.content)
        after = application.status(attempt_id=state.attempt_id)
        self.assertEqual((after.attempt_id, after.deadline_at, after.status), (state.attempt_id, state.deadline_at, ACTIVE))
        self.assertEqual(self.pointer(), state.attempt_id)
        self.assertEqual(
            [child.name for child in self.attempts.iterdir() if child.is_dir() and not child.name.startswith(".")],
            [state.attempt_id],
        )

    def test_explicit_resume_repairs_a_corrupt_pointer_but_not_live_work(self) -> None:
        first = self.service.start(FILE_STORAGE_METADATA)
        legacy = session(str(uuid4()))
        self.manager.create_attempt(legacy)  # pointer now names the legacy attempt
        (self.attempts / "active.json").write_text("{bad", encoding="utf-8")

        resumed = self.service.resume(first.attempt_id)

        self.assertEqual(resumed, first)
        self.assertEqual(self.pointer(), first.attempt_id)
        with self.assertRaises(LiveSelectionError):
            self.service.resume(legacy.attempt_id)
        self.assertEqual(self.pointer(), first.attempt_id)


class RecordingApplication:
    def __init__(self, result: object | Exception = None) -> None:
        self.result = {"ok": True} if result is None else result
        self.calls: list[tuple[str, dict[str, object]]] = []

    def __getattr__(self, command: str):
        def adapter(**arguments: object) -> object:
            self.calls.append((command, arguments))
            if isinstance(self.result, Exception):
                raise self.result
            return self.result

        return adapter


class CliActionTests(unittest.TestCase):
    def execute(self, arguments: list[str], application: RecordingApplication | None = None):
        output = io.StringIO()
        application = application or RecordingApplication()
        code = cli.execute(
            [*arguments, "--json"],
            application_factory=lambda _root: application,
            output=output,
        )
        return code, json.loads(output.getvalue()), application

    def test_abandon_and_restart_dispatch_validated_arguments(self) -> None:
        attempt = str(uuid4())
        operation = str(uuid4())

        code, _document, application = self.execute(
            ["abandon", "--attempt", attempt, "--expected-revision", "2"]
        )
        self.assertEqual(code, 0)
        self.assertEqual(
            application.calls,
            [("abandon", {"attempt_id": attempt, "expected_revision": 2})],
        )

        code, _document, application = self.execute(
            [
                "restart",
                "--expected-revision",
                "0",
                "--operation-id",
                operation,
                "--mode",
                "drill",
                "--drill-duration-seconds",
                "600",
            ]
        )
        self.assertEqual(code, 0)
        self.assertEqual(
            application.calls,
            [
                (
                    "restart",
                    {
                        "attempt_id": None,
                        "operation_id": operation,
                        "expected_revision": 0,
                        "mode": "drill",
                        "drill_duration_seconds": 600,
                    },
                )
            ],
        )

        # Without an operation ID the CLI mints a canonical one so a retry can reuse it.
        code, _document, application = self.execute(["restart", "--expected-revision", "1"])
        self.assertEqual(code, 0)
        minted = application.calls[0][1]["operation_id"]
        self.assertEqual(str(UUID(minted)), minted)
        self.assertIsNone(application.calls[0][1]["mode"])

        invalid = {
            "missing revision": ["abandon"],
            "negative revision": ["abandon", "--expected-revision", "-1"],
            "non-integer revision": ["restart", "--expected-revision", "one"],
            "bad operation id": ["restart", "--expected-revision", "0", "--operation-id", "nope"],
            "uppercase operation id": [
                "restart", "--expected-revision", "0", "--operation-id", operation.upper()
            ],
            "duration without drill": [
                "restart", "--expected-revision", "0", "--drill-duration-seconds", "60"
            ],
            "zero duration": [
                "restart", "--expected-revision", "0", "--mode", "drill",
                "--drill-duration-seconds", "0",
            ],
        }
        for label, arguments in invalid.items():
            with self.subTest(case=label):
                code, document, application = self.execute(arguments)
                self.assertEqual(code, 2)
                self.assertEqual(document["error"]["code"], "invalid_input")
                self.assertEqual(application.calls, [])

    def test_results_and_specific_error_codes_reach_the_envelope(self) -> None:
        started = LEGACY_START
        state = SessionStateV2(
            schema_version=SESSION_SCHEMA_VERSION_V2,
            attempt_id=str(uuid4()),
            assessment=make_cache(Path(tempfile.mkdtemp())).pinned_assessment(FILE_STORAGE),
            profile=ModeProfile(DRILL_MODE, DRILL_PROFILE, DRILL_DEFAULT_DURATION_SECONDS),
            started_at=started,
            deadline_at=started + timedelta(seconds=DRILL_DEFAULT_DURATION_SECONDS),
            status=ACTIVE,
            revision=0,
        )
        restart = RestartResult(
            operation_id=str(uuid4()),
            old_attempt_id=str(uuid4()),
            replacement_attempt_id=state.attempt_id,
            committed_at=started,
            replayed=False,
            replacement_state=state,
        )
        code, document, _application = self.execute(
            ["restart", "--expected-revision", "0"], RecordingApplication(restart)
        )
        self.assertEqual(code, 0)
        self.assertEqual(document["result"]["session"], state.to_dict())
        self.assertEqual(document["result"]["replayed"], False)
        self.assertIsNone(document["result"]["abandoned_session"])
        self.assertEqual(document["result"]["committed_at"], started.isoformat())

        code, document, _application = self.execute(
            ["abandon", "--expected-revision", "0"],
            RecordingApplication(AbandonResult(state=state, newly_abandoned=True)),
        )
        self.assertEqual(code, 0)
        self.assertEqual(document["result"], {"session": state.to_dict(), "newly_abandoned": True})

        errors = {
            StaleRevisionError("stale"): (4, "stale_revision"),
            RestartConflictError("conflict"): (4, "operation_conflict"),
            LiveSelectionError("live"): (4, "live_selection"),
            RestartRecoveryPendingError("pending"): (3, "recovery_pending"),
            IllegalLifecycleError("illegal"): (4, "illegal_lifecycle"),
        }
        for error, (exit_code, code_name) in errors.items():
            with self.subTest(error=type(error).__name__):
                code, document, _application = self.execute(
                    ["restart", "--expected-revision", "0"], RecordingApplication(error)
                )
                self.assertEqual((code, document["error"]["code"]), (exit_code, code_name))
                self.assertEqual(document["error"]["message"], error.message)


_RESTART_SCRIPT = """
import hashlib, json, sys
from pathlib import Path
from codesignal_practice_simulator.application import RuntimeApplication
from codesignal_practice_simulator.errors import DomainError
from codesignal_practice_simulator.workspace import ValidatedFixtureCache

cache_root, workspace, attempt, operation, revision = sys.argv[1:6]
root = Path(cache_root)
hashes = {
    path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in root.rglob("*")
    if path.is_file()
}
application = RuntimeApplication(
    Path(workspace),
    cache=ValidatedFixtureCache(root, hashes, content_version="upstream-0000000"),
)
try:
    result = application.restart(
        attempt_id=attempt, operation_id=operation, expected_revision=int(revision)
    )
    print(json.dumps({"ok": True, "replacement": result.replacement_attempt_id, "replayed": result.replayed}))
except DomainError as error:
    print(json.dumps({"ok": False, "code": error.code or type(error).__name__}))
"""


class TwoProcessTests(ActionsTestCase):
    def run_restart(self, attempt_id: str, operation: str) -> subprocess.Popen[str]:
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(PROJECT / "src")
        return subprocess.Popen(
            [
                sys.executable,
                "-c",
                _RESTART_SCRIPT,
                str(self.cache.root),
                str(self.workspace_root),
                attempt_id,
                operation,
                "0",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )

    def test_restart_against_a_lock_held_by_another_process_is_a_bounded_busy_error(self) -> None:
        # A scorer in another process owns the attempt's flock; this exercises the
        # real cross-process contention path, not the in-process held-lock guard.
        state = self.service.start(FILE_STORAGE_METADATA)
        attempt = self.attempt(state.attempt_id)
        before = tree_bytes(attempt)
        locker = subprocess.Popen(
            [
                sys.executable,
                "-c",
                (
                    "import fcntl, sys, time; "
                    "handle = open(sys.argv[1], 'a+'); "
                    "fcntl.flock(handle, fcntl.LOCK_EX); "
                    "print('locked', flush=True); time.sleep(20)"
                ),
                str(attempt / ".session.lock"),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            assert locker.stdout is not None
            self.assertEqual(locker.stdout.readline().strip(), "locked")
            self.clock.value = LEGACY_START + timedelta(minutes=1)
            with self.assertRaisesRegex(LockUnavailableError, "busy"):
                self.service.restart(
                    state.attempt_id, operation_id=str(uuid4()), expected_revision=0
                )
            with self.assertRaisesRegex(LockUnavailableError, "busy"):
                self.service.abandon(state.attempt_id, expected_revision=0)
        finally:
            locker.terminate()
            locker.communicate(timeout=10)
        self.assertEqual(tree_bytes(attempt), before)
        self.assertEqual(self.pointer(), state.attempt_id)
        self.assertEqual(
            [child.name for child in self.attempts.iterdir() if child.is_dir() and not child.name.startswith(".")],
            [state.attempt_id],
        )

    def test_concurrent_restarts_with_one_operation_id_create_one_replacement(self) -> None:
        # Real clock: the subprocesses cannot see the fake one.
        application = RuntimeApplication(self.workspace_root, cache=self.cache)
        state = application.start(assessment="file_storage", mode="full", drill_duration_seconds=None)
        operation = str(uuid4())

        processes = [self.run_restart(state.attempt_id, operation) for _ in range(2)]
        outputs = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=60)
            self.assertEqual(process.returncode, 0, stderr)
            outputs.append(json.loads(stdout.strip().splitlines()[-1]))

        succeeded = [output for output in outputs if output["ok"]]
        failed = [output for output in outputs if not output["ok"]]
        self.assertGreaterEqual(len(succeeded), 1)
        for output in failed:
            # The loser of the lock race sees a bounded busy or stale error, never
            # a second replacement.
            self.assertIn(output["code"], {"illegal_lifecycle", "IllegalLifecycleError", "LockUnavailableError", "stale_revision"})
            retry = self.run_restart(state.attempt_id, operation)
            stdout, stderr = retry.communicate(timeout=60)
            self.assertEqual(retry.returncode, 0, stderr)
            replay = json.loads(stdout.strip().splitlines()[-1])
            self.assertTrue(replay["ok"], replay)
            self.assertTrue(replay["replayed"])
            succeeded.append(replay)

        replacement_ids = {output["replacement"] for output in succeeded}
        self.assertEqual(len(replacement_ids), 1)
        replacement_id = replacement_ids.pop()
        directories = [
            child.name
            for child in self.attempts.iterdir()
            if child.is_dir() and not child.name.startswith(".")
        ]
        self.assertEqual(sorted(directories), sorted([state.attempt_id, replacement_id]))
        self.assertEqual(self.pointer(), replacement_id)
        old = Persistence().read_session(self.attempt(state.attempt_id))
        self.assertEqual(old.status, ABANDONED)
        self.assertEqual(
            Persistence().read_session(self.attempt(replacement_id)).status, ACTIVE
        )


if __name__ == "__main__":
    unittest.main()
