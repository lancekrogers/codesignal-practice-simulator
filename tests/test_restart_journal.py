"""D001 restart transaction: write-ahead commit intent, roll-forward, replay."""

from __future__ import annotations

import json
import tempfile
import unittest
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from tests.workspace_test_support import (
    ValidatedFixtureCache,
    WorkspaceManager,
    make_cache,
    session,
    tree_snapshot,
)

from codesignal_practice_simulator.assessments import FILE_STORAGE
from codesignal_practice_simulator.attempt_reviews import AttemptReviewService
from codesignal_practice_simulator.errors import (
    IllegalLifecycleError,
    InvalidInputError,
    LockUnavailableError,
    RestartConflictError,
    RestartRecoveryPendingError,
    SessionCorruptError,
    StaleRevisionError,
)
from codesignal_practice_simulator.filesystem import LocalFilesystem
from codesignal_practice_simulator.lifecycle import LifecycleService
from codesignal_practice_simulator.models import (
    ABANDONED,
    ACTIVE,
    CONTENT_IDENTITY_PINNED,
    CONTENT_IDENTITY_UNAVAILABLE,
    DRILL_DEFAULT_DURATION_SECONDS,
    DRILL_MODE,
    DRILL_PROFILE,
    EVENT_SCHEMA_VERSION,
    EVENT_SCHEMA_VERSION_V2,
    FULL_DURATION_SECONDS,
    SESSION_SCHEMA_VERSION_V2,
    AbandonmentMetadata,
    AssessmentMetadata,
    LevelResult,
    ModeProfile,
    RestartCompletion,
    RestartJournal,
    RestartRequest,
    ScoreSummary,
    SessionRecord,
    SessionState,
    SessionStateV2,
    abandoned_record,
    adapt_session_record,
    parse_session_record,
)
from codesignal_practice_simulator.persistence import (
    RESTART_COMPLETION_DIRECTORY,
    RESTART_JOURNAL_DIRECTORY,
    Persistence,
)
from codesignal_practice_simulator.rendering import load_attempt_context, render_markdown
from codesignal_practice_simulator.workspace import CREATION_MARKER


LEGACY_START = datetime(2026, 9, 8, 19, tzinfo=timezone.utc)
FILE_STORAGE_METADATA = AssessmentMetadata("file_storage", "File Storage")
Predicate = Callable[[Path, Path | None], bool]


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


class InjectedFilesystem(LocalFilesystem):
    """Fail the durable operations a predicate selects.

    ``once`` fails only the first match; ``after`` performs the operation and
    then reports failure, the durable-but-reported-failed case every boundary
    must tolerate.
    """

    def __init__(
        self,
        operation: str | tuple[str, ...],
        predicate: Predicate,
        *,
        once: bool = True,
        after: bool = False,
    ) -> None:
        self.operations = (operation,) if isinstance(operation, str) else operation
        self.predicate = predicate
        self.once = once
        self.after = after
        self.failures = 0

    def _maybe_fail(
        self, operation: str, path: Path, destination: Path | None, perform
    ) -> None:
        if operation not in self.operations or (self.once and self.failures):
            perform()
            return
        if not self.predicate(path, destination):
            perform()
            return
        self.failures += 1
        if self.after:
            perform()
        raise OSError(f"injected {operation} failure")

    def write_bytes(self, path: Path, data: bytes) -> None:
        self._maybe_fail("write_bytes", path, None, lambda: super(InjectedFilesystem, self).write_bytes(path, data))

    def append_bytes(self, path: Path, data: bytes) -> None:
        self._maybe_fail("append_bytes", path, None, lambda: super(InjectedFilesystem, self).append_bytes(path, data))

    def flush_directory(self, path: Path) -> None:
        self._maybe_fail("flush_directory", path, None, lambda: super(InjectedFilesystem, self).flush_directory(path))

    def replace(self, source: Path, destination: Path) -> None:
        self._maybe_fail("replace", source, destination, lambda: super(InjectedFilesystem, self).replace(source, destination))

    def unlink(self, path: Path) -> None:
        self._maybe_fail("unlink", path, None, lambda: super(InjectedFilesystem, self).unlink(path))

    def copyfile(self, source: Path, destination: Path) -> None:
        self._maybe_fail("copyfile", source, destination, lambda: super(InjectedFilesystem, self).copyfile(source, destination))


