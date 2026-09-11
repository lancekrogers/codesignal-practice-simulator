"""Focused tests for the prompt retrieval service boundary."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from codesignal_practice_simulator.errors import (  # noqa: E402
    InvalidInputError,
    LockUnavailableError,
    SessionUnavailableError,
)
from codesignal_practice_simulator.models import (  # noqa: E402
    ACTIVE,
    ACTIVE_POINTER_SCHEMA_VERSION,
    FULL_DURATION_SECONDS,
    FULL_MODE,
    FULL_PROFILE,
    ActivePointer,
    SESSION_SCHEMA_VERSION,
    AssessmentMetadata,
    ModeProfile,
    SessionState,
)
from codesignal_practice_simulator.prompts import PromptResult, PromptService  # noqa: E402
from codesignal_practice_simulator.persistence import Persistence  # noqa: E402
from codesignal_practice_simulator.workspace import (  # noqa: E402
    CACHE_INPUTS,
    ValidatedFixtureCache,
    WorkspaceManager,
)


class RecordingPersistence(Persistence):
    """Record lock order and inject work just before an attempt lock is taken."""

    def __init__(self) -> None:
        super().__init__()
        self.lock_calls: list[tuple[str, Path]] = []
        self.before_attempt_lock = None

    @contextmanager
    def workspace_lock(self, attempts_directory: Path) -> Iterator[None]:
        self.lock_calls.append(("workspace", attempts_directory))
        with super().workspace_lock(attempts_directory):
            yield

    @contextmanager
    def attempt_lock(self, attempt_directory: Path) -> Iterator[None]:
        self.lock_calls.append(("attempt", attempt_directory))
        if self.before_attempt_lock is not None:
            self.before_attempt_lock()
        with super().attempt_lock(attempt_directory):
            yield


def make_cache(root: Path) -> ValidatedFixtureCache:
    cache = root / "cache"
    contents = {"vendor-readme.md": b"vendor fixture\n"}
    contents.update(
        {
            f"assessment/file_storage/{filename}": f"cached {filename}\n".encode()
            for filename in CACHE_INPUTS
        }
    )
    hashes: dict[str, str] = {}
    for relative, data in contents.items():
        path = cache.joinpath(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        hashes[relative] = hashlib.sha256(data).hexdigest()
    return ValidatedFixtureCache(cache, hashes, content_version="upstream-0000000")


def state(attempt_id: str) -> SessionState:
    started_at = datetime(2026, 9, 8, 19, tzinfo=timezone.utc)
    return SessionState(
        schema_version=SESSION_SCHEMA_VERSION,
        attempt_id=attempt_id,
        assessment=AssessmentMetadata("file_storage", "File Storage"),
        profile=ModeProfile(FULL_MODE, FULL_PROFILE, FULL_DURATION_SECONDS),
        started_at=started_at,
        deadline_at=started_at + timedelta(seconds=FULL_DURATION_SECONDS),
        status=ACTIVE,
        revision=0,
    )


class PromptServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.workspace = root / "workspace"
        self.workspace.mkdir()
        self.manager = WorkspaceManager(self.workspace, make_cache(root))
        self.first = self.manager.create_attempt(state(str(uuid4())))
        self.service = PromptService(self.manager)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_reads_typed_result_under_attempt_lock(self) -> None:
        with patch.object(
            self.manager.persistence,
            "attempt_lock",
            wraps=self.manager.persistence.attempt_lock,
        ) as attempt_lock:
            result = self.service.read_prompt(level=1)

        self.assertEqual(
            result,
            PromptResult(self.first.name, 1, "cached level1.md\n"),
        )
        attempt_lock.assert_called_once_with(self.first.resolve())

    def test_explicit_selection_precedes_a_corrupt_active_pointer(self) -> None:
        second = self.manager.create_attempt(state(str(uuid4())))
        (self.workspace / "attempts" / "active.json").write_text("{bad", encoding="utf-8")
        (self.first / "level1.md").write_text("first prompt\n", encoding="utf-8")

        result = self.service.read_prompt(attempt_id=self.first.name, level=1)

        self.assertEqual(result.attempt_id, self.first.name)
        self.assertEqual(result.prompt, "first prompt\n")
        self.assertTrue(second.exists())

    def test_active_selection_and_prompt_read_hold_workspace_then_attempt_locks(self) -> None:
        persistence = RecordingPersistence()
        manager = WorkspaceManager(
            self.workspace, self.manager.cache, persistence=persistence
        )
        first = manager.resolve_attempt()
        second = manager.create_attempt(state(str(uuid4())))
        (second / "level1.md").write_text("second prompt\n", encoding="utf-8")
        persistence.lock_calls.clear()
        pointer_update_blocked = False

        def try_to_select_first() -> None:
            nonlocal pointer_update_blocked
            try:
                persistence.write_active_pointer(
                    manager.attempts_directory,
                    ActivePointer(ACTIVE_POINTER_SCHEMA_VERSION, first.name),
                )
            except LockUnavailableError:
                pointer_update_blocked = True

        persistence.before_attempt_lock = try_to_select_first
        result = PromptService(manager).read_prompt(level=1)

        self.assertEqual(result, PromptResult(second.name, 1, "second prompt\n"))
        self.assertTrue(pointer_update_blocked)
        self.assertEqual(
            persistence.lock_calls[:2],
            [
                ("workspace", manager.attempts_directory),
                ("attempt", second),
            ],
        )
        self.assertEqual(manager.resolve_attempt(), second)

    def test_rejects_invalid_levels_and_unsafe_or_unreadable_prompt_files(self) -> None:
        with self.assertRaisesRegex(InvalidInputError, "level is unavailable"):
            self.service.read_prompt(level=5)
        with self.assertRaisesRegex(InvalidInputError, "level must be an integer"):
            self.service.read_prompt(level=True)  # type: ignore[arg-type]

        prompt = self.first / "level1.md"
        prompt.unlink()
        prompt.symlink_to(self.first / "simulation.py")
        with self.assertRaisesRegex(SessionUnavailableError, "selected level is unavailable"):
            self.service.read_prompt(level=1)

        prompt.unlink()
        prompt.write_bytes(b"\xff")
        with self.assertRaisesRegex(SessionUnavailableError, "cannot read selected level"):
            self.service.read_prompt(level=1)

    def test_revalidates_persisted_registry_state_before_reading(self) -> None:
        session = json.loads((self.first / "session.json").read_text(encoding="utf-8"))
        session["assessment"]["assessment_id"] = "removed_assessment"
        (self.first / "session.json").write_text(json.dumps(session), encoding="utf-8")

        with self.assertRaisesRegex(
            SessionUnavailableError, "assessment is not registered"
        ):
            self.service.read_prompt(level=1)


if __name__ == "__main__":
    unittest.main()
