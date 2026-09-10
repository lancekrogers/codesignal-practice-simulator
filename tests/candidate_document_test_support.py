"""Shared fixtures and assertions for candidate-document tests."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4

from codesignal_practice_simulator.candidate_documents import (
    HISTORY_DIRECTORY,
    HISTORY_ORDER_FILENAME,
    INITIAL_SOURCE_FILENAME,
    CandidateDocumentService,
)
from codesignal_practice_simulator.clock import Clock
from codesignal_practice_simulator.filesystem import LocalFilesystem
from codesignal_practice_simulator.models import (
    ACTIVE,
    FULL_DURATION_SECONDS,
    FULL_MODE,
    FULL_PROFILE,
    SESSION_SCHEMA_VERSION,
    AssessmentMetadata,
    ModeProfile,
    SessionState,
)
from codesignal_practice_simulator.workspace import CACHE_INPUTS, ValidatedFixtureCache, WorkspaceManager


PROMPT_BYTES = b"synthetic prompt\n"
TEST_BYTES = b"synthetic test fixture\n"
VENDOR_BYTES = b"synthetic vendor fixture\n"
FORBIDDEN_FIXTURE_BYTES = (PROMPT_BYTES, TEST_BYTES, VENDOR_BYTES)


class MutableClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


class CandidateFailureFilesystem(LocalFilesystem):
    """Inject one failure at a named candidate-source boundary."""

    def __init__(self, boundary: str) -> None:
        self.boundary = boundary
        self.failed = False
        self.history_flushes = 0

    def flush_file(self, path: Path) -> None:
        if (
            self.boundary == "snapshot_flush"
            and path.parent.name == HISTORY_DIRECTORY
            and not self.failed
        ):
            self.failed = True
            raise OSError("injected snapshot flush failure")
        super().flush_file(path)

    def replace(self, source: Path, destination: Path) -> None:
        if (
            self.boundary == "source_replace_cleanup"
            and destination.name == "simulation.py"
            and not self.failed
        ):
            self.failed = True
            raise OSError("injected source replacement failure")
        if (
            self.boundary == "source_replace"
            and destination.name == "simulation.py"
            and not self.failed
        ):
            super().replace(source, destination)
            self.failed = True
            raise OSError("injected source replacement failure")
        super().replace(source, destination)

    def unlink(self, path: Path) -> None:
        if (
            self.boundary == "source_replace_cleanup"
            and self.failed
            and path.parent.name == HISTORY_DIRECTORY
            and path.suffix == ".json"
        ):
            raise OSError("injected snapshot cleanup failure")
        super().unlink(path)

    def flush_directory(self, path: Path) -> None:
        if (
            self.boundary == "prune_flush"
            and path.name == HISTORY_DIRECTORY
            and not self.failed
        ):
            self.history_flushes += 1
            if self.history_flushes == 1:
                super().flush_directory(path)
                return
            super().flush_directory(path)
            self.failed = True
            raise OSError("injected pruning flush failure")
        super().flush_directory(path)


def make_cache(root: Path) -> ValidatedFixtureCache:
    cache = root / "cache"
    contents = {"vendor-readme.md": VENDOR_BYTES}
    contents.update(
        {
            f"assessment/file_storage/{name}": (
                PROMPT_BYTES
                if name.startswith("level")
                else b"cached simulation.py fixture\n"
                if name == "simulation.py"
                else TEST_BYTES
            )
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


def make_session(attempt_id: str) -> SessionState:
    started = datetime(2026, 9, 9, 9, tzinfo=timezone.utc)
    return SessionState(
        schema_version=SESSION_SCHEMA_VERSION,
        attempt_id=attempt_id,
        assessment=AssessmentMetadata("file_storage", "File Storage"),
        profile=ModeProfile(FULL_MODE, FULL_PROFILE, FULL_DURATION_SECONDS),
        started_at=started,
        deadline_at=started + timedelta(seconds=FULL_DURATION_SECONDS),
        status=ACTIVE,
        revision=0,
    )


class CandidateDocumentTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.workspace_root = root / "workspace"
        self.workspace_root.mkdir()
        self.cache = make_cache(root)
        self.clock: Clock = MutableClock(datetime(2026, 9, 9, 10, tzinfo=timezone.utc))
        self.manager = WorkspaceManager(self.workspace_root, self.cache)
        self.state = make_session(str(uuid4()))
        self.attempt = self.manager.create_attempt(self.state)
        self.service = CandidateDocumentService(self.manager, self.clock)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def attempt_bytes(self) -> dict[str, object]:
        history = self.attempt / HISTORY_DIRECTORY
        history_bytes = tuple(
            sorted(
                (path.name, path.read_bytes())
                for path in history.iterdir()
            )
        )
        return {
            "source": (self.attempt / "simulation.py").read_bytes(),
            "baseline": (self.attempt / INITIAL_SOURCE_FILENAME).read_bytes(),
            "history": history_bytes,
            "order": (self.attempt / HISTORY_ORDER_FILENAME).read_bytes(),
            "session": (self.attempt / "session.json").read_bytes(),
            "events": (self.attempt / "events.jsonl").read_bytes(),
        }

    def attempt_tree_bytes(self) -> tuple[tuple[str, bytes], ...]:
        return tuple(
            sorted(
                (
                    path.relative_to(self.attempt).as_posix(),
                    path.read_bytes(),
                )
                for path in self.attempt.rglob("*")
                if path.is_file() and not path.is_symlink()
            )
        )

    def assert_rejected_without_mutation(
        self, operation: Callable[[], object], error_type: type[BaseException]
    ) -> None:
        before = self.attempt_bytes()
        with self.assertRaises(error_type):
            operation()
        self.assertEqual(self.attempt_bytes(), before)
