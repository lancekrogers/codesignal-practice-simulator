"""Deterministic application-service tests for attempt lifecycle rules."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from codesignal_practice_simulator.errors import (
    IllegalLifecycleError,
    LockUnavailableError,
    SessionCorruptError,
)
from codesignal_practice_simulator.lifecycle import LifecycleService
from codesignal_practice_simulator.models import (
    ACTIVE,
    DRILL_DEFAULT_DURATION_SECONDS,
    EXPIRED,
    FULL_DURATION_SECONDS,
    SUBMITTED,
    AssessmentMetadata,
    LevelResult,
    ScoreSummary,
)
from codesignal_practice_simulator.workspace import (
    CACHE_INPUTS,
    ValidatedFixtureCache,
    WorkspaceManager,
)


START = datetime(2026, 9, 8, 19, 0, tzinfo=timezone.utc)


class FakeClock:
    def __init__(self, value: datetime = START) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


class RecordingScorer:
    def __init__(self, result: ScoreSummary) -> None:
        self.result = result
        self.calls: list[Path] = []

    def __call__(self, attempt: Path) -> ScoreSummary:
        self.calls.append(attempt)
        return self.result


def score() -> ScoreSummary:
    return ScoreSummary(
        (
            LevelResult(1, "passed"),
            LevelResult(2, "failed"),
            LevelResult(3, "error"),
            LevelResult(4, "passed"),
        )
    )


def make_cache(root: Path) -> ValidatedFixtureCache:
    cache = root / "cache"
    contents = {"vendor-readme.md": b"vendor readme\n"}
    contents.update(
        {
            f"assessment/file_storage/{name}": f"fixture {name}\n".encode()
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


def durable_bytes(attempt: Path) -> tuple[bytes, bytes]:
    return (
        (attempt / "session.json").read_bytes(),
        (attempt / "events.jsonl").read_bytes(),
    )


class LifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.manager = WorkspaceManager(root / "workspace", make_cache(root))
        self.clock = FakeClock()
        self.scorer = RecordingScorer(score())
        self.service = LifecycleService(self.manager, self.clock, self.scorer)
        self.assessment = AssessmentMetadata("file_storage", "File Storage")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def start(self, **kwargs: object):
        state = self.service.start(self.assessment, **kwargs)
        return state, self.manager.resolve_attempt(state.attempt_id)

    def test_start_creates_selected_full_or_drill_attempt(self) -> None:
        full, full_attempt = self.start()
        self.assertEqual(full.status, ACTIVE)
        self.assertEqual(full.profile.duration_seconds, FULL_DURATION_SECONDS)
        self.assertEqual(self.manager.resolve_attempt(), full_attempt)
        self.assertEqual(
            [event.name for event in self.manager.persistence.read_events(full_attempt)],
            ["started"],
        )

        drill, drill_attempt = self.start(mode="drill", drill_duration_seconds=71)
        self.assertEqual(drill.profile.duration_seconds, 71)
        self.assertEqual(self.manager.resolve_attempt(), drill_attempt)
        self.assertEqual(full_attempt.exists(), True)
        self.assertEqual(DRILL_DEFAULT_DURATION_SECONDS, 1800)

    def test_explicit_active_resume_replaces_selection(self) -> None:
        first, first_attempt = self.start()
        second, second_attempt = self.start()
        first_before = durable_bytes(first_attempt)
        second_before = durable_bytes(second_attempt)

        resumed = self.service.resume(first.attempt_id)

        self.assertEqual(resumed, first)
        self.assertEqual(self.manager.resolve_attempt(), first_attempt)
        self.assertNotEqual(first_attempt, second_attempt)
        self.assertEqual(durable_bytes(first_attempt), first_before)
        self.assertEqual(durable_bytes(second_attempt), second_before)

    def test_status_and_time_before_deadline_are_safe_reads(self) -> None:
        state, attempt = self.start()
        before = durable_bytes(attempt)
        self.clock.value = START + timedelta(seconds=30)

        self.assertEqual(self.service.status(), state)
        observed = self.service.time()

        self.assertEqual(observed.state, state)
        self.assertEqual(observed.elapsed_seconds, 30)
        self.assertEqual(observed.remaining_seconds, FULL_DURATION_SECONDS - 30)
        self.assertEqual(durable_bytes(attempt), before)

    def test_first_overdue_status_observer_persists_exactly_one_expiry(self) -> None:
        state, attempt = self.start()
        self.clock.value = state.deadline_at

        expired = self.service.status()
        bytes_after_expiry = durable_bytes(attempt)
        observed = self.service.time()

        self.assertEqual(expired.status, EXPIRED)
        self.assertEqual(expired.revision, 1)
        self.assertEqual(observed.state, expired)
        self.assertEqual(observed.remaining_seconds, 0)
        self.assertEqual(durable_bytes(attempt), bytes_after_expiry)
        self.assertEqual(
            [(event.name, event.revision) for event in self.manager.persistence.read_events(attempt)],
            [("started", 0), ("expired", 1)],
        )

    def test_record_test_result_updates_active_state_under_one_revision(self) -> None:
        state, attempt = self.start()

        recorded = self.service.record_test_result(score())

        self.assertEqual(recorded.status, ACTIVE)
        self.assertEqual(recorded.score, score())
        self.assertEqual(recorded.revision, state.revision + 1)
        self.assertEqual(
            [event.name for event in self.manager.persistence.read_events(attempt)],
            ["started", "tested"],
        )

    def test_test_runs_injected_scorer_then_records_result(self) -> None:
        state, attempt = self.start()

        recorded = self.service.test()

        self.assertEqual(recorded.revision, state.revision + 1)
        self.assertEqual(recorded.score, score())
        self.assertEqual(self.scorer.calls, [attempt])

    def test_expired_resume_and_test_are_exit_four_and_byte_identical(self) -> None:
        state, attempt = self.start()
        self.clock.value = state.deadline_at
        self.assertEqual(self.service.status().status, EXPIRED)
        before = durable_bytes(attempt)

        with self.assertRaisesRegex(IllegalLifecycleError, "cannot resume"):
            self.service.resume()
        with self.assertRaisesRegex(IllegalLifecycleError, "cannot test"):
            self.service.test()

        self.assertEqual(durable_bytes(attempt), before)
        self.assertEqual(self.scorer.calls, [])

    def test_terminal_commands_do_not_recover_a_missing_current_event(self) -> None:
        for status in (EXPIRED, SUBMITTED):
            for command in ("resume", "test", "record_test_result"):
                with self.subTest(status=status, command=command):
                    state, attempt = self.start()
                    terminal = replace(
                        state,
                        status=status,
                        revision=state.revision + 1,
                        score=score() if status == SUBMITTED else None,
                        submitted_at=state.started_at if status == SUBMITTED else None,
                    )
                    self.manager.persistence.write_session(attempt, terminal)
                    before = durable_bytes(attempt)

                    with self.assertRaisesRegex(IllegalLifecycleError, "cannot"):
                        if command == "resume":
                            self.service.resume(state.attempt_id)
                        elif command == "test":
                            self.service.test(state.attempt_id)
                        else:
                            self.service.record_test_result(score(), state.attempt_id)

                    self.assertEqual(durable_bytes(attempt), before)
                    self.assertEqual(
                        [event.revision for event in self.manager.persistence.read_events(attempt)],
                        [state.revision],
                    )
        self.assertEqual(self.scorer.calls, [])

    def test_submitted_attempt_refuses_resume_and_test_without_mutation(self) -> None:
        _state, attempt = self.start()
        self.service.submit()
        before = durable_bytes(attempt)
        scorer_calls = list(self.scorer.calls)

        with self.assertRaisesRegex(IllegalLifecycleError, "cannot resume"):
            self.service.resume()
        with self.assertRaisesRegex(IllegalLifecycleError, "cannot test"):
            self.service.test()

        self.assertEqual(durable_bytes(attempt), before)
        self.assertEqual(self.scorer.calls, scorer_calls)

    def test_submit_active_and_repeat_submit_returns_the_stored_result_without_writes(self) -> None:
        state, attempt = self.start()

        first = self.service.submit()
        before_repeat = durable_bytes(attempt)
        second = self.service.submit()

        self.assertEqual(first.state.status, SUBMITTED)
        self.assertEqual(first.state.revision, state.revision + 1)
        self.assertEqual(first, second)
        self.assertEqual(durable_bytes(attempt), before_repeat)
        self.assertEqual(self.scorer.calls, [attempt])
        self.assertEqual(
            [event.name for event in self.manager.persistence.read_events(attempt)],
            ["started", "submitted"],
        )

    def test_repeat_submit_without_scorer_preserves_submitted_missing_event_bytes(self) -> None:
        state, attempt = self.start()
        submitted = replace(
            state,
            status=SUBMITTED,
            revision=state.revision + 1,
            score=score(),
            submitted_at=state.started_at,
        )
        self.manager.persistence.write_session(attempt, submitted)
        before = durable_bytes(attempt)
        without_scorer = LifecycleService(self.manager, self.clock)

        result = without_scorer.submit(state.attempt_id)

        self.assertEqual(result.state, submitted)
        self.assertEqual(result.score, submitted.score)
        self.assertEqual(durable_bytes(attempt), before)
        self.assertEqual(
            [event.revision for event in self.manager.persistence.read_events(attempt)],
            [state.revision],
        )

    def test_overdue_submit_persists_expiry_before_one_submission(self) -> None:
        state, attempt = self.start()
        self.clock.value = state.deadline_at

        submitted = self.service.submit()

        self.assertEqual(submitted.state.status, SUBMITTED)
        self.assertEqual(submitted.state.revision, 2)
        self.assertEqual(
            [(event.name, event.revision) for event in self.manager.persistence.read_events(attempt)],
            [("started", 0), ("expired", 1), ("submitted", 2)],
        )
        self.assertEqual(self.scorer.calls, [attempt])

    def test_submit_finalizes_a_previously_expired_attempt_once(self) -> None:
        state, attempt = self.start()
        self.clock.value = state.deadline_at
        self.assertEqual(self.service.status().status, EXPIRED)

        result = self.service.submit()
        before_repeat = durable_bytes(attempt)

        self.assertEqual(result.state.status, SUBMITTED)
        self.assertEqual(result.state.revision, 2)
        self.assertEqual(self.service.submit(), result)
        self.assertEqual(durable_bytes(attempt), before_repeat)
        self.assertEqual(self.scorer.calls, [attempt])

    def test_next_command_recovers_a_missing_event_for_the_current_revision(self) -> None:
        state, attempt = self.start()
        revised = state.__class__(
            schema_version=state.schema_version,
            attempt_id=state.attempt_id,
            assessment=state.assessment,
            profile=state.profile,
            started_at=state.started_at,
            deadline_at=state.deadline_at,
            status=state.status,
            revision=1,
        )
        self.manager.persistence.write_session(attempt, revised)

        recovered = self.service.status()

        self.assertEqual(recovered, revised)
        self.assertEqual(
            [(event.name, event.outcome, event.revision) for event in self.manager.persistence.read_events(attempt)],
            [("started", "succeeded", 0), ("recovered", "recovered", 1)],
        )

    def test_lock_contention_returns_exit_four_and_preserves_neighboring_attempt(self) -> None:
        state, attempt = self.start()
        _neighbor_state, neighbor = self.start()
        neighbor_before = durable_bytes(neighbor)

        with self.manager.persistence.attempt_lock(attempt):
            with self.assertRaises(LockUnavailableError):
                self.service.status(state.attempt_id)

        self.assertEqual(durable_bytes(neighbor), neighbor_before)

    def test_corrupt_active_selection_fails_but_explicit_selection_still_works(self) -> None:
        first, first_attempt = self.start()
        _second, second_attempt = self.start()
        (self.manager.attempts_directory / "active.json").write_text("{bad", encoding="utf-8")
        first_before = durable_bytes(first_attempt)
        second_before = durable_bytes(second_attempt)

        self.assertEqual(self.service.status(first.attempt_id).attempt_id, first.attempt_id)
        with self.assertRaises(SessionCorruptError):
            self.service.status()

        self.assertEqual(durable_bytes(first_attempt), first_before)
        self.assertEqual(durable_bytes(second_attempt), second_before)

    def test_expiring_one_attempt_leaves_neighbor_bytes_unchanged(self) -> None:
        first, first_attempt = self.start()
        _second, second_attempt = self.start()
        second_before = durable_bytes(second_attempt)
        self.clock.value = first.deadline_at

        self.assertEqual(self.service.status(first.attempt_id).status, EXPIRED)

        self.assertEqual(durable_bytes(second_attempt), second_before)


if __name__ == "__main__":
    unittest.main()
