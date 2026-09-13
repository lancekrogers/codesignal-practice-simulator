"""Bounded, read-only metadata history listing (D004)."""

from __future__ import annotations

import base64
import json
import os
import tempfile
import unittest
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

from codesignal_practice_simulator.application import RuntimeApplication
from codesignal_practice_simulator.attempt_history import (
    CONTENT_IDENTITY_UNAVAILABLE_ISSUE,
    DEFAULT_PAGE_SIZE,
    FINALIZATION_PENDING,
    MAX_PAGE_SIZE,
    RECORD_CORRUPT,
    RECORD_UNAVAILABLE,
    RESTART_JOURNALS_UNREADABLE,
    RESTART_PENDING,
    UNAVAILABLE_RECORDS_EXCLUDED_BY_FILTER,
    UNSAFE_ENTRIES_SKIPPED,
    AttemptHistoryService,
    HistoryCursor,
    HistoryFilters,
    HistoryPage,
)
from codesignal_practice_simulator.assessments import FILE_STORAGE
from codesignal_practice_simulator.errors import (
    InvalidInputError,
    RestartRecoveryPendingError,
    SessionCorruptError,
)
from codesignal_practice_simulator.filesystem import LocalFilesystem
from codesignal_practice_simulator.lifecycle import LifecycleService
from codesignal_practice_simulator.models import (
    ABANDONED,
    ACTIVE,
    CONTENT_IDENTITY_PINNED,
    CONTENT_IDENTITY_UNAVAILABLE,
    EXPIRED,
    SESSION_SCHEMA_VERSION,
    SESSION_SCHEMA_VERSION_V2,
    SUBMITTED,
    AssessmentMetadata,
    LevelResult,
    ModeProfile,
    RestartRequest,
    ScoreSummary,
)
from codesignal_practice_simulator.persistence import (
    ABANDONMENT_RECOVERY_FILENAME,
    RESTART_JOURNAL_DIRECTORY,
    SUBMISSION_RECOVERY_FILENAME,
    Persistence,
)


START = datetime(2026, 9, 8, 19, tzinfo=timezone.utc)
FILE_STORAGE_METADATA = AssessmentMetadata("file_storage", "File Storage")
FORBIDDEN_READS = ("simulation.py", "review.json", "events.jsonl", "test_simulation.py")


class FakeClock:
    def __init__(self, value: datetime = START) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


class RecordingScorer:
    def __call__(self, attempt: Path) -> ScoreSummary:
        return ScoreSummary(
            tuple(
                LevelResult(level, "passed" if level < 4 else "failed")
                for level in range(1, 5)
            )
        )


class ReadSpyFilesystem(LocalFilesystem):
    """Record every file the listing opens so forbidden reads are provable."""

    def __init__(self) -> None:
        self.reads: list[Path] = []

    def read_bytes(self, path: Path) -> bytes:
        self.reads.append(path)
        return super().read_bytes(path)

    def read_bytes_limited(self, path: Path, limit: int) -> bytes:
        self.reads.append(path)
        return super().read_bytes_limited(path, limit)


class PointerFailFilesystem(LocalFilesystem):
    def replace(self, source: Path, destination: Path) -> None:
        if destination.name == "active.json":
            raise OSError("injected pointer failure")
        super().replace(source, destination)


class HistoryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workspace_root = self.root / "workspace"
        self.workspace_root.mkdir()
        self.cache: ValidatedFixtureCache = make_cache(self.root)
        self.clock = FakeClock()
        self.manager = WorkspaceManager(self.workspace_root, self.cache)
        self.service = LifecycleService(self.manager, self.clock, RecordingScorer())
        self.attempts = self.workspace_root / "attempts"
        self.spy = ReadSpyFilesystem()
        self.history = AttemptHistoryService(
            self.attempts, persistence=Persistence(self.spy), clock=self.clock
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def start(self, minutes: int, **kwargs: object):
        self.clock.value = START + timedelta(minutes=minutes)
        return self.service.start(FILE_STORAGE_METADATA, **kwargs)

    def ids(self, page: HistoryPage) -> list[str]:
        return [item.attempt_id for item in page.items]

    def assert_read_only(self, before: dict[str, object]) -> None:
        self.assertEqual(tree_snapshot(self.attempts), before)
        forbidden = [path for path in self.spy.reads if path.name in FORBIDDEN_READS]
        self.assertEqual(forbidden, [])
        level_reads = [path for path in self.spy.reads if path.name.startswith("level")]
        self.assertEqual(level_reads, [])


class ListingTests(HistoryTestCase):
    def test_missing_or_empty_attempts_directory_lists_nothing_and_creates_nothing(self) -> None:
        page = self.history.list_attempts()
        self.assertEqual(page.items, ())
        self.assertIsNone(page.next_cursor)
        self.assertEqual(page.warnings, ())
        self.assertFalse(self.attempts.exists())

        self.attempts.mkdir()
        page = self.history.list_attempts(limit=5)
        self.assertEqual((page.items, page.limit), ((), 5))
        self.assertEqual(sorted(os.listdir(self.attempts)), [])

    def test_mixed_records_are_listed_from_metadata_newest_first(self) -> None:
        legacy = session(str(uuid4()))
        self.manager.create_attempt(legacy)  # started 19:00, v1
        submitted = self.start(1)  # 19:01, v2, will be submitted with a review
        self.clock.value = START + timedelta(minutes=2)
        self.service.test(submitted.attempt_id)
        self.service.submit(submitted.attempt_id)
        restarted = self.start(3)  # 19:03, abandoned by restart at 19:04
        self.service.test(restarted.attempt_id)
        self.clock.value = START + timedelta(minutes=4)
        result = self.service.restart(
            restarted.attempt_id, operation_id=str(uuid4()), expected_revision=1
        )
        overdue = self.start(5, mode="drill", drill_duration_seconds=60)  # 19:05
        self.clock.value = START + timedelta(minutes=10)
        before = tree_snapshot(self.attempts)
        pointer_before = (self.attempts / "active.json").read_bytes()

        page = self.history.list_attempts()

        self.assert_read_only(before)
        self.assertEqual((self.attempts / "active.json").read_bytes(), pointer_before)
        self.assertEqual(
            self.ids(page),
            [
                overdue.attempt_id,
                result.replacement_attempt_id,
                restarted.attempt_id,
                submitted.attempt_id,
                legacy.attempt_id,
            ],
        )
        by_id = {item.attempt_id: item for item in page.items}
        self.assertEqual(
            (by_id[overdue.attempt_id].status, by_id[overdue.attempt_id].persisted_status),
            (EXPIRED, ACTIVE),
        )
        self.assertEqual(by_id[result.replacement_attempt_id].status, ACTIVE)
        ended = by_id[restarted.attempt_id]
        self.assertEqual((ended.status, ended.review_available), (ABANDONED, False))
        self.assertEqual(ended.ended_at, START + timedelta(minutes=4))
        self.assertIsNone(ended.score)
        self.assertEqual(ended.practice_score.passed_levels, 3)
        done = by_id[submitted.attempt_id]
        self.assertEqual((done.status, done.review_available), (SUBMITTED, True))
        self.assertEqual(done.score.highest_contiguous_level, 3)
        self.assertEqual(done.assessment.content_identity, CONTENT_IDENTITY_PINNED)
        self.assertEqual(done.assessment.content_version, "upstream-0000000")
        self.assertEqual(done.issues, ())
        old = by_id[legacy.attempt_id]
        self.assertEqual(old.schema_version, SESSION_SCHEMA_VERSION)
        self.assertEqual(old.assessment.content_identity, CONTENT_IDENTITY_UNAVAILABLE)
        self.assertIsNone(old.assessment.content_version)
        self.assertEqual(old.issues, (CONTENT_IDENTITY_UNAVAILABLE_ISSUE,))
        for item in page.items:
            self.assertTrue(item.available)
            document = json.dumps(item.to_dict())
            self.assertNotIn(str(self.attempts), document)
            self.assertNotIn("simulate", document)
        # The persisted overdue record was displayed as expired, never written.
        self.assertEqual(
            json.loads((self.attempts / overdue.attempt_id / "session.json").read_text())["status"],
            ACTIVE,
        )
        json.dumps(page.to_dict())

    def test_pages_are_bounded_deterministic_and_bound_to_their_filters(self) -> None:
        started = [self.start(minute) for minute in range(7)]
        same_minute = [session(str(uuid4())) for _ in range(3)]
        for record in same_minute:
            self.manager.create_attempt(record)  # all at 19:00, ordered by UUID
        before = tree_snapshot(self.attempts)

        pages: list[HistoryPage] = []
        cursor = None
        # Ten records at four per page is three pages; a cursor that never
        # advances must fail here instead of looping forever.
        for _ in range(4):
            page = self.history.list_attempts(limit=4, cursor=cursor)
            pages.append(page)
            cursor = page.next_cursor
            if cursor is None:
                break
        else:
            self.fail("pagination did not terminate")

        self.assert_read_only(before)
        self.assertEqual([len(page.items) for page in pages], [4, 4, 2])
        seen = [attempt_id for page in pages for attempt_id in self.ids(page)]
        self.assertEqual(len(seen), len(set(seen)))
        # started[0] shares 19:00 with the three legacy records; ties order by UUID.
        expected = [state.attempt_id for state in reversed(started[1:])] + sorted(
            [started[0].attempt_id, *(record.attempt_id for record in same_minute)],
            reverse=True,
        )
        self.assertEqual(seen, expected)
        # The same cursor yields the same page again.
        self.assertEqual(
            self.ids(self.history.list_attempts(limit=4, cursor=pages[0].next_cursor)),
            self.ids(pages[1]),
        )
        self.assertEqual(self.history.list_attempts().limit, DEFAULT_PAGE_SIZE)

        with self.assertRaisesRegex(InvalidInputError, "does not match these filters"):
            self.history.list_attempts(
                limit=4, cursor=pages[0].next_cursor, filters={"status": ACTIVE}
            )
        malformed = {
            "garbage": "not-a-cursor",
            "wrong schema": base64.urlsafe_b64encode(
                json.dumps(
                    {
                        "schema_version": "history-cursor/v9",
                        "started_at": None,
                        "attempt_id": str(uuid4()),
                        "filters": HistoryFilters().fingerprint,
                    }
                ).encode()
            ).decode(),
            "extra key": base64.urlsafe_b64encode(b'{"schema_version":"history-cursor/v1","x":1}').decode(),
            "bad uuid": HistoryCursor(None, str(uuid4()), HistoryFilters().fingerprint).encode()[:-4] + "AAAA",
            "empty": "",
        }
        for label, value in malformed.items():
            with self.subTest(cursor=label):
                with self.assertRaisesRegex(InvalidInputError, "cursor"):
                    self.history.list_attempts(cursor=value)
        for limit in (0, MAX_PAGE_SIZE + 1, "10", True, 2.5):
            with self.subTest(limit=limit):
                with self.assertRaisesRegex(InvalidInputError, "limit"):
                    self.history.list_attempts(limit=limit)  # type: ignore[arg-type]
        with self.assertRaisesRegex(InvalidInputError, "unknown history filter"):
            self.history.list_attempts(filters={"newest": True})
        with self.assertRaisesRegex(InvalidInputError, "status filter"):
            self.history.list_attempts(filters={"status": "paused"})
        with self.assertRaisesRegex(InvalidInputError, "assessment_id filter"):
            self.history.list_attempts(filters={"assessment_id": "File Storage"})

    def test_records_changing_between_pages_refresh_rather_than_snapshot(self) -> None:
        for minute in range(5):
            self.start(minute)
        first = self.history.list_attempts(limit=2)

        newest = self.start(9)  # newer than every listed record
        removed = first.items[-1].attempt_id
        LocalFilesystem().remove_tree(self.attempts / removed)
        second = self.history.list_attempts(limit=2, cursor=first.next_cursor)

        # Newer records land before the boundary and belong to a refreshed first
        # page; a removed record simply disappears. No exception, no duplicates.
        self.assertNotIn(newest.attempt_id, self.ids(second))
        self.assertNotIn(removed, self.ids(second))
        self.assertEqual(len(second.items), 2)
        self.assertEqual(self.ids(self.history.list_attempts(limit=2))[0], newest.attempt_id)

    def test_filters_select_by_assessment_and_effective_status(self) -> None:
        active = self.start(0)
        finished = self.start(1)
        self.service.submit(finished.attempt_id)
        overdue = self.start(2, mode="drill", drill_duration_seconds=60)
        self.clock.value = START + timedelta(minutes=5)

        self.assertEqual(self.ids(self.history.list_attempts(filters={"status": ACTIVE})), [active.attempt_id])
        self.assertEqual(self.ids(self.history.list_attempts(filters={"status": EXPIRED})), [overdue.attempt_id])
        self.assertEqual(
            self.ids(self.history.list_attempts(filters={"status": SUBMITTED})),
            [finished.attempt_id],
        )
        self.assertEqual(
            len(self.history.list_attempts(filters={"assessment_id": "file_storage"}).items), 3
        )
        self.assertEqual(
            self.history.list_attempts(filters={"assessment_id": "other_track"}).items, ()
        )
        self.assertEqual(
            self.history.list_attempts(filters=HistoryFilters(status=ABANDONED)).items, ()
        )


class CorruptionAndPendingTests(HistoryTestCase):
    def test_unsafe_entries_are_skipped_and_corrupt_valid_ids_are_unavailable(self) -> None:
        good = self.start(0)
        corrupt = session(str(uuid4()))
        self.manager.create_attempt(corrupt)
        (self.attempts / corrupt.attempt_id / "session.json").write_text("{bad", encoding="utf-8")
        missing = str(uuid4())
        (self.attempts / missing).mkdir()  # valid ID, no session at all
        wrong_identity = session(str(uuid4()))
        self.manager.create_attempt(wrong_identity)
        other = session(str(uuid4()))
        (self.attempts / wrong_identity.attempt_id / "session.json").write_text(
            json.dumps(other.to_dict()), encoding="utf-8"
        )
        (self.attempts / "not-an-attempt").mkdir()
        os.symlink(self.attempts / good.attempt_id, self.attempts / str(uuid4()))
        (self.attempts / f".{uuid4()}.staging-{uuid4()}").mkdir()
        (self.attempts / "stray.txt").write_text("ignored", encoding="utf-8")
        before = tree_snapshot(self.attempts)

        page = self.history.list_attempts()

        self.assert_read_only(before)
        by_id = {item.attempt_id: item for item in page.items}
        self.assertEqual(
            set(by_id), {good.attempt_id, corrupt.attempt_id, missing, wrong_identity.attempt_id}
        )
        self.assertTrue(by_id[good.attempt_id].available)
        self.assertEqual(by_id[corrupt.attempt_id].issues, (RECORD_CORRUPT,))
        self.assertEqual(by_id[missing].issues, (RECORD_UNAVAILABLE,))
        self.assertEqual(by_id[wrong_identity.attempt_id].issues, (RECORD_CORRUPT,))
        for attempt_id in (corrupt.attempt_id, missing, wrong_identity.attempt_id):
            item = by_id[attempt_id]
            self.assertFalse(item.available)
            self.assertIsNone(item.status)
            self.assertIsNone(item.started_at)
        # Undated rows sort after every dated row, by UUID descending.
        self.assertEqual(self.ids(page)[0], good.attempt_id)
        self.assertEqual(
            self.ids(page)[1:],
            sorted((corrupt.attempt_id, missing, wrong_identity.attempt_id), reverse=True),
        )
        self.assertEqual(
            [(warning.code, warning.count) for warning in page.warnings],
            [(UNSAFE_ENTRIES_SKIPPED, 2)],
        )

        filtered = self.history.list_attempts(filters={"status": ACTIVE})
        self.assertEqual(self.ids(filtered), [good.attempt_id])
        self.assertEqual(
            [(warning.code, warning.count) for warning in filtered.warnings],
            [(UNAVAILABLE_RECORDS_EXCLUDED_BY_FILTER, 3), (UNSAFE_ENTRIES_SKIPPED, 2)],
        )

    def test_pending_restart_rows_are_reported_and_never_recovered_by_listing(self) -> None:
        old = self.start(0)
        neighbor = self.start(1)
        failing = WorkspaceManager(self.workspace_root, self.cache, filesystem=PointerFailFilesystem())
        request = RestartRequest(
            operation_id=str(uuid4()),
            old_attempt_id=old.attempt_id,
            expected_revision=0,
            assessment=self.cache.pinned_assessment(FILE_STORAGE),
            profile=old.profile,
        )
        self.clock.value = START + timedelta(minutes=2)
        with self.assertRaises(RestartRecoveryPendingError):
            failing.restart_attempt(request, now=self.clock.value)
        journal = json.loads(next((self.attempts / RESTART_JOURNAL_DIRECTORY).iterdir()).read_text())
        replacement_id = journal["replacement_state"]["attempt_id"]
        before = tree_snapshot(self.attempts)

        page = self.history.list_attempts()
        again = self.history.list_attempts()

        self.assert_read_only(before)
        self.assertEqual(page, again)
        by_id = {item.attempt_id: item for item in page.items}
        self.assertEqual(set(by_id), {old.attempt_id, neighbor.attempt_id, replacement_id})
        for pending in (old.attempt_id, replacement_id):
            self.assertFalse(by_id[pending].available)
            self.assertIn(RESTART_PENDING, by_id[pending].issues)
        self.assertTrue(by_id[neighbor.attempt_id].available)
        # Metadata is still shown honestly for a pending row that has a record.
        self.assertEqual(by_id[old.attempt_id].persisted_status, ABANDONED)
        self.assertEqual(by_id[replacement_id].persisted_status, ACTIVE)
        # An active filter hides the pending rows and counts them.
        filtered = self.history.list_attempts(filters={"status": ACTIVE})
        self.assertEqual(self.ids(filtered), [neighbor.attempt_id])
        self.assertEqual(
            [(warning.code, warning.count) for warning in filtered.warnings],
            [(UNAVAILABLE_RECORDS_EXCLUDED_BY_FILTER, 2)],
        )
        self.assertEqual(tree_snapshot(self.attempts), before)

        # A lifecycle entrypoint owns recovery; afterwards the rows are normal.
        self.assertEqual(self.manager.recover_restarts(), [request.operation_id])
        recovered = {item.attempt_id: item for item in self.history.list_attempts().items}
        self.assertTrue(recovered[old.attempt_id].available)
        self.assertTrue(recovered[replacement_id].available)
        self.assertEqual(recovered[old.attempt_id].issues, ())

    def test_unreadable_restart_journal_is_an_aggregate_warning_only(self) -> None:
        state = self.start(0)
        journal_directory = self.attempts / RESTART_JOURNAL_DIRECTORY
        journal_directory.mkdir()
        (journal_directory / f"{uuid4()}.json").write_text("{tampered", encoding="utf-8")
        before = tree_snapshot(self.attempts)

        page = self.history.list_attempts()

        self.assert_read_only(before)
        self.assertEqual(self.ids(page), [state.attempt_id])
        self.assertTrue(page.items[0].available)
        self.assertEqual(
            [(warning.code, warning.count) for warning in page.warnings],
            [(RESTART_JOURNALS_UNREADABLE, 1)],
        )

    def test_pending_finalization_markers_mark_rows_unavailable(self) -> None:
        submitting = self.start(0)
        ending = self.start(1)
        (self.attempts / submitting.attempt_id / SUBMISSION_RECOVERY_FILENAME).write_text("{}")
        (self.attempts / ending.attempt_id / ABANDONMENT_RECOVERY_FILENAME).write_text("{}")
        before = tree_snapshot(self.attempts)

        page = self.history.list_attempts()

        self.assert_read_only(before)
        for item in page.items:
            self.assertFalse(item.available)
            self.assertEqual(item.issues, (FINALIZATION_PENDING,))
            self.assertEqual(item.persisted_status, ACTIVE)

    def test_unsafe_attempts_directory_is_rejected(self) -> None:
        real = self.root / "elsewhere"
        real.mkdir()
        os.symlink(real, self.attempts)
        with self.assertRaisesRegex(SessionCorruptError, "unsafe"):
            self.history.list_attempts()
        os.unlink(self.attempts)
        self.attempts.write_text("file", encoding="utf-8")
        with self.assertRaisesRegex(SessionCorruptError, "unsafe"):
            self.history.list_attempts()


class ApplicationBoundaryTests(HistoryTestCase):
    def test_application_lists_without_selecting_or_reading_source(self) -> None:
        application = RuntimeApplication(
            self.workspace_root,
            clock=self.clock,
            cache=self.cache,
            scorer_factory=lambda _definition: RecordingScorer(),
        )
        first = application.start(assessment="file_storage", mode="full", drill_duration_seconds=None)
        application.abandon(attempt_id=first.attempt_id, expected_revision=0)
        self.clock.value = START + timedelta(minutes=1)
        second = application.start(assessment="file_storage", mode="drill", drill_duration_seconds=600)
        before = tree_snapshot(self.attempts)

        page = application.list_attempts(limit=1)
        rest = application.list_attempts(limit=1, cursor=page.next_cursor)

        self.assertEqual(tree_snapshot(self.attempts), before)
        self.assertEqual(self.ids(page), [second.attempt_id])
        self.assertEqual(self.ids(rest), [first.attempt_id])
        self.assertIsNone(rest.next_cursor)
        self.assertEqual(rest.items[0].status, ABANDONED)
        self.assertEqual(page.items[0].profile, ModeProfile("drill", "drill-30m", 600))
        self.assertEqual(application.status(attempt_id=None).attempt_id, second.attempt_id)
        document = page.to_dict()
        self.assertEqual(set(document), {"items", "next_cursor", "warnings", "filters", "limit"})
        json.dumps(document)


if __name__ == "__main__":
    unittest.main()
