from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from codesignal_practice_simulator.web import resources


class WebResourceTests(unittest.TestCase):
    def test_imported_and_first_time_static_package_reads_verify_every_hash(self) -> None:
        static_module = __import__(
            "codesignal_practice_simulator.web.static",
            fromlist=["__name__"],
        )
        manifest = json.loads(
            (Path(static_module.__file__).parent / "manifest.json").read_text()
        )
        self.assertEqual(set(resources.asset_names()), set(manifest))
        for name, record in manifest.items():
            asset = resources.read_asset(name)
            self.assertEqual(hashlib.sha256(asset.body).hexdigest(), record.get("sha256", hashlib.sha256(asset.body).hexdigest()))
            self.assertEqual(len(asset.body), record.get("size", len(asset.body)))

        project = Path(__file__).resolve().parents[1]
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(project / "src")
        probe = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import hashlib, json; "
                    "from codesignal_practice_simulator.web.resources import asset_names, read_asset; "
                    "names = asset_names(); "
                    "print(json.dumps({name: hashlib.sha256(read_asset(name).body).hexdigest() for name in names}, sort_keys=True))"
                ),
            ],
            cwd=project,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(probe.returncode, 0, probe.stderr)
        self.assertEqual(
            set(json.loads(probe.stdout)),
            set(manifest),
        )

    def test_marker_keeps_readers_on_valid_previous_generation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            live = root / "static"
            previous = root / ".static.previous"
            shutil.copytree(
                Path(__file__).resolve().parents[1]
                / "src"
                / "codesignal_practice_simulator"
                / "web"
                / "static",
                previous,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            shutil.copytree(previous, live)
            old_body = (previous / "index.html").read_bytes()
            new_body = b"new generation\n"
            (live / "index.html").write_bytes(new_body)
            manifest = json.loads((live / "manifest.json").read_text())
            manifest["index.html"]["sha256"] = hashlib.sha256(new_body).hexdigest()
            manifest["index.html"]["size"] = len(new_body)
            (live / "manifest.json").write_text(json.dumps(manifest))
            (root / ".static.publish.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "backup": str(previous),
                        "stage": str(root / ".static.stage-test"),
                        "phase": "old-moved",
                    }
                )
            )
            with patch.object(resources, "_resource_root", return_value=live):
                self.assertEqual(resources.read_asset("index.html").body, old_body)
                (root / ".static.publish.json").unlink()
                self.assertEqual(resources.read_asset("index.html").body, new_body)

    def test_marker_fails_closed_for_hash_valid_previous_missing_required_asset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            live = root / "static"
            previous = root / ".static.previous"
            shutil.copytree(
                Path(__file__).resolve().parents[1]
                / "src"
                / "codesignal_practice_simulator"
                / "web"
                / "static",
                previous,
            )
            shutil.copytree(previous, live)
            (previous / "favicon.svg").unlink()
            manifest = json.loads((previous / "manifest.json").read_text())
            del manifest["favicon.svg"]
            (previous / "manifest.json").write_text(json.dumps(manifest))
            (root / ".static.publish.json").write_text("{}")
            with patch.object(resources, "_resource_root", return_value=live):
                with self.assertRaisesRegex(OSError, "unavailable"):
                    resources.asset_names()

    def test_undeclared_generation_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            live = root / "static"
            shutil.copytree(
                Path(__file__).resolve().parents[1]
                / "src"
                / "codesignal_practice_simulator"
                / "web"
                / "static",
                live,
            )
            (live / "unexpected.txt").write_text("not packaged", encoding="utf-8")
            with patch.object(resources, "_resource_root", return_value=live):
                with self.assertRaisesRegex(OSError, "incomplete"):
                    resources.asset_names()

    def test_invalid_previous_generation_is_not_used_as_reader_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            live = root / "static"
            target = root / "target"
            shutil.copytree(
                Path(__file__).resolve().parents[1]
                / "src"
                / "codesignal_practice_simulator"
                / "web"
                / "static",
                target,
            )
            (root / ".static.previous").symlink_to(target, target_is_directory=True)
            with patch.object(resources, "_resource_root", return_value=live):
                with self.assertRaises(OSError):
                    resources.asset_names()

    def test_reader_lock_wait_has_a_bounded_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = root.parent / f".{root.name}.publish.lock"
            lock.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "kind": "build",
                        "pid": os.getpid(),
                        "token": "active-reader-test",
                    }
                )
            )
            with patch.object(resources, "_resource_root", return_value=root):
                with patch.object(resources, "_READER_WAIT_SECONDS", 0.05):
                    with patch.object(resources, "_READER_POLL_SECONDS", 0.005):
                        with self.assertRaisesRegex(OSError, "did not become available"):
                            resources.asset_names()
            lock.unlink()

    def test_multiple_readers_reclaim_stale_lock_serially(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = root.parent / f".{root.name}.publish.lock"
            lock.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "kind": "build",
                        "pid": 2_147_483_647,
                        "token": "stale-owner",
                    }
                )
            )
            script = """
import sys
import time
from pathlib import Path
from codesignal_practice_simulator.web.resources import _publication_reader_lock

root = Path(sys.argv[1])
with _publication_reader_lock(root):
    print(time.monotonic(), flush=True)
    time.sleep(0.25)
"""
            processes = [
                subprocess.Popen(
                    [sys.executable, "-c", script, str(root)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env={
                        **os.environ,
                        "PYTHONPATH": str(
                            Path(__file__).resolve().parents[1] / "src"
                        ),
                    },
                )
                for _ in range(3)
            ]
            results = [process.communicate(timeout=10) for process in processes]
            for process, (stdout, stderr) in zip(processes, results):
                self.assertEqual(process.returncode, 0, stderr)
                self.assertEqual(len(stdout.splitlines()), 1, stderr)
            starts = sorted(float(stdout.strip()) for stdout, _stderr in results)
            self.assertGreaterEqual(starts[1] - starts[0], 0.18)
            self.assertGreaterEqual(starts[2] - starts[1], 0.18)
            self.assertFalse(lock.exists())
            self.assertFalse(Path(f"{lock}.reclaimer").exists())

    def test_read_asset_rejects_hash_and_size_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            body = b"stable\n"
            (root / "index.html").write_bytes(body)
            (root / "manifest.json").write_text(
                json.dumps(
                    {
                        "index.html": {
                            "media_type": "text/html; charset=utf-8",
                            "cache_control": "no-store",
                            "sha256": hashlib.sha256(body).hexdigest(),
                            "size": len(body),
                        },
                        "manifest.json": {
                            "media_type": "application/json; charset=utf-8",
                            "cache_control": "no-store",
                        },
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(resources, "_resource_root", return_value=root):
                self.assertEqual(resources.read_asset("index.html").body, body)
                (root / "index.html").write_bytes(b"stablE\n")
                with self.assertRaisesRegex(OSError, "hash"):
                    resources.read_asset("index.html")
                (root / "index.html").write_bytes(body)
                manifest = json.loads((root / "manifest.json").read_text())
                manifest["index.html"]["size"] += 1
                (root / "manifest.json").write_text(
                    json.dumps(manifest),
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(OSError, "size"):
                    resources.read_asset("index.html")

    def test_manifest_record_requires_json_media_type_and_no_store_cache(self) -> None:
        body = b"stable\n"
        for field, value in (
            ("media_type", "text/plain; charset=utf-8"),
            ("cache_control", "public, max-age=31536000, immutable"),
        ):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                manifest = {
                    "index.html": {
                        "media_type": "text/html; charset=utf-8",
                        "cache_control": "no-store",
                        "sha256": hashlib.sha256(body).hexdigest(),
                        "size": len(body),
                    },
                    "manifest.json": {
                        "media_type": "application/json; charset=utf-8",
                        "cache_control": "no-store",
                    },
                }
                manifest["manifest.json"][field] = value
                (root / "index.html").write_bytes(body)
                (root / "manifest.json").write_text(
                    json.dumps(manifest),
                    encoding="utf-8",
                )
                with patch.object(resources, "_resource_root", return_value=root):
                    with self.assertRaisesRegex(OSError, "manifest"):
                        resources._load_manifest(root)

    def test_manifest_rejects_listed_filesystem_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "manifest.json").write_text(
                '{"index.html":{"media_type":"text/html","cache_control":"no-store"}}',
                encoding="utf-8",
            )
            (root / "real.html").write_text("shell", encoding="utf-8")
            (root / "index.html").symlink_to(root / "real.html")
            with patch.object(resources, "_resource_root", return_value=root):
                with self.assertRaises(OSError):
                    resources.asset_names()

    def test_manifest_must_be_valid_and_wheel_resource_is_readable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "manifest.json").write_text("{broken", encoding="utf-8")
            with patch.object(resources, "_resource_root", return_value=root):
                with self.assertRaises(OSError):
                    resources.asset_names()
        asset = resources.read_asset("index.html")
        self.assertGreater(len(asset.body), 0)
        self.assertEqual(asset.media_type, "text/html; charset=utf-8")


if __name__ == "__main__":
    unittest.main()
