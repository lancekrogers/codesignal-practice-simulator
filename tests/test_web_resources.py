from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from codesignal_practice_simulator.web import resources


class WebResourceTests(unittest.TestCase):
    def test_manifest_rejects_listed_filesystem_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "manifest.json").write_text(
                '{"index.html":{"media_type":"text/html","cache_control":"no-store"}}',
                encoding="utf-8",
            )
            (root / "real.html").write_text("shell", encoding="utf-8")
            (root / "index.html").symlink_to(root / "real.html")
            with patch.object(resources.resources, "files", return_value=root):
                with self.assertRaises(OSError):
                    resources.asset_names()

    def test_manifest_must_be_valid_and_wheel_resource_is_readable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "manifest.json").write_text("{broken", encoding="utf-8")
            with patch.object(resources.resources, "files", return_value=root):
                with self.assertRaises(OSError):
                    resources.asset_names()
        asset = resources.read_asset("index.html")
        self.assertGreater(len(asset.body), 0)
        self.assertEqual(asset.media_type, "text/html; charset=utf-8")


if __name__ == "__main__":
    unittest.main()
