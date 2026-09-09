"""Focused tests for validated fixture-cache metadata boundaries."""

from __future__ import annotations

import tempfile
import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from codesignal_practice_simulator.errors import FixtureSetupRequiredError
from codesignal_practice_simulator.workspace_cache import ValidatedFixtureCache


class WorkspaceCacheTests(unittest.TestCase):
    def test_invalid_manifest_encoding_is_a_fixture_setup_required_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "docs" / "migration-manifest.json"
            manifest.parent.mkdir()
            manifest.write_bytes(b"\xff")

            with self.assertRaisesRegex(
                FixtureSetupRequiredError, "cannot read manifest"
            ):
                ValidatedFixtureCache.from_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
