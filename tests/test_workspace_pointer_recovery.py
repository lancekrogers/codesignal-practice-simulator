"""Pointer recovery tests for transactional workspace creation."""

from __future__ import annotations

import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from uuid import uuid4

from codesignal_practice_simulator.workspace import CREATION_MARKER
from tests.workspace_test_support import (
    PersistentPointerFailureFilesystem,
    PointerFlushThenReportFilesystem,
    PublishThenReportFilesystem,
    ValidatedFixtureCache,
    WorkspaceManager,
    existing_attempt,
    session,
    tree_bytes,
    workspace_environment,
)


class WorkspacePointerRecoveryTests(unittest.TestCase):
    def _environment(
        self,
    ) -> tuple[TemporaryDirectory[str], Path, ValidatedFixtureCache]:
        return workspace_environment()

    def _with_existing_attempt(
        self, root: Path, cache: ValidatedFixtureCache
    ) -> tuple[WorkspaceManager, Path]:
        return existing_attempt(root, cache)

    def test_reported_after_publish_failure_rolls_back_the_owned_attempt(self) -> None:
        temporary, root, cache = self._environment()
        self.addCleanup(temporary.cleanup)
        _manager, old = self._with_existing_attempt(root, cache)
        attempts = root / "attempts"
        pointer_before = (attempts / "active.json").read_bytes()
        state = session(str(uuid4()))

        with self.assertRaisesRegex(OSError, "publish failure after replacement"):
            WorkspaceManager(
                root, cache, filesystem=PublishThenReportFilesystem(state.attempt_id)
            ).create_attempt(state)

        self.assertFalse((attempts / state.attempt_id).exists())
        self.assertTrue(old.exists())
        self.assertEqual((attempts / "active.json").read_bytes(), pointer_before)

    def test_reported_pointer_flush_failure_restores_the_prior_selection(self) -> None:
        temporary, root, cache = self._environment()
        self.addCleanup(temporary.cleanup)
        _manager, old = self._with_existing_attempt(root, cache)
        attempts = root / "attempts"
        pointer_before = (attempts / "active.json").read_bytes()
        state = session(str(uuid4()))

        with self.assertRaisesRegex(OSError, "pointer flush failure after replacement"):
            WorkspaceManager(
                root, cache, filesystem=PointerFlushThenReportFilesystem(attempts)
            ).create_attempt(state)

        self.assertFalse((attempts / state.attempt_id).exists())
        self.assertTrue(old.exists())
        self.assertEqual((attempts / "active.json").read_bytes(), pointer_before)

    def test_unverifiable_pointer_restore_leaves_marker_for_reconciliation(self) -> None:
        for has_prior_pointer in (False, True):
            for final_pointer in ("prior", "new"):
                with self.subTest(
                    has_prior_pointer=has_prior_pointer, final_pointer=final_pointer
                ):
                    self._assert_unverifiable_restore(
                        has_prior_pointer, final_pointer
                    )

    def _assert_unverifiable_restore(
        self, has_prior_pointer: bool, final_pointer: str
    ) -> None:
        temporary, root, cache = self._environment()
        try:
            old, old_before = self._prepare_prior_attempt(
                root, cache, has_prior_pointer
            )
            attempts = root / "attempts"
            cache_before = tree_bytes(cache.root)
            state = session(str(uuid4()))
            failing = WorkspaceManager(
                root,
                cache,
                filesystem=PersistentPointerFailureFilesystem(
                    attempts, final_pointer=final_pointer
                ),
            )

            with self.assertRaisesRegex(OSError, "pointer flush failure"):
                failing.create_attempt(state)

            self._assert_published_marker(attempts, state.attempt_id)
            self._assert_pointer(
                failing, attempts, state.attempt_id, old, final_pointer
            )
            self._assert_reconciled(
                root,
                cache,
                state.attempt_id,
                cache_before,
                old,
                old_before,
                final_pointer,
            )
        finally:
            temporary.cleanup()

    def _prepare_prior_attempt(
        self, root: Path, cache: ValidatedFixtureCache, has_prior_pointer: bool
    ) -> tuple[Path | None, dict[str, bytes] | None]:
        if has_prior_pointer:
            _manager, old = self._with_existing_attempt(root, cache)
            return old, tree_bytes(old)
        (root / "attempts").mkdir()
        return None, None

    def _assert_published_marker(self, attempts: Path, attempt_id: str) -> None:
        published = attempts / attempt_id
        self.assertTrue(published.is_dir())
        self.assertTrue((published / CREATION_MARKER).is_file())

    def _assert_pointer(
        self,
        manager: WorkspaceManager,
        attempts: Path,
        attempt_id: str,
        old: Path | None,
        final_pointer: str,
    ) -> None:
        pointer = manager.persistence.read_active_pointer(attempts)
        expected = (
            attempt_id
            if final_pointer == "new"
            else None if old is None else old.name
        )
        self.assertEqual(None if pointer is None else pointer.attempt_id, expected)

    def _assert_reconciled(
        self,
        root: Path,
        cache: ValidatedFixtureCache,
        attempt_id: str,
        cache_before: dict[str, bytes],
        old: Path | None,
        old_before: dict[str, bytes] | None,
        final_pointer: str,
    ) -> None:
        reconciled = WorkspaceManager(root, cache).reconcile()
        published = root / "attempts" / attempt_id
        self.assertEqual(tree_bytes(cache.root), cache_before)
        if old is not None:
            self.assertEqual(tree_bytes(old), old_before)
        if final_pointer == "prior":
            self.assertEqual(reconciled, [attempt_id])
            self.assertFalse(published.exists())
            restored = WorkspaceManager(root, cache).persistence.read_active_pointer(
                root / "attempts"
            )
            expected = None if old is None else old.name
            self.assertEqual(
                None if restored is None else restored.attempt_id,
                expected,
            )
        else:
            self.assertEqual(reconciled, [])
            self.assertTrue(published.is_dir())
            self.assertFalse((published / CREATION_MARKER).exists())
            self.assertEqual(
                WorkspaceManager(root, cache)
                .persistence.read_active_pointer(root / "attempts")
                .attempt_id,
                attempt_id,
            )


if __name__ == "__main__":
    unittest.main()
