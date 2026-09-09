"""Tests for wheel-safe, FETCH_ONLY fixture setup."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from codesignal_practice_simulator.fixture_setup import (
    FixtureSetupError,
    load_runtime_manifest,
    populate_runtime_fixture,
)


def synthetic_manifest() -> tuple[dict[str, object], dict[str, bytes]]:
    """Build metadata and bytes that cannot be mistaken for vendor content."""
    payloads = {
        f"upstream/file-{index}.txt": f"fixture {index}\n".encode()
        for index in range(7)
    }
    return (
        {
            "fixture_cache_root": ".cache/codesignal-fixtures/test",
            "upstream": {"repository": "example/fixtures", "commit": "pinned"},
            "fetches": [
                {
                    "upstream_path": upstream_path,
                    "repository_path": upstream_path,
                    "cache_path": f"assessment/file-{index}.txt",
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
                for index, (upstream_path, data) in enumerate(payloads.items())
            ],
        },
        payloads,
    )


def write_offline_source(root: Path, payloads: dict[str, bytes]) -> Path:
    """Create a complete synthetic source tree for an offline fixture fetch."""
    source = root / "offline-source"
    for relative, data in payloads.items():
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return source


class FixtureSetupTests(unittest.TestCase):
    def test_packaged_metadata_matches_the_canonical_fetch_records(self) -> None:
        canonical = json.loads(
            (PROJECT / "docs" / "migration-manifest.json").read_text(encoding="utf-8")
        )
        packaged = load_runtime_manifest()

        self.assertEqual(
            packaged["fetches"],
            [
                {
                    key: record[key]
                    for key in ("upstream_path", "repository_path", "cache_path", "sha256")
                }
                for record in canonical["fetches"]
            ],
        )

    def test_packaged_setup_logic_fetches_and_validates_without_checkout_scripts(self) -> None:
        manifest, payloads = synthetic_manifest()
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "outside-checkout"
            with patch(
                "codesignal_practice_simulator.fixture_setup.load_runtime_manifest",
                return_value=manifest,
            ):
                cache = populate_runtime_fixture(
                    workspace,
                    downloader=lambda url: payloads[
                        "upstream/" + url.rsplit("/", 1)[-1]
                    ],
                )

            self.assertEqual(
                {
                    path.relative_to(cache).as_posix(): path.read_bytes()
                    for path in cache.rglob("*")
                    if path.is_file()
                },
                {
                    f"assessment/file-{index}.txt": data
                    for index, data in enumerate(payloads.values())
                },
            )
            self.assertFalse((workspace / "attempts").exists())

    def test_setup_refuses_an_attempts_symlink_to_its_cache_before_writing(self) -> None:
        manifest, _payloads = synthetic_manifest()
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            workspace.mkdir()
            cache = workspace / ".cache" / "codesignal-fixtures" / "test"
            (workspace / "attempts").symlink_to(cache, target_is_directory=True)

            with (
                patch(
                    "codesignal_practice_simulator.fixture_setup.load_runtime_manifest",
                    return_value=manifest,
                ),
                self.assertRaisesRegex(FixtureSetupError, "must not overlap"),
            ):
                populate_runtime_fixture(workspace, downloader=lambda _url: b"unsafe")

            self.assertTrue((workspace / "attempts").is_symlink())
            self.assertFalse(cache.exists())

    def test_publish_restores_the_old_cache_after_staging_rename_failure(self) -> None:
        manifest, payloads = synthetic_manifest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            source = write_offline_source(root, payloads)
            with patch(
                "codesignal_practice_simulator.fixture_setup.load_runtime_manifest",
                return_value=manifest,
            ):
                cache = populate_runtime_fixture(workspace, source_root=source)
                before = {
                    path.relative_to(cache).as_posix(): path.read_bytes()
                    for path in cache.rglob("*")
                    if path.is_file()
                }
                replace = os.replace

                def fail_staging_publish(source_path: Path, destination: Path) -> None:
                    if (
                        Path(source_path).name.startswith(".test.staging-")
                        and Path(destination) == cache
                    ):
                        raise OSError("injected staging publish failure")
                    replace(source_path, destination)

                with (
                    patch(
                        "codesignal_practice_simulator.fixture_setup.os.replace",
                        side_effect=fail_staging_publish,
                    ),
                    self.assertRaisesRegex(
                        FixtureSetupError, "could not publish validated fixture cache"
                    ),
                ):
                    populate_runtime_fixture(workspace, source_root=source)

            self.assertEqual(
                {
                    path.relative_to(cache).as_posix(): path.read_bytes()
                    for path in cache.rglob("*")
                    if path.is_file()
                },
                before,
            )
            self.assertFalse(list(cache.parent.glob(".test.previous-*")))

    def test_publish_never_removes_an_unowned_legacy_backup_path(self) -> None:
        manifest, payloads = synthetic_manifest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            source = write_offline_source(root, payloads)
            legacy_backup = (
                workspace / ".cache" / "codesignal-fixtures" / ".test.previous"
            )
            legacy_backup.mkdir(parents=True)
            sentinel = legacy_backup / "keep.txt"
            sentinel.write_text("unowned content", encoding="utf-8")

            with patch(
                "codesignal_practice_simulator.fixture_setup.load_runtime_manifest",
                return_value=manifest,
            ):
                populate_runtime_fixture(workspace, source_root=source)

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "unowned content")


if __name__ == "__main__":
    unittest.main()
