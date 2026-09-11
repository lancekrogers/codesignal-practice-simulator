"""Safe derived-context and generated-status tests."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from codesignal_practice_simulator import rendering
from codesignal_practice_simulator.errors import LockUnavailableError, SessionUnavailableError
from codesignal_practice_simulator.filesystem import LocalFilesystem
from codesignal_practice_simulator.lifecycle import LifecycleService
from codesignal_practice_simulator.models import (
    ACTIVE,
    FULL_DURATION_SECONDS,
    FULL_MODE,
    FULL_PROFILE,
    SESSION_SCHEMA_VERSION,
    AssessmentMetadata,
    LevelResult,
    ModeProfile,
    ScoreSummary,
    SessionState,
)
from codesignal_practice_simulator.rendering import (
    DerivedStatusService,
    SESSION_UNAVAILABLE_MESSAGE,
    load_attempt_context,
    refresh_status,
    render_json,
    render_markdown,
)
from codesignal_practice_simulator.workspace import (
    CACHE_INPUTS,
    ValidatedFixtureCache,
    WorkspaceManager,
)


START = datetime(2026, 9, 8, 19, tzinfo=timezone.utc)


def state() -> SessionState:
    return SessionState(
        schema_version=SESSION_SCHEMA_VERSION,
        attempt_id=str(uuid4()),
        assessment=AssessmentMetadata("file_storage", "File Storage"),
        profile=ModeProfile(FULL_MODE, FULL_PROFILE, FULL_DURATION_SECONDS),
        started_at=START,
        deadline_at=START + timedelta(seconds=FULL_DURATION_SECONDS),
        status=ACTIVE,
        revision=0,
    )


def make_cache(root: Path) -> ValidatedFixtureCache:
    contents = {
        "vendor-readme.md": b"reference cache content must not render\n",
        "assessment/file_storage/simulation.py": b"candidate source must not render\n",
        "assessment/file_storage/test_simulation.py": b"answer-bearing test output\n",
        "assessment/file_storage/level1.md": b"level one\n",
        "assessment/file_storage/level2.md": b"level two\n",
        "assessment/file_storage/level3.md": b"level three\n",
        "assessment/file_storage/level4.md": b"level four\n",
    }
    assert set(
        path.rsplit("/", 1)[-1]
        for path in contents
        if path.startswith("assessment/")
    ) == set(CACHE_INPUTS)
    cache = root / "cache"
    hashes: dict[str, str] = {}
    for relative, content in contents.items():
        path = cache.joinpath(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        hashes[relative] = hashlib.sha256(content).hexdigest()
    return ValidatedFixtureCache(cache, hashes, content_version="upstream-0000000")


def tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and not path.name.endswith(".lock")
    }


class FailingStatusFilesystem(LocalFilesystem):
    """Fail the atomic status replacement after its temporary write."""

    def replace(self, source: Path, destination: Path) -> None:
        if destination.name == "STATUS.md":
            raise OSError("injected status replacement failure")
        super().replace(source, destination)


class FakeClock:
    def now(self) -> datetime:
        return START


class RenderingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.cache = make_cache(root)
        self.reference = root / "reference.md"
        self.reference.write_text("reference answer must not change\n", encoding="utf-8")
        self.workspace = WorkspaceManager(root / "workspace", self.cache)
        self.attempt = self.workspace.create_attempt(state())
        refresh_status(self.attempt, self.workspace.persistence)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_markdown_and_json_contain_only_safe_derived_context(self) -> None:
        event = self.workspace.persistence.read_events(self.attempt)[0]
        self.workspace.persistence.append_event(
            self.attempt,
            event.__class__(
                schema_version=event.schema_version,
                event_id=str(uuid4()),
                attempt_id=event.attempt_id,
                revision=1,
                occurred_at=event.occurred_at,
                name="tested",
                outcome="succeeded",
                arguments={"answer": "reference answer must not render"},
            ),
        )
        session = self.workspace.persistence.read_session(self.attempt)
        self.workspace.persistence.write_session(
            self.attempt,
            session.__class__(
                schema_version=session.schema_version,
                attempt_id=session.attempt_id,
                assessment=session.assessment,
                profile=session.profile,
                started_at=session.started_at,
                deadline_at=session.deadline_at,
                status=session.status,
                revision=1,
            ),
        )

        context = load_attempt_context(self.attempt, self.workspace.persistence)
        markdown = render_markdown(context)
        document = json.loads(render_json(context))

        self.assertEqual(document["attempt_id"], self.attempt.name)
        self.assertEqual(
            document["events"],
            [
                {
                    "revision": 0,
                    "occurred_at": START.isoformat(),
                    "name": "started",
                    "outcome": "succeeded",
                },
                {
                    "revision": 1,
                    "occurred_at": START.isoformat(),
                    "name": "tested",
                    "outcome": "succeeded",
                },
            ],
        )
        self.assertEqual(document["score"]["levels"], [])
        self.assertEqual(
            document["next_legal_commands"],
            [
                f"codesignal-sim status --attempt {self.attempt.name}",
                f"codesignal-sim context --attempt {self.attempt.name}",
                f"codesignal-sim resume --attempt {self.attempt.name}",
                f"codesignal-sim time --attempt {self.attempt.name}",
                f"codesignal-sim test --attempt {self.attempt.name}",
                f"codesignal-sim submit --attempt {self.attempt.name}",
            ],
        )
        self.assertIn("derived, non-authoritative session context", markdown)
        self.assertIn("Next legal commands", markdown)
        for forbidden in (
            "candidate source must not render",
            "answer-bearing test output",
            "reference cache content must not render",
            "reference answer must not render",
            "level one",
            "candidate_source",
            "simulation.py",
            "COACHING.md",
            "source history",
            "hidden-test",
        ):
            self.assertNotIn(forbidden, markdown)
            self.assertNotIn(forbidden, render_json(context))
        self.assertEqual(render_markdown(context), markdown)
        self.assertEqual(render_json(context), render_json(context))

    def test_lifecycle_transition_never_renders_and_explicit_refresh_uses_latest_state(self) -> None:
        initial = (self.attempt / "STATUS.md").read_text(encoding="utf-8")
        self.assertEqual(
            initial,
            render_markdown(load_attempt_context(self.attempt, self.workspace.persistence)),
        )

        score = ScoreSummary(
            tuple(LevelResult(level, "passed") for level in range(1, 5))
        )
        service = LifecycleService(self.workspace, FakeClock())
        service.record_test_result(score, self.attempt.name)
        durable_after_transition = (
            (self.attempt / "session.json").read_bytes(),
            (self.attempt / "events.jsonl").read_bytes(),
        )

        self.assertEqual((self.attempt / "STATUS.md").read_text(encoding="utf-8"), initial)
        with self.assertRaisesRegex(OSError, "injected status replacement failure"):
            refresh_status(
                self.attempt,
                self.workspace.persistence,
                filesystem=FailingStatusFilesystem(),
            )
        self.assertEqual(
            (
                (self.attempt / "session.json").read_bytes(),
                (self.attempt / "events.jsonl").read_bytes(),
            ),
            durable_after_transition,
        )

        refresh_status(self.attempt, self.workspace.persistence)
        refreshed = (self.attempt / "STATUS.md").read_text(encoding="utf-8")
        self.assertIn("- Passed levels: 4 of 4", refreshed)
        self.assertEqual(
            refreshed,
            render_markdown(load_attempt_context(self.attempt, self.workspace.persistence)),
        )

    def test_derived_status_is_best_effort_and_does_not_reject_lifecycle_results(self) -> None:
        service = DerivedStatusService(self.workspace)
        durable_before = (
            (self.attempt / "session.json").read_bytes(),
            (self.attempt / "events.jsonl").read_bytes(),
        )

        with patch.object(rendering, "refresh_status", side_effect=RuntimeError):
            self.assertIsNone(service.refresh(self.attempt.name))

        self.assertEqual(
            (
                (self.attempt / "session.json").read_bytes(),
                (self.attempt / "events.jsonl").read_bytes(),
            ),
            durable_before,
        )

    def test_derived_status_cannot_replace_newer_lifecycle_state(self) -> None:
        score = ScoreSummary(
            tuple(LevelResult(level, "passed") for level in range(1, 5))
        )
        lifecycle = LifecycleService(self.workspace, FakeClock())
        service = DerivedStatusService(self.workspace)
        original_write_status = rendering.write_status
        lifecycle_write_blocked = False

        def write_status_after_attempted_transition(*args: object, **kwargs: object) -> None:
            nonlocal lifecycle_write_blocked
            try:
                lifecycle.record_test_result(score, self.attempt.name)
            except LockUnavailableError:
                lifecycle_write_blocked = True
            original_write_status(*args, **kwargs)

        with patch.object(
            rendering, "write_status", side_effect=write_status_after_attempted_transition
        ):
            refreshed = service.refresh(self.attempt.name)

        self.assertIsNotNone(refreshed)
        self.assertTrue(lifecycle_write_blocked)
        self.assertEqual(self.workspace.persistence.read_session(self.attempt).revision, 0)

        lifecycle.record_test_result(score, self.attempt.name)
        service.refresh(self.attempt.name)
        self.assertIn(
            "- Passed levels: 4 of 4",
            (self.attempt / "STATUS.md").read_text(encoding="utf-8"),
        )

    def test_coaching_and_regenerated_status_preserve_candidate_state_cache_and_reference(self) -> None:
        candidate_before = (self.attempt / "simulation.py").read_bytes()
        state_before = (
            (self.attempt / "session.json").read_bytes(),
            (self.attempt / "events.jsonl").read_bytes(),
        )
        cache_before = tree_bytes(self.cache.root)
        reference_before = self.reference.read_bytes()

        (self.attempt / "COACHING.md").write_text(
            "Candidate-approved question only.\n", encoding="utf-8"
        )
        refresh_status(self.attempt, self.workspace.persistence)

        self.assertEqual((self.attempt / "simulation.py").read_bytes(), candidate_before)
        self.assertEqual(
            (
                (self.attempt / "session.json").read_bytes(),
                (self.attempt / "events.jsonl").read_bytes(),
            ),
            state_before,
        )
        self.assertEqual(tree_bytes(self.cache.root), cache_before)
        self.assertEqual(self.reference.read_bytes(), reference_before)

    def test_invalid_session_or_events_return_unavailable_without_status_write(self) -> None:
        status_before = (self.attempt / "STATUS.md").read_bytes()
        (self.attempt / "events.jsonl").write_text("{invalid", encoding="utf-8")

        with self.assertRaisesRegex(SessionUnavailableError, SESSION_UNAVAILABLE_MESSAGE):
            refresh_status(self.attempt, self.workspace.persistence)
        self.assertEqual((self.attempt / "STATUS.md").read_bytes(), status_before)

        self.workspace.persistence.write_session(self.attempt, state())
        with self.assertRaisesRegex(SessionUnavailableError, SESSION_UNAVAILABLE_MESSAGE):
            refresh_status(self.attempt, self.workspace.persistence)
        self.assertEqual((self.attempt / "STATUS.md").read_bytes(), status_before)

    def test_renderer_failure_preserves_candidate_state_cache_and_reference_bytes(self) -> None:
        attempt_before = tree_bytes(self.attempt)
        cache_before = tree_bytes(self.cache.root)
        reference_before = self.reference.read_bytes()

        with self.assertRaisesRegex(OSError, "injected status replacement failure"):
            refresh_status(
                self.attempt,
                self.workspace.persistence,
                filesystem=FailingStatusFilesystem(),
            )

        self.assertEqual(tree_bytes(self.attempt), attempt_before)
        self.assertEqual(tree_bytes(self.cache.root), cache_before)
        self.assertEqual(self.reference.read_bytes(), reference_before)
        self.assertFalse(list(self.attempt.glob(".STATUS.md.*.tmp")))

    def test_attempt_templates_state_the_operational_boundary(self) -> None:
        coaching = (self.attempt / "COACHING.md").read_text(encoding="utf-8")
        instructions = (self.attempt / "AGENTS.md").read_text(encoding="utf-8")

        self.assertIn("candidate-owned, non-executable", coaching.lower())
        for required in (
            "candidate-approved",
            "source",
            "history",
            "hidden-test claims",
            "simulation.py",
            "post-attempt",
        ):
            self.assertIn(required, coaching.lower())
        for required in (
            "STATUS.md",
            "context --workspace-root PATH",
            "COACHING.md",
            "candidate-approved",
            "explicit permission",
            "source history",
            "reference, solution, stages, walkthrough",
            "study, vendor, fixture cache, copied tests",
            "hidden-test material",
            "simulation.py",
            "session.json",
            "events.jsonl",
            "locks",
            "active.json",
            "Browser UI and CLI",
            "timer, scoring",
            "operational policy, not a security sandbox",
        ):
            self.assertIn(required, instructions)
        self.assertNotIn("read or edit candidate code only", instructions.lower())
        self.assertIn("codesignal-sim context", instructions)


if __name__ == "__main__":
    unittest.main()
