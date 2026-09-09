"""Transactional workspace creation, recovery, cache, and isolation tests."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from codesignal_practice_simulator.errors import (
    FixtureSetupRequiredError,
    InvalidInputError,
    SessionCorruptError,
)
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
from codesignal_practice_simulator.workspace import (
    CACHE_INPUTS,
    CREATION_MARKER,
    PublishInterrupted,
    ValidatedFixtureCache,
    WorkspaceManager,
)


def session(attempt_id: str) -> SessionState:
    started = datetime(2026, 9, 8, 19, tzinfo=timezone.utc)
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


def make_cache(root: Path) -> ValidatedFixtureCache:
    cache = root / "cache"
    hashes: dict[str, str] = {}
    contents = {"vendor-readme.md": b"vendor readme\n"}
    contents.update(
        {
            f"assessment/file_storage/{name}": f"fixture {name}\n".encode()
            for name in CACHE_INPUTS
        }
    )
    for relative, data in contents.items():
        path = cache.joinpath(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        hashes[relative] = hashlib.sha256(data).hexdigest()
    return ValidatedFixtureCache(cache, hashes)


def tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and not path.name.endswith(".lock")
    }


def tree_snapshot(root: Path) -> dict[str, tuple[str, bytes | str | None]]:
    """Capture paths and bytes, including symlinks, for mutation assertions."""
    snapshot: dict[str, tuple[str, bytes | str | None]] = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            snapshot[relative] = ("symlink", os.readlink(path))
        elif path.is_dir():
            snapshot[relative] = ("directory", None)
        elif path.is_file():
            snapshot[relative] = ("file", path.read_bytes())
    return snapshot


class RecordingFilesystem(LocalFilesystem):
    """Records and optionally fails exactly one mutating filesystem call."""

    def __init__(self, fail_operation: str | None = None, fail_call: int = 0) -> None:
        self.fail_operation = fail_operation
        self.fail_call = fail_call
        self.calls: dict[str, int] = {}

    def _record(self, operation: str) -> None:
        self.calls[operation] = self.calls.get(operation, 0) + 1
        if operation == self.fail_operation and self.calls[operation] == self.fail_call:
            raise OSError(f"injected {operation} failure {self.fail_call}")

    def mkdir(self, path: Path, *, parents: bool = False, exist_ok: bool = False) -> None:
        self._record("mkdir")
        super().mkdir(path, parents=parents, exist_ok=exist_ok)

    def copyfile(self, source: Path, destination: Path) -> None:
        self._record("copyfile")
        super().copyfile(source, destination)

    def write_bytes(self, path: Path, data: bytes) -> None:
        self._record("write_bytes")
        super().write_bytes(path, data)

    def flush_file(self, path: Path) -> None:
        self._record("flush_file")
        super().flush_file(path)

    def replace(self, source: Path, destination: Path) -> None:
        self._record("replace")
        super().replace(source, destination)


class WorkspaceTests(unittest.TestCase):
    def _environment(self) -> tuple[tempfile.TemporaryDirectory[str], Path, ValidatedFixtureCache]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name) / "workspace"
        root.mkdir()
        return temporary, root, make_cache(Path(temporary.name))

    def _with_existing_attempt(
        self, root: Path, cache: ValidatedFixtureCache
    ) -> tuple[WorkspaceManager, Path]:
        manager = WorkspaceManager(root, cache)
        old = manager.create_attempt(session(str(uuid4())))
        return manager, old

    def test_creation_copies_only_six_assessment_files_and_keeps_cache_immutable(self) -> None:
        temporary, root, cache = self._environment()
        self.addCleanup(temporary.cleanup)
        before = tree_bytes(cache.root)

        attempt = WorkspaceManager(root, cache).create_attempt(session(str(uuid4())))

        self.assertEqual(before, tree_bytes(cache.root))
        self.assertEqual(
            {
                path.name
                for path in attempt.iterdir()
                if path.is_file() and not path.name.startswith(".")
            }
            - {"session.json", "events.jsonl", "COACHING.md", "AGENTS.md"},
            set(CACHE_INPUTS),
        )
        for filename in CACHE_INPUTS:
            self.assertEqual(
                (attempt / filename).read_bytes(),
                (cache.root / "assessment" / "file_storage" / filename).read_bytes(),
            )
        self.assertFalse((attempt / "vendor-readme.md").exists())
        self.assertFalse((attempt / CREATION_MARKER).exists())
        self.assertEqual(
            WorkspaceManager(root, cache).resolve_attempt().name,
            attempt.name,
        )

    def test_invalid_or_absent_cache_creates_nothing(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / "workspace"
        root.mkdir()
        missing = ValidatedFixtureCache(root / "absent-cache", {})

        with self.assertRaisesRegex(FixtureSetupRequiredError, "setup is required"):
            WorkspaceManager(root, missing).create_attempt(session(str(uuid4())))

        self.assertFalse((root / "attempts").exists())

    def test_hash_invalid_cache_creates_nothing(self) -> None:
        temporary, root, cache = self._environment()
        self.addCleanup(temporary.cleanup)
        (cache.root / "assessment" / "file_storage" / "level1.md").write_text(
            "changed cache bytes\n", encoding="utf-8"
        )

        with self.assertRaisesRegex(FixtureSetupRequiredError, "hash mismatch"):
            WorkspaceManager(root, cache).create_attempt(session(str(uuid4())))

        self.assertFalse((root / "attempts").exists())

    def test_attempts_symlink_to_cache_is_rejected_without_cache_mutation(self) -> None:
        temporary, root, cache = self._environment()
        self.addCleanup(temporary.cleanup)
        attempts = root / "attempts"
        attempts.symlink_to(cache.root, target_is_directory=True)
        cache_before = tree_snapshot(cache.root)

        manager = WorkspaceManager(root, cache)
        with self.assertRaisesRegex(InvalidInputError, "must not overlap"):
            manager.create_attempt(session(str(uuid4())))
        with self.assertRaisesRegex(InvalidInputError, "must not overlap"):
            manager.reconcile()

        self.assertEqual(tree_snapshot(cache.root), cache_before)
        self.assertTrue(attempts.is_symlink())
        self.assertEqual(attempts.resolve(), cache.root.resolve())

    def test_cache_nested_in_attempts_is_rejected_without_cache_mutation(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / "workspace"
        root.mkdir()
        cache = make_cache(root / "attempts")
        cache_before = tree_snapshot(cache.root)

        with self.assertRaisesRegex(InvalidInputError, "must not overlap"):
            WorkspaceManager(root, cache).create_attempt(session(str(uuid4())))

        self.assertEqual(tree_snapshot(cache.root), cache_before)
        self.assertFalse((root / "attempts" / ".workspace.lock").exists())

    def test_workspace_with_cache_symlink_ancestor_is_rejected_before_mutation(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        cache = make_cache(Path(temporary.name))
        workspace_target = cache.root / "workspace"
        workspace_target.mkdir()
        workspace = Path(temporary.name) / "workspace-alias"
        workspace.symlink_to(workspace_target, target_is_directory=True)
        cache_before = tree_snapshot(cache.root)

        with self.assertRaisesRegex(InvalidInputError, "must not overlap"):
            WorkspaceManager(workspace, cache).create_attempt(session(str(uuid4())))

        self.assertEqual(tree_snapshot(cache.root), cache_before)
        self.assertTrue(workspace.is_symlink())
        self.assertFalse((workspace_target / "attempts").exists())

    def test_every_creation_filesystem_failure_rolls_back_only_new_attempt(self) -> None:
        """Exercise every individual mkdir/copy/write/flush/replace creation call."""
        temporary, root, cache = self._environment()
        self.addCleanup(temporary.cleanup)
        _manager, old = self._with_existing_attempt(root, cache)
        new_state = session(str(uuid4()))
        recorder = RecordingFilesystem()
        WorkspaceManager(root, cache, filesystem=recorder).create_attempt(new_state)
        counts = recorder.calls.copy()

        for operation, count in counts.items():
            for call in range(1, count + 1):
                with self.subTest(operation=operation, call=call):
                    case_temporary, case_root, case_cache = self._environment()
                    try:
                        _case_manager, case_old = self._with_existing_attempt(
                            case_root, case_cache
                        )
                        attempts = case_root / "attempts"
                        pointer_before = (attempts / "active.json").read_bytes()
                        old_before = tree_bytes(case_old)
                        cache_before = tree_bytes(case_cache.root)
                        state = session(new_state.attempt_id)
                        manager = WorkspaceManager(
                            case_root,
                            case_cache,
                            filesystem=RecordingFilesystem(operation, call),
                        )

                        with self.assertRaisesRegex(OSError, f"injected {operation}"):
                            manager.create_attempt(state)

                        self.assertEqual((attempts / "active.json").read_bytes(), pointer_before)
                        self.assertEqual(tree_bytes(case_old), old_before)
                        self.assertEqual(tree_bytes(case_cache.root), cache_before)
                        self.assertFalse((attempts / state.attempt_id).exists())
                        self.assertFalse(
                            list(attempts.glob(f".{state.attempt_id}.staging-*"))
                        )
                    finally:
                        case_temporary.cleanup()

    def test_publish_before_pointer_interruption_reconciles_only_owned_attempt(self) -> None:
        temporary, root, cache = self._environment()
        self.addCleanup(temporary.cleanup)
        manager, old = self._with_existing_attempt(root, cache)
        old_pointer = (root / "attempts" / "active.json").read_bytes()
        second_old = root / "attempts" / str(uuid4())
        second_old.mkdir()
        (second_old / "keep.txt").write_text("pre-existing", encoding="utf-8")
        new_state = session(str(uuid4()))

        with self.assertRaises(PublishInterrupted):
            manager.create_attempt(new_state, interrupt_after_publish=True)

        unpublished = root / "attempts" / new_state.attempt_id
        self.assertTrue((unpublished / CREATION_MARKER).is_file())
        self.assertEqual(manager.reconcile(), [new_state.attempt_id])
        self.assertFalse(unpublished.exists())
        self.assertEqual((root / "attempts" / "active.json").read_bytes(), old_pointer)
        self.assertTrue(old.exists())
        self.assertEqual((second_old / "keep.txt").read_text(encoding="utf-8"), "pre-existing")

    def test_reconciliation_never_deletes_unowned_or_pointer_selected_attempt(self) -> None:
        temporary, root, cache = self._environment()
        self.addCleanup(temporary.cleanup)
        manager, selected = self._with_existing_attempt(root, cache)
        marker = {
            "schema_version": "attempt-creation/v1",
            "attempt_id": selected.name,
            "creation_token": str(uuid4()),
        }
        (selected / CREATION_MARKER).write_text(json.dumps(marker), encoding="utf-8")
        inactive = root / "attempts" / str(uuid4())
        inactive.mkdir()
        (inactive / CREATION_MARKER).write_text("{not valid", encoding="utf-8")

        self.assertEqual(manager.reconcile(), [])
        self.assertTrue(selected.exists())
        self.assertFalse((selected / CREATION_MARKER).exists())
        self.assertTrue(inactive.exists())

    def test_corrupt_pointer_and_explicit_selection_precedence(self) -> None:
        temporary, root, cache = self._environment()
        self.addCleanup(temporary.cleanup)
        manager, old = self._with_existing_attempt(root, cache)
        explicit = WorkspaceManager(root, cache).create_attempt(session(str(uuid4())))
        (root / "attempts" / "active.json").write_text("{broken", encoding="utf-8")

        self.assertEqual(manager.resolve_attempt(old.name), old)
        with self.assertRaises(SessionCorruptError):
            manager.resolve_attempt()
        with self.assertRaises(SessionCorruptError):
            manager.reconcile()
        with self.assertRaises(InvalidInputError):
            manager.resolve_attempt("not-a-uuid")
        self.assertTrue(old.exists())
        self.assertTrue(explicit.exists())


if __name__ == "__main__":
    unittest.main()
