"""Transactional workspace creation, recovery, cache, and isolation tests."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from codesignal_practice_simulator.errors import (
    FixtureSetupRequiredError,
    InvalidInputError,
    SessionCorruptError,
)
from codesignal_practice_simulator.workspace import (
    CREATION_MARKER,
    PublishInterrupted,
    WorkspaceManager,
)
from tests.workspace_test_support import (
    CACHE_INPUTS,
    RecordingFilesystem,
    ValidatedFixtureCache,
    make_cache,
    session,
    tree_bytes,
    tree_snapshot,
    workspace_environment,
)


class WorkspaceTests(unittest.TestCase):
    def _environment(self) -> tuple[object, Path, ValidatedFixtureCache]:
        return workspace_environment()

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

    def test_each_cache_record_hash_is_checked_before_workspace_mutation(self) -> None:
        """Every declared cache input must match before an attempt path exists."""
        cache_paths = (
            "vendor-readme.md",
            *(f"assessment/file_storage/{name}" for name in CACHE_INPUTS),
        )
        self.assertEqual(len(cache_paths), 7)
        for relative_path in cache_paths:
            with self.subTest(relative_path=relative_path):
                temporary, root, cache = self._environment()
                try:
                    self.assertEqual(set(cache.hashes), set(cache_paths))
                    cache_file = cache.root.joinpath(*relative_path.split("/"))
                    cache_file.write_bytes(cache_file.read_bytes() + b"tampered\n")

                    with self.assertRaisesRegex(
                        FixtureSetupRequiredError,
                        f"cache hash mismatch for {relative_path}",
                    ):
                        WorkspaceManager(root, cache).create_attempt(session(str(uuid4())))

                    self.assertFalse((root / "attempts").exists())
                finally:
                    temporary.cleanup()

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

    def test_dangling_attempts_symlink_is_rejected_without_target_mutation(self) -> None:
        temporary, root, cache = self._environment()
        self.addCleanup(temporary.cleanup)
        target_parent = root / "unowned-target"
        target_parent.mkdir()
        sentinel = target_parent / "sentinel.txt"
        sentinel.write_text("keep\n", encoding="utf-8")
        target = target_parent / "attempts"
        attempts = root / "attempts"
        attempts.symlink_to(target, target_is_directory=True)

        manager = WorkspaceManager(root, cache)
        with self.assertRaisesRegex(
            InvalidInputError, "must be a non-symlink directory"
        ):
            manager.create_attempt(session(str(uuid4())))
        with self.assertRaisesRegex(
            InvalidInputError, "must be a non-symlink directory"
        ):
            manager.reconcile()

        self.assertFalse(target.exists())
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")
        self.assertTrue(attempts.is_symlink())

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

    def test_attempt_templates_preserve_coaching_and_permission_boundaries(self) -> None:
        temporary, root, cache = self._environment()
        self.addCleanup(temporary.cleanup)
        attempt = WorkspaceManager(root, cache).create_attempt(session(str(uuid4())))
        coaching = (attempt / "COACHING.md").read_text(encoding="utf-8").lower()
        instructions = (attempt / "AGENTS.md").read_text(encoding="utf-8").lower()

        for required in (
            "candidate-owned, non-executable",
            "candidate-approved",
            "source",
            "history",
            "hidden-test claims",
            "simulation.py",
            "post-attempt",
        ):
            self.assertIn(required, coaching)
        for required in (
            "status.md",
            "context --workspace-root path",
            "coaching.md",
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
            "browser ui and cli",
            "timer, scoring",
            "operational policy, not a security sandbox",
        ):
            self.assertIn(required, instructions)
        self.assertNotIn("read or edit candidate code only", instructions)

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