def _same(left: Path, right: Path) -> bool:
    return left.resolve() == right.resolve()


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _events(attempt: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in (attempt / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]


class RestartTestCase(unittest.TestCase):
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
        self.now = LEGACY_START + timedelta(minutes=10)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    # -- fixtures ---------------------------------------------------------

    def use_filesystem(self, filesystem: LocalFilesystem) -> None:
        persistence = Persistence(filesystem)
        self.manager.filesystem = filesystem
        self.manager.persistence = persistence
        self.service.persistence = persistence

    def fresh_manager(self) -> WorkspaceManager:
        return WorkspaceManager(self.workspace_root, self.cache)

    def pinned_old(self, *, tested: bool = True) -> SessionRecord:
        state = self.service.start(FILE_STORAGE_METADATA)
        if tested:
            state = self.service.test(state.attempt_id)
        return state

    def legacy_old(self) -> SessionState:
        state = session(str(uuid4()))
        self.manager.create_attempt(state)
        return state

    def request_for(
        self,
        old: SessionRecord,
        *,
        operation_id: str | None = None,
        expected_revision: int | None = None,
        profile: ModeProfile | None = None,
    ) -> RestartRequest:
        return RestartRequest(
            operation_id=operation_id or str(uuid4()),
            old_attempt_id=old.attempt_id,
            expected_revision=old.revision if expected_revision is None else expected_revision,
            assessment=self.cache.pinned_assessment(FILE_STORAGE),
            profile=profile or old.profile,
        )

    def attempt(self, attempt_id: str) -> Path:
        return self.attempts / attempt_id

    def journal_files(self) -> list[Path]:
        directory = self.attempts / RESTART_JOURNAL_DIRECTORY
        return sorted(directory.iterdir()) if directory.exists() else []

    def completion_path(self, operation_id: str) -> Path:
        return self.attempts / RESTART_COMPLETION_DIRECTORY / f"{operation_id}.json"

    def pointer(self) -> str | None:
        pointer = self.fresh_manager().persistence.read_active_pointer(self.attempts)
        return None if pointer is None else pointer.attempt_id

    def replacement_directories(self, old_id: str) -> list[Path]:
        found = []
        for child in self.attempts.iterdir():
            if not child.is_dir() or child.name.startswith("."):
                continue
            events = _events(child) if (child / "events.jsonl").exists() else []
            if any(
                event["name"] == "started"
                and event["arguments"].get("replaces_attempt_id") == old_id
                for event in events
            ):
                found.append(child)
        return found

    # -- assertions -------------------------------------------------------

    def assert_restart_complete(
        self,
        old: SessionRecord,
        request: RestartRequest,
        replacement_id: str,
        *,
        old_source_before: bytes,
        committed_at: datetime | None = None,
    ) -> SessionStateV2:
        committed_at = committed_at or self.now
        persistence = self.fresh_manager().persistence
        old_dir = self.attempt(old.attempt_id)
        abandoned = persistence.read_session(old_dir)
        self.assertIsInstance(abandoned, SessionStateV2)
        self.assertEqual(abandoned.status, ABANDONED)
        self.assertEqual(abandoned.revision, old.revision + 1)
        self.assertEqual(abandoned.started_at, old.started_at)
        self.assertEqual(abandoned.deadline_at, old.deadline_at)
        self.assertEqual(abandoned.assessment, old.assessment)
        self.assertIsNone(abandoned.score)
        self.assertEqual(
            abandoned.abandonment,
            AbandonmentMetadata(committed_at, "restarted", old.score),
        )
        self.assertEqual((old_dir / "simulation.py").read_bytes(), old_source_before)
        old_events = _events(old_dir)
        abandoned_events = [
            event for event in old_events if event["revision"] == abandoned.revision
        ]
        self.assertEqual(len(abandoned_events), 1)
        self.assertEqual(abandoned_events[0]["name"], "abandoned")
        self.assertEqual(abandoned_events[0]["schema_version"], EVENT_SCHEMA_VERSION_V2)
        self.assertEqual(
            abandoned_events[0]["arguments"],
            {
                "operation_id": request.operation_id,
                "replacement_attempt_id": replacement_id,
            },
        )

        replacement_dir = self.attempt(replacement_id)
        replacement = persistence.read_session(replacement_dir)
        self.assertIsInstance(replacement, SessionStateV2)
        self.assertEqual(replacement.status, ACTIVE)
        self.assertEqual(replacement.revision, 0)
        self.assertEqual(replacement.started_at, committed_at)
        self.assertEqual(
            replacement.deadline_at,
            committed_at + timedelta(seconds=request.profile.duration_seconds),
        )
        self.assertEqual(replacement.assessment, request.assessment)
        self.assertEqual(replacement.profile, request.profile)
        started = _events(replacement_dir)
        self.assertEqual(len(started), 1)
        self.assertEqual(started[0]["name"], "started")
        self.assertEqual(
            started[0]["arguments"],
            {
                "operation_id": request.operation_id,
                "replaces_attempt_id": old.attempt_id,
            },
        )
        self.assertFalse((replacement_dir / CREATION_MARKER).exists())
        self.assertEqual(
            [child for child in self.attempts.iterdir() if ".staging-" in child.name],
            [],
        )
        self.assertEqual(self.pointer(), replacement_id)
        self.assertEqual(self.journal_files(), [])
        completion = RestartCompletion.from_dict(
            _read_json(self.completion_path(request.operation_id))
        )
        self.assertEqual(completion.request, request)
        self.assertEqual(completion.replacement_attempt_id, replacement_id)
        self.assertEqual(
            [path.name for path in self.replacement_directories(old.attempt_id)],
            [replacement_id],
        )
        return replacement


class RestartHappyPathTests(RestartTestCase):
    def test_restart_abandons_the_old_attempt_and_selects_one_replacement(self) -> None:
        old = self.pinned_old()
        source_before = (self.attempt(old.attempt_id) / "simulation.py").read_bytes()
        request = self.request_for(old)

        result = self.manager.restart_attempt(request, now=self.now)

        self.assertFalse(result.replayed)
        self.assertEqual(result.old_attempt_id, old.attempt_id)
        self.assertEqual(result.committed_at, self.now)
        replacement = self.assert_restart_complete(
            old, request, result.replacement_attempt_id, old_source_before=source_before
        )
        self.assertEqual(result.replacement_state, replacement)
        self.assertEqual(
            result.abandoned_state,
            self.manager.persistence.read_session(self.attempt(old.attempt_id)),
        )
        self.assertEqual(result.abandoned_state.content_identity, CONTENT_IDENTITY_PINNED)
        # The old attempt is a terminal record that still renders and reviews.
        markdown = render_markdown(
            load_attempt_context(self.attempt(old.attempt_id), self.manager.persistence)
        )
        self.assertIn("Status: `abandoned`", markdown)
        self.assertIn("codesignal-sim status", markdown)
        self.assertNotIn("submit", markdown.split("## Next legal commands")[1])
        review = AttemptReviewService(self.attempts).get_review(old.attempt_id)
        self.assertEqual(review.status, ABANDONED)
        self.assertEqual(review.source_binding, "not_applicable")
        self.assertIsNone(review.score)
        with self.assertRaisesRegex(IllegalLifecycleError, "abandoned state"):
            self.service.submit(old.attempt_id)
        self.assertEqual(len(self.scorer.calls), 1)

    def test_restart_stages_through_the_verified_creation_path(self) -> None:
        old = self.pinned_old(tested=False)
        request = self.request_for(old)

        result = self.manager.restart_attempt(request, now=self.now)

        replacement = self.attempt(result.replacement_attempt_id)
        for name in ("level1.md", "simulation.py", "test_simulation.py"):
            self.assertEqual(
                replacement.joinpath(name).read_bytes(),
                self.attempt(old.attempt_id).joinpath(name).read_bytes(),
            )
        self.assertTrue((replacement / "AGENTS.md").is_file())
        self.assertTrue((replacement / ".candidate-initial.json").is_file())
        # The replacement is a normal live attempt for every lifecycle command.
        self.clock.value = self.now + timedelta(minutes=1)
        self.assertEqual(self.service.status().attempt_id, result.replacement_attempt_id)
        tested = self.service.test()
        self.assertEqual(tested.revision, 1)

    def test_legacy_v1_old_attempt_is_upgraded_only_as_an_explicit_legacy_identity(self) -> None:
        old = self.legacy_old()
        old_dir = self.attempt(old.attempt_id)
        source_before = (old_dir / "simulation.py").read_bytes()
        request = self.request_for(old)

        result = self.manager.restart_attempt(request, now=self.now)

        abandoned = self.assert_restart_complete(
            old, request, result.replacement_attempt_id, old_source_before=source_before
        )
        raw = _read_json(old_dir / "session.json")
        self.assertEqual(raw["schema_version"], SESSION_SCHEMA_VERSION_V2)
        self.assertEqual(raw["content_identity"], CONTENT_IDENTITY_UNAVAILABLE)
        self.assertEqual(
            set(raw["assessment"]), {"assessment_id", "display_name", "level_count"}
        )
        self.assertNotIn("content_version", (old_dir / "session.json").read_text("utf-8"))
        upgraded = parse_session_record(raw)
        self.assertIsInstance(upgraded.assessment, AssessmentMetadata)
        self.assertFalse(adapt_session_record(upgraded).content_identity_available)
        self.assertEqual(
            [(event["schema_version"], event["name"]) for event in _events(old_dir)],
            [(EVENT_SCHEMA_VERSION, "started"), (EVENT_SCHEMA_VERSION_V2, "abandoned")],
        )
        # The legacy adapter still resolves its definition; nothing pins content.
        self.manager.definition_for_persisted_session(upgraded)
        review = AttemptReviewService(self.attempts).get_review(old.attempt_id)
        self.assertEqual(review.assessment.content_identity, CONTENT_IDENTITY_UNAVAILABLE)
        self.assertIn("content_identity_unavailable", review.issues)
        # The replacement itself is a normal pinned attempt.
        self.assertEqual(abandoned.content_identity, CONTENT_IDENTITY_PINNED)

    def test_replacement_timer_starts_at_the_committed_timestamp_not_recovery(self) -> None:
        old = self.pinned_old()
        request = self.request_for(old)
        self.use_filesystem(
            InjectedFilesystem("replace", lambda _s, d: d is not None and d.name == "active.json")
        )
        with self.assertRaises(RestartRecoveryPendingError):
            self.manager.restart_attempt(request, now=self.now)

        # Recovery happens much later; the journal's committed timestamp wins.
        self.clock.value = self.now + timedelta(hours=3)
        recovered = self.fresh_manager().recover_restarts()

        self.assertEqual(recovered, [request.operation_id])
        replacement = self.fresh_manager().persistence.read_session(
            self.attempt(self.replacement_directories(old.attempt_id)[0].name)
        )
        self.assertEqual(replacement.started_at, self.now)
        self.assertEqual(
            replacement.deadline_at, self.now + timedelta(seconds=FULL_DURATION_SECONDS)
        )


class PreCommitFailureTests(RestartTestCase):
    def snapshot(self) -> dict[str, object]:
        # An empty journal directory left by a failed commit write is not state.
        return {
            key: value
            for key, value in tree_snapshot(self.attempts).items()
            if key != RESTART_JOURNAL_DIRECTORY
        }

    def assert_untouched(
        self, before: dict[str, object], old: SessionRecord, request: RestartRequest
    ) -> None:
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.pointer(), old.attempt_id)
        self.assertEqual(self.journal_files(), [])
        self.assertFalse(self.completion_path(request.operation_id).exists())
        state = self.fresh_manager().persistence.read_session(self.attempt(old.attempt_id))
        self.assertEqual(state.status, ACTIVE)
        self.assertEqual(state, old)

    def test_staging_failures_leave_the_old_attempt_active_and_selected(self) -> None:
        old = self.pinned_old()
        before = self.snapshot()
        cases = {
            "input copy": InjectedFilesystem(
                "copyfile", lambda _s, d: d is not None and d.name == "simulation.py"
            ),
            "staged session": InjectedFilesystem(
                "replace",
                lambda _s, d: d is not None and d.name == "session.json" and ".staging-" in d.parent.name,
            ),
            "journal not durable": InjectedFilesystem(
                "replace", lambda _s, d: d is not None and d.parent.name == RESTART_JOURNAL_DIRECTORY
            ),
        }
        for label, filesystem in cases.items():
            with self.subTest(boundary=label):
                self.use_filesystem(filesystem)
                request = self.request_for(old)
                with self.assertRaisesRegex(OSError, "injected"):
                    self.manager.restart_attempt(request, now=self.now)
                self.assertEqual(filesystem.failures, 1)
                self.assert_untouched(before, old, request)

    def test_journal_durable_but_reported_failed_completes_the_operation(self) -> None:
        old = self.pinned_old()
        source_before = (self.attempt(old.attempt_id) / "simulation.py").read_bytes()
        request = self.request_for(old)
        self.use_filesystem(
            InjectedFilesystem(
                "flush_directory",
                lambda p, _d: p.name == RESTART_JOURNAL_DIRECTORY,
                after=True,
            )
        )

        result = self.manager.restart_attempt(request, now=self.now)

        self.assertFalse(result.replayed)
        self.assert_restart_complete(
            old, request, result.replacement_attempt_id, old_source_before=source_before
        )

    def test_validation_failures_write_nothing(self) -> None:
        old = self.pinned_old()
        before = tree_snapshot(self.attempts)
        drill = ModeProfile(DRILL_MODE, DRILL_PROFILE, DRILL_DEFAULT_DURATION_SECONDS)
        cases: dict[str, tuple[type[Exception], str, RestartRequest, datetime]] = {
            "stale revision": (
                StaleRevisionError,
                "expected revision 0, current 1",
                self.request_for(old, expected_revision=0),
                self.now,
            ),
            "at deadline": (
                IllegalLifecycleError,
                "at or after its deadline",
                self.request_for(old),
                old.deadline_at,
            ),
            "unknown target content": (
                InvalidInputError,
                "does not match the installed",
                replace(
                    self.request_for(old),
                    assessment=replace(
                        self.cache.pinned_assessment(FILE_STORAGE),
                        content_version="upstream-9999999",
                    ),
                ),
                self.now,
            ),
        }
        for label, (error, message, request, now) in cases.items():
            with self.subTest(case=label):
                with self.assertRaisesRegex(error, message):
                    self.manager.restart_attempt(request, now=now)
                self.assertEqual(tree_snapshot(self.attempts), before)
        # A drill restart of a full attempt is a legal target change, not a conflict.
        result = self.manager.restart_attempt(self.request_for(old, profile=drill), now=self.now)
        self.assertEqual(
            self.fresh_manager().persistence.read_session(
                self.attempt(result.replacement_attempt_id)
            ).profile,
            drill,
        )

    def test_terminal_old_attempts_cannot_be_restarted(self) -> None:
        old = self.pinned_old()
        submitted = self.service.submit(old.attempt_id).state
        before = tree_snapshot(self.attempts)

        with self.assertRaisesRegex(IllegalLifecycleError, "submitted state"):
            self.manager.restart_attempt(self.request_for(submitted), now=self.now)

        self.assertEqual(tree_snapshot(self.attempts), before)
        self.assertEqual(len(self.scorer.calls), 2)

    def test_restart_while_the_old_attempt_is_locked_is_a_bounded_busy_error(self) -> None:
        old = self.pinned_old()
        before = tree_snapshot(self.attempts)

        with self.manager.persistence.attempt_lock(self.attempt(old.attempt_id)):
            with self.assertRaisesRegex(LockUnavailableError, "busy"):
                self.fresh_manager().restart_attempt(self.request_for(old), now=self.now)

        self.assertEqual(tree_snapshot(self.attempts), before)


class PostCommitRecoveryTests(RestartTestCase):
    def boundaries(self, old_id: str) -> dict[str, InjectedFilesystem]:
        def old_session(_s: Path, d: Path | None) -> bool:
            return d is not None and d.name == "session.json" and d.parent.name == old_id

        def old_events(p: Path, d: Path | None) -> bool:
            target = d if d is not None else p
            return target.name == "events.jsonl" and target.parent.name == old_id

        def publish(s: Path, d: Path | None) -> bool:
            return ".staging-" in s.name and d is not None and _same(d.parent, self.attempts)

        def pointer(_s: Path, d: Path | None) -> bool:
            return d is not None and d.name == "active.json"

        def completion(_s: Path, d: Path | None) -> bool:
            return d is not None and d.parent.name == RESTART_COMPLETION_DIRECTORY

        def journal(p: Path, _d: Path | None) -> bool:
            return p.parent.name == RESTART_JOURNAL_DIRECTORY

        return {
            "old session replace": InjectedFilesystem("replace", old_session),
            "old session replaced then reported": InjectedFilesystem(
                "replace", old_session, after=True
            ),
            # An append that reports failure is retried as a full rewrite, so
            # the event log has to stay unavailable for the failure to surface.
            "old event unavailable": InjectedFilesystem(
                ("append_bytes", "replace"), old_events, once=False
            ),
            "replacement publish": InjectedFilesystem("replace", publish),
            "replacement published then reported": InjectedFilesystem(
                "replace", publish, after=True
            ),
            "pointer replace": InjectedFilesystem("replace", pointer),
            "pointer replaced then reported": InjectedFilesystem(
                "replace", pointer, after=True
            ),
            "pointer flush": InjectedFilesystem(
                "flush_directory", lambda p, _d: _same(p, self.attempts), after=True
            ),
            "completion write": InjectedFilesystem("replace", completion),
            "completion written then reported": InjectedFilesystem(
                "replace", completion, after=True
            ),
            "journal prune": InjectedFilesystem("unlink", journal),
        }

    def test_every_post_commit_boundary_rolls_forward_the_same_replacement(self) -> None:
        for legacy in (False, True):
            for label, filesystem in self.boundaries("placeholder").items():
                with self.subTest(boundary=label, legacy=legacy):
                    self.use_filesystem(LocalFilesystem())
                    old = self.legacy_old() if legacy else self.pinned_old()
                    filesystem = self.boundaries(old.attempt_id)[label]
                    self._assert_rolls_forward(old, filesystem)

    def _assert_rolls_forward(
        self, old: SessionRecord, filesystem: InjectedFilesystem
    ) -> None:
        old_dir = self.attempt(old.attempt_id)
        source_before = (old_dir / "simulation.py").read_bytes()
        request = self.request_for(old)
        self.use_filesystem(filesystem)

        with self.assertRaisesRegex(RestartRecoveryPendingError, "recovery is pending"):
            self.manager.restart_attempt(request, now=self.now)

        self.assertGreaterEqual(filesystem.failures, 1)
        journals = self.journal_files()
        self.assertEqual([path.name for path in journals], [f"{request.operation_id}.json"])
        journal = RestartJournal.from_dict(_read_json(journals[0]))
        self.assertEqual((old_dir / "simulation.py").read_bytes(), source_before)
        self.assertIn(
            self.fresh_manager().persistence.read_session(old_dir),
            (journal.old_prior_state, journal.old_final_state),
        )

        self.use_filesystem(LocalFilesystem())
        recovered = self.fresh_manager().recover_restarts()

        self.assertEqual(recovered, [request.operation_id])
        self.assert_restart_complete(
            old,
            request,
            journal.replacement_state.attempt_id,
            old_source_before=source_before,
        )
        # Recovery is idempotent and a repeat request replays the receipt.
        self.assertEqual(self.fresh_manager().recover_restarts(), [])
        replay = self.fresh_manager().restart_attempt(request, now=self.now + timedelta(hours=1))
        self.assertTrue(replay.replayed)
        self.assertEqual(replay.replacement_attempt_id, journal.replacement_state.attempt_id)

    def test_pending_journals_are_discovered_by_every_selection_mutation(self) -> None:
        entries: dict[str, Callable[[RestartRequest, RestartJournal], None]] = {
            "reconcile": lambda _r, _j: self.fresh_manager().reconcile(),
            "create attempt": lambda _r, _j: self.fresh_manager().create_attempt(
                session(str(uuid4()))
            ),
            "implicit status": lambda _r, _j: LifecycleService(
                self.fresh_manager(), self.clock, self.scorer
            ).status(),
            "explicit resolve": lambda _r, j: self.fresh_manager().resolve_attempt(
                j.replacement_state.attempt_id
            ),
        }
        for label, entry in entries.items():
            with self.subTest(entry=label):
                self.use_filesystem(LocalFilesystem())
                self.clock.value = LEGACY_START
                old = self.pinned_old()
                source_before = (self.attempt(old.attempt_id) / "simulation.py").read_bytes()
                request = self.request_for(old)
                # Crash after the replacement is published but before it is selected:
                # the marker scan must not treat it as an abandoned creation.
                self.use_filesystem(
                    InjectedFilesystem(
                        "replace",
                        lambda _s, d: d is not None and d.name == "active.json",
                    )
                )
                with self.assertRaises(RestartRecoveryPendingError):
                    self.manager.restart_attempt(request, now=self.now)
                journal = RestartJournal.from_dict(_read_json(self.journal_files()[0]))
                self.assertTrue(
                    (self.attempt(journal.replacement_state.attempt_id) / CREATION_MARKER).is_file()
                )
                self.use_filesystem(LocalFilesystem())
                self.clock.value = self.now + timedelta(minutes=1)

                entry(request, journal)

                self.assertEqual(self.journal_files(), [])
                self.assertTrue(self.attempt(journal.replacement_state.attempt_id).is_dir())
                if label == "create attempt":
                    self.assertNotEqual(self.pointer(), journal.replacement_state.attempt_id)
                    self.assertTrue(self.completion_path(request.operation_id).is_file())
                else:
                    self.assert_restart_complete(
                        old,
                        request,
                        journal.replacement_state.attempt_id,
                        old_source_before=source_before,
                    )

    def test_receipt_written_but_journal_left_is_pruned_without_state_checks(self) -> None:
        old = self.pinned_old()
        request = self.request_for(old)
        self.use_filesystem(
            InjectedFilesystem("unlink", lambda p, _d: p.parent.name == RESTART_JOURNAL_DIRECTORY)
        )
        with self.assertRaises(RestartRecoveryPendingError):
            self.manager.restart_attempt(request, now=self.now)
        journal = RestartJournal.from_dict(_read_json(self.journal_files()[0]))
        replacement = self.attempt(journal.replacement_state.attempt_id)
        # The replacement may legitimately move on once its receipt is durable.
        self.use_filesystem(LocalFilesystem())
        self.assertEqual(self.pointer(), replacement.name)

        self.assertEqual(self.fresh_manager().recover_restarts(), [request.operation_id])

        self.assertEqual(self.journal_files(), [])
        self.assertFalse((replacement / CREATION_MARKER).exists())


class ReplayAndConflictTests(RestartTestCase):
    def test_identical_repeat_returns_the_original_replacement_without_reselecting(self) -> None:
        old = self.pinned_old()
        request = self.request_for(old)
        first = self.manager.restart_attempt(request, now=self.now)
        before = tree_snapshot(self.attempts)

        repeat = self.manager.restart_attempt(request, now=self.now + timedelta(minutes=5))

        self.assertTrue(repeat.replayed)
        self.assertEqual(repeat.replacement_attempt_id, first.replacement_attempt_id)
        self.assertEqual(repeat.committed_at, self.now)
        self.assertIsNone(repeat.replacement_state)
        self.assertEqual(tree_snapshot(self.attempts), before)

        # Another attempt is selected afterwards; replay leaves that selection alone.
        other = session(str(uuid4()))
        self.manager.create_attempt(other)
        self.assertEqual(self.pointer(), other.attempt_id)
        self.assertEqual(
            self.manager.restart_attempt(request, now=self.now).replacement_attempt_id,
            first.replacement_attempt_id,
        )
        self.assertEqual(self.pointer(), other.attempt_id)

    def test_replay_after_the_replacement_was_submitted_changes_nothing(self) -> None:
        old = self.pinned_old()
        request = self.request_for(old)
        first = self.manager.restart_attempt(request, now=self.now)
        self.clock.value = self.now + timedelta(minutes=2)
        submitted = self.service.submit(first.replacement_attempt_id)
        calls = len(self.scorer.calls)
        before = tree_snapshot(self.attempts)

        repeat = self.manager.restart_attempt(request, now=self.clock.value)

        self.assertTrue(repeat.replayed)
        self.assertEqual(repeat.replacement_attempt_id, first.replacement_attempt_id)
        self.assertEqual(tree_snapshot(self.attempts), before)
        self.assertEqual(len(self.scorer.calls), calls)
        self.assertEqual(
            self.service.submit(first.replacement_attempt_id).state, submitted.state
        )

    def test_reused_operation_id_with_different_arguments_conflicts(self) -> None:
        old = self.pinned_old()
        request = self.request_for(old)
        first = self.manager.restart_attempt(request, now=self.now)
        before = tree_snapshot(self.attempts)
        drill = ModeProfile(DRILL_MODE, DRILL_PROFILE, DRILL_DEFAULT_DURATION_SECONDS)
        changed = {
            "profile": replace(request, profile=drill),
            "revision": replace(request, expected_revision=request.expected_revision + 1),
            "old attempt": replace(request, old_attempt_id=first.replacement_attempt_id),
            "content version": replace(
                request,
                assessment=replace(request.assessment, content_version="upstream-1111111"),
            ),
        }
        for label, conflicting in changed.items():
            with self.subTest(changed=label):
                with self.assertRaisesRegex(RestartConflictError, "different arguments"):
                    self.manager.restart_attempt(conflicting, now=self.now)
                self.assertEqual(tree_snapshot(self.attempts), before)
        self.assertEqual(
            [path.name for path in self.replacement_directories(old.attempt_id)],
            [first.replacement_attempt_id],
        )

    def test_changed_arguments_against_a_pending_journal_recover_then_conflict(self) -> None:
        old = self.pinned_old()
        request = self.request_for(old)
        self.use_filesystem(
            InjectedFilesystem("replace", lambda _s, d: d is not None and d.name == "active.json")
        )
        with self.assertRaises(RestartRecoveryPendingError):
            self.manager.restart_attempt(request, now=self.now)
        self.use_filesystem(LocalFilesystem())
        drill = ModeProfile(DRILL_MODE, DRILL_PROFILE, DRILL_DEFAULT_DURATION_SECONDS)

        with self.assertRaises(RestartConflictError):
            self.manager.restart_attempt(replace(request, profile=drill), now=self.now)

        self.assertEqual(self.journal_files(), [])
        self.assertEqual(len(self.replacement_directories(old.attempt_id)), 1)
        self.assertTrue(self.completion_path(request.operation_id).is_file())


class FailClosedTests(RestartTestCase):
    def pending_journal(self, old: SessionRecord, request: RestartRequest) -> RestartJournal:
        self.use_filesystem(
            InjectedFilesystem(
                "replace",
                lambda s, d: ".staging-" in s.name
                and d is not None
                and _same(d.parent, self.attempts),
            )
        )
        with self.assertRaises(RestartRecoveryPendingError):
            self.manager.restart_attempt(request, now=self.now)
        self.use_filesystem(LocalFilesystem())
        return RestartJournal.from_dict(_read_json(self.journal_files()[0]))

    def test_tampered_journal_fails_closed_and_preserves_evidence(self) -> None:
        old = self.pinned_old()
        request = self.request_for(old)
        self.pending_journal(old, request)
        path = self.journal_files()[0]
        raw = _read_json(path)
        raw["expected_pointer"] = None
        path.write_text(json.dumps(raw), encoding="utf-8")
        before = tree_snapshot(self.attempts)

        for entry in (
            self.fresh_manager().recover_restarts,
            self.fresh_manager().reconcile,
            lambda: self.fresh_manager().restart_attempt(request, now=self.now),
        ):
            with self.assertRaisesRegex(SessionCorruptError, "restart journal"):
                entry()
            self.assertEqual(tree_snapshot(self.attempts), before)

    def test_pointer_moved_by_something_else_fails_closed(self) -> None:
        third = session(str(uuid4()))
        self.manager.create_attempt(third)
        old = self.pinned_old()
        request = self.request_for(old)
        journal = self.pending_journal(old, request)
        Persistence().write_active_pointer(
            self.attempts, replace(Persistence().read_active_pointer(self.attempts), attempt_id=third.attempt_id)
        )
        before = tree_snapshot(self.attempts)

        with self.assertRaisesRegex(SessionCorruptError, "active pointer changed"):
            self.fresh_manager().recover_restarts()

        self.assertEqual(tree_snapshot(self.attempts), before)
        self.assertEqual(self.pointer(), third.attempt_id)
        # The staged replacement and the journal are kept for repair.
        self.assertTrue((self.attempts / journal.staging_name).is_dir())
        self.assertEqual(len(self.journal_files()), 1)

    def test_missing_replacement_fails_closed(self) -> None:
        old = self.pinned_old()
        request = self.request_for(old)
        journal = self.pending_journal(old, request)
        staging = self.attempts / journal.staging_name
        LocalFilesystem().remove_tree(staging)
        before = tree_snapshot(self.attempts)

        with self.assertRaisesRegex(SessionCorruptError, "replacement is missing"):
            self.fresh_manager().recover_restarts()

        self.assertEqual(tree_snapshot(self.attempts), before)

    def test_receipt_is_immutable(self) -> None:
        old = self.pinned_old()
        request = self.request_for(old)
        result = self.manager.restart_attempt(request, now=self.now)
        completion = RestartCompletion.from_dict(_read_json(self.completion_path(request.operation_id)))
        different = replace(completion, replacement_attempt_id=str(uuid4()))

        with self.assertRaisesRegex(SessionCorruptError, "does not match its journal"):
            self.manager.persistence.write_restart_completion_locked(self.attempts, different)

        self.assertEqual(
            RestartCompletion.from_dict(_read_json(self.completion_path(request.operation_id))),
            completion,
        )
        self.assertEqual(completion.replacement_attempt_id, result.replacement_attempt_id)


class LegacyIdentityModelTests(RestartTestCase):
    def test_unpinned_v2_records_exist_only_as_abandonment(self) -> None:
        legacy = session(str(uuid4()))
        abandoned = abandoned_record(legacy, ended_at=self.now, reason="restarted")

        self.assertEqual(abandoned.content_identity, CONTENT_IDENTITY_UNAVAILABLE)
        self.assertEqual(SessionStateV2.from_dict(abandoned.to_dict()), abandoned)
        self.assertEqual(parse_session_record(abandoned.to_dict()), abandoned)
        with self.assertRaisesRegex(InvalidInputError, "only record abandonment"):
            replace(abandoned, status=ACTIVE, abandonment=None)
        with self.assertRaisesRegex(InvalidInputError, "cannot abandon"):
            abandoned_record(abandoned, ended_at=self.now, reason="restarted")
        # The explicit label decides the shape and must agree with it.
        mislabeled = abandoned.to_dict()
        mislabeled["content_identity"] = CONTENT_IDENTITY_PINNED
        with self.assertRaises(InvalidInputError):
            SessionStateV2.from_dict(mislabeled)
        pinned = self.pinned_old(tested=False).to_dict()
        pinned["content_identity"] = CONTENT_IDENTITY_UNAVAILABLE
        with self.assertRaises(InvalidInputError):
            SessionStateV2.from_dict(pinned)
        unlabeled = abandoned.to_dict()
        del unlabeled["content_identity"]
        with self.assertRaisesRegex(InvalidInputError, "invalid field set"):
            SessionStateV2.from_dict(unlabeled)

    def test_practice_score_moves_out_of_the_submitted_score_field(self) -> None:
        old = self.pinned_old()
        self.assertIsNotNone(old.score)

        abandoned = abandoned_record(old, ended_at=self.now, reason="restarted")

        self.assertIsNone(abandoned.score)
        self.assertEqual(abandoned.abandonment.practice_score, old.score)
        self.assertEqual(adapt_session_record(abandoned).practice_score, old.score)
        self.assertIsNone(adapt_session_record(abandoned).score)

    def test_a_new_attempt_can_never_start_from_a_legacy_identity(self) -> None:
        abandoned = abandoned_record(
            session(str(uuid4())), ended_at=self.now, reason="restarted"
        )

        with self.assertRaisesRegex(InvalidInputError, "requires a pinned content identity"):
            self.manager.create_attempt(abandoned)

        self.assertFalse(self.attempts.exists())

    def test_journal_binds_every_record_to_the_committed_timestamp(self) -> None:
        old = self.pinned_old()
        request = self.request_for(old)
        journal = self.manager._plan_restart(  # noqa: SLF001 - model contract test
            self.attempts, request, old, self.now, "restarted"
        )
        self.assertEqual(RestartJournal.from_dict(journal.to_dict()), journal)

        cases: dict[str, Callable[[], RestartJournal]] = {
            "replacement start": lambda: replace(
                journal,
                replacement_state=replace(
                    journal.replacement_state,
                    started_at=self.now + timedelta(seconds=1),
                    deadline_at=journal.replacement_state.deadline_at + timedelta(seconds=1),
                ),
            ),
            "final not from prior": lambda: replace(
                journal,
                old_final_state=replace(
                    journal.old_final_state, revision=journal.old_final_state.revision + 1
                ),
            ),
            "wrong event name": lambda: replace(
                journal, old_event=replace(journal.old_event, name="expired")
            ),
            "staging name": lambda: replace(journal, staging_name=".other"),
            "pointer is replacement": lambda: replace(
                journal, expected_pointer=journal.replacement_state.attempt_id
            ),
        }
        for label, build in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(InvalidInputError):
                    build()
        tampered = journal.to_dict()
        tampered["committed_at"] = (self.now + timedelta(seconds=1)).isoformat()
        with self.assertRaisesRegex(InvalidInputError, "checksum"):
            RestartJournal.from_dict(tampered)


if __name__ == "__main__":
    unittest.main()
