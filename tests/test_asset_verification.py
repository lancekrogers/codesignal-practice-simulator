"""Bounded reproducibility and distribution checks for browser assets."""

from __future__ import annotations

import importlib
import json
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
STATIC = PROJECT / "src" / "codesignal_practice_simulator" / "web" / "static"
WEBUI = PROJECT / "webui"
sys.path.insert(0, str(PROJECT / "scripts"))

import check_assets  # noqa: E402
from check_assets import (  # noqa: E402
    AssetCheckError,
    REQUIRED_RUNTIME_NOTICE_MAPPING,
    _check_runtime_notice_boundary,
    check_static_root,
    scan_text,
)
from packaging_support import discover_packaging_interpreter  # noqa: E402


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=180,
    )


def _manifest() -> dict[str, object]:
    return json.loads((STATIC / "manifest.json").read_text(encoding="utf-8"))


def _packaged_static_bytes() -> dict[str, bytes]:
    names = set(_manifest()) | {"__init__.py"}
    return {name: (STATIC / name).read_bytes() for name in names}


def _copy_static_without_caches(destination: Path) -> None:
    shutil.copytree(
        STATIC,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )


def _static_members(members: list[str]) -> set[str]:
    prefix = "codesignal_practice_simulator/web/static/"
    return {
        member.removeprefix(prefix)
        for member in members
        if member.startswith(prefix) and not member.endswith("/")
    }


ARCHIVE_FORBIDDEN_PARTS = frozenset(
    {
        "node_modules",
        ".cache",
        ".pytest_cache",
        "__pycache__",
        ".tmp",
        "test-results",
        "playwright-report",
        "playwright-reports",
        "playwright-cache",
        ".playwright",
        ".npm",
        "npm-cache",
        "npm_cache",
        "build",
        "dist",
    }
)


def _reject_forbidden_archive_paths(members: list[str]) -> None:
    for member in members:
        parts = set(re.split(r"[/\\]+", member.lower()))
        if parts & ARCHIVE_FORBIDDEN_PARTS:
            raise AssetCheckError(f"forbidden archive path: {member}")


def _assert_clean_asset_bytes(test: unittest.TestCase, name: str, body: bytes) -> None:
    try:
        scan_text(name, body)
    except AssetCheckError as error:
        test.fail(str(error))


def _assert_archive_is_clean(test: unittest.TestCase, members: list[str]) -> None:
    try:
        _reject_forbidden_archive_paths(members)
    except AssetCheckError as error:
        test.fail(str(error))


class AssetCheckerTests(unittest.TestCase):
    def test_source_static_tree_is_complete_and_integrity_checked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "static"
            _copy_static_without_caches(root)
            report = check_static_root(root)
            self.assertEqual(set(report.names), set(_manifest()))
            self.assertEqual(len(report.asset_hashes), len(report.names))

    def test_checker_accepts_only_python_runtime_cache_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "static"
            _copy_static_without_caches(root)
            cache = root / "__pycache__"
            cache.mkdir()
            (cache / "generated.cpython-311.pyc").write_bytes(b"runtime cache")
            check_static_root(root)

    def test_checker_rejects_nested_or_non_pyc_cache_contents(self) -> None:
        cases = {
            "nested cache content": (Path("nested") / "evil.js", b"not a runtime cache"),
            "direct non-pyc cache content": (Path("evil.js"), b"not a runtime cache"),
        }
        for label, (relative, body) in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "static"
                _copy_static_without_caches(root)
                cache_file = root / "__pycache__" / relative
                cache_file.parent.mkdir(parents=True)
                cache_file.write_bytes(body)
                with self.assertRaisesRegex(AssetCheckError, "undeclared"):
                    check_static_root(root)

    def test_checker_rejects_stale_files_and_digest_mismatches(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "static"
            _copy_static_without_caches(root)
            (root / "stale.js").write_bytes(b"stale")
            with self.assertRaisesRegex(AssetCheckError, "undeclared"):
                check_static_root(root)
            (root / "stale.js").unlink()
            (root / "node_modules").mkdir()
            with self.assertRaisesRegex(AssetCheckError, "forbidden directory"):
                check_static_root(root)
            (root / "node_modules").rmdir()
            (root / "NOTICE.txt").write_bytes(b"changed")
            with self.assertRaisesRegex(AssetCheckError, "SHA-256"):
                check_static_root(root)

    def test_checker_rejects_generated_cache_and_install_directories(self) -> None:
        for directory_name in (
            ".cache",
            ".pytest_cache",
            ".tmp",
            "build",
            "dist",
            "npm-cache",
            "node_modules",
            ".npm",
            "playwright-report",
            "playwright-reports",
            "playwright-cache",
            ".playwright",
            "test-results",
        ):
            with self.subTest(directory_name=directory_name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "static"
                _copy_static_without_caches(root)
                (root / directory_name).mkdir()
                with self.assertRaisesRegex(AssetCheckError, "forbidden directory"):
                    check_static_root(root)

    def test_checker_rejects_symlinked_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "static"
            _copy_static_without_caches(root)
            (root / "escape.js").symlink_to(STATIC / "app.js")
            with self.assertRaisesRegex(AssetCheckError, "symlink"):
                check_static_root(root)

    def test_checker_rejects_symlinked_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target"
            _copy_static_without_caches(target)
            root = Path(directory) / "static"
            root.symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(AssetCheckError, "root"):
                check_static_root(root)

    def test_content_scans_reject_each_forbidden_class(self) -> None:
        cases = {
            "absolute checkout path": b'const source = "/Users/lance/project/src/app.ts";',
            "absolute temp path": b'const source = "/private/var/folders/x/source";',
            "absolute file URL": b'const source = "file:///Users/lance/project/src/app.ts";',
            "private key": b"-----BEGIN RSA PRIVATE KEY-----",
            "token": b'const token = "ghp_12345678901234567890";',
            "secret": b'api_key="1234567890123456";',
            "FETCH_ONLY": b"FETCH_ONLY",
            "external URL": b'const endpoint = "https://attacker.example/api";',
            "external network target": (
                b'fetch("https://github.com/microsoft/monaco-editor#faq");'
            ),
        }
        for label, body in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(AssetCheckError):
                    scan_text("app.js", body)

    def test_content_scan_rejects_allowlisted_urls_in_network_invocations(self) -> None:
        allowed = "https://github.com/microsoft/monaco-editor#faq"
        cases = {
            "fetch call": f'fetch("{allowed}")',
            "fetch apply": f'fetch.apply(null, ["{allowed}"])',
            "fetch bind": f'fetch.bind(null, "{allowed}")',
            "globalThis fetch": f'globalThis.fetch("{allowed}")',
            "window fetch": f'window.fetch("{allowed}")',
            "XMLHttpRequest open": f'new XMLHttpRequest().open("GET", "{allowed}")',
            "WebSocket": f'new WebSocket("{allowed}")',
            "EventSource": f'new EventSource("{allowed}")',
            "importScripts": f'importScripts("{allowed}")',
            "sendBeacon": f'navigator.sendBeacon("{allowed}")',
            "new URL": f'new URL("{allowed}")',
            "dynamic import": f'import("{allowed}")',
            "static import": f'import "{allowed}"',
            "function alias": f'const request = fetch; request("{allowed}")',
            "aliased XMLHttpRequest open": (
                f'const open = XMLHttpRequest.prototype.open; '
                f'open.call(xhr, "GET", "{allowed}")'
            ),
        }
        for label, source in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(AssetCheckError):
                    scan_text("app.js", source.encode())

    def test_content_scan_preserves_required_license_and_diagnostic_urls(self) -> None:
        scan_text(
            "NOTICE.txt",
            (
                b"Copyright notice: "
                b"https://github.com/puppeteer/puppeteer/blob/master/LICENSE\n"
            ),
        )
        scan_text(
            "app.js",
            b'const namespace = "http://www.w3.org/2000/svg";',
        )
        scan_text(
            "app.js",
            b'const license = "http://mozilla.org/MPL/2.0/";',
        )

    def test_content_scan_rejects_allowlisted_license_url_as_network_target(self) -> None:
        with self.assertRaisesRegex(AssetCheckError, "external network target"):
            scan_text(
                "app.js",
                b'globalThis["fetch"]("http://mozilla.org/MPL/2.0/");',
            )

    def test_runtime_notice_boundary_rejects_a_missing_bundled_package_notice(self) -> None:
        notice = (STATIC / "NOTICE.txt").read_bytes()
        incomplete = notice.replace(
            b"===== marked@14.0.0 :: LICENSE.md =====",
            b"===== omitted marked notice =====",
        )
        with self.assertRaisesRegex(AssetCheckError, "marked/LICENSE.md"):
            _check_runtime_notice_boundary(incomplete)

    def test_runtime_notice_boundary_rejects_every_locked_mapping_mutation(self) -> None:
        for package, records in REQUIRED_RUNTIME_NOTICE_MAPPING["packages"].items():
            for index, _record in enumerate(records):
                for field in ("source", "snapshot"):
                    with self.subTest(package=package, index=index, field=field):
                        with tempfile.TemporaryDirectory(
                            prefix="codesignal-notices-"
                        ) as directory:
                            root = Path(directory)
                            licenses = root / "webui" / "LICENSES"
                            shutil.copytree(WEBUI / "LICENSES", licenses)
                            shutil.copy2(
                                WEBUI / "package-lock.json",
                                root / "webui" / "package-lock.json",
                            )
                            specification = json.loads(
                                (licenses / "runtime-notices.json").read_text()
                            )
                            specification["packages"][package][index][field] += ".changed"
                            (licenses / "runtime-notices.json").write_text(
                                json.dumps(specification),
                                encoding="utf-8",
                            )
                            with patch.object(check_assets, "PROJECT_ROOT", root):
                                with self.assertRaisesRegex(
                                    AssetCheckError,
                                    "locked runtime mapping",
                                ):
                                    _check_runtime_notice_boundary(b"")

    def test_runtime_notice_boundary_rejects_joint_snapshot_and_notice_mutation(self) -> None:
        notice = (STATIC / "NOTICE.txt").read_bytes()
        snapshot_names = [
            item["snapshot"]
            for records in REQUIRED_RUNTIME_NOTICE_MAPPING["packages"].values()
            for item in records
        ]
        for snapshot_name in snapshot_names:
            with self.subTest(snapshot=snapshot_name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                licenses = root / "webui" / "LICENSES"
                shutil.copytree(WEBUI / "LICENSES", licenses)
                shutil.copy2(
                    WEBUI / "package-lock.json",
                    root / "webui" / "package-lock.json",
                )
                original = (licenses / snapshot_name).read_bytes()
                mutated = original.rstrip() + b"\nJOINTLY MUTATED\n"
                (licenses / snapshot_name).write_bytes(mutated)
                mutated_notice = notice.replace(
                    original.rstrip(),
                    mutated.rstrip(),
                    1,
                )
                with patch.object(check_assets, "PROJECT_ROOT", root):
                    with self.assertRaisesRegex(AssetCheckError, "snapshot hash"):
                        _check_runtime_notice_boundary(mutated_notice)

    def test_runtime_notice_boundary_rejects_each_generated_section_mutation(self) -> None:
        notice = (STATIC / "NOTICE.txt").read_bytes()
        headings = re.findall(rb"^===== [^\n]+ =====$", notice, re.MULTILINE)
        self.assertEqual(len(headings), 5)
        for heading in headings:
            with self.subTest(heading=heading):
                mutated = notice.replace(heading, b"===== changed runtime section =====", 1)
                with self.assertRaises(AssetCheckError):
                    _check_runtime_notice_boundary(mutated)


class ReproducibleBuildTests(unittest.TestCase):
    def _build(
        self,
        output: Path,
        *,
        extra_environment: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        npm = shutil.which("npm")
        if npm is None:
            self.skipTest("npm is required for publication tests")
        environment = os.environ.copy()
        environment["ASSET_OUTPUT_DIR"] = str(output)
        if extra_environment:
            environment.update(extra_environment)
        return _run([npm, "run", "build"], cwd=WEBUI, env=environment)

    def _recover(self, output: Path) -> subprocess.CompletedProcess[str]:
        npm = shutil.which("npm")
        if npm is None:
            self.skipTest("npm is required for publication tests")
        environment = os.environ.copy()
        environment["ASSET_OUTPUT_DIR"] = str(output)
        return _run([npm, "run", "recover"], cwd=WEBUI, env=environment)

    def test_recover_only_recovers_every_durable_publication_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory(prefix="codesignal-publication-") as directory:
            output = Path(directory) / "static"
            self.assertEqual(self._build(output).returncode, 0)
            marker = output.parent / ".static.publish.json"
            lock = output.parent / ".static.publish.lock"
            backup = output.parent / ".static.previous"
            for checkpoint in (
                "after-durable-stage",
                "after-marker-prepared",
                "after-old-moved",
                "after-live-rename",
            ):
                with self.subTest(checkpoint=checkpoint):
                    crashed = self._build(
                        output,
                        extra_environment={"ASSET_PUBLISH_CRASH_AT": checkpoint},
                    )
                    self.assertEqual(crashed.returncode, 91, crashed.stderr)
                    self.assertEqual(
                        marker.exists(),
                        checkpoint != "after-durable-stage",
                    )
                    recovered = self._recover(output)
                    self.assertEqual(recovered.returncode, 0, recovered.stderr)
                    check_static_root(output)
                    self.assertFalse(marker.exists())
                    self.assertFalse(lock.exists())
                    self.assertFalse(backup.exists())
                    self.assertEqual(
                        list(output.parent.glob(".static.stage-*")),
                        [],
                    )

    def test_publication_recovers_malformed_marker_and_stale_lock(self) -> None:
        with tempfile.TemporaryDirectory(prefix="codesignal-publication-") as directory:
            output = Path(directory) / "static"
            self.assertEqual(self._build(output).returncode, 0)
            marker = output.parent / ".static.publish.json"
            lock = output.parent / ".static.publish.lock"
            marker.write_text("{malformed", encoding="utf-8")
            lock.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "kind": "build",
                        "pid": 2_147_483_647,
                        "created_at": time.time(),
                        "token": "stale-owner",
                    }
                ),
                encoding="utf-8",
            )
            recovered = self._build(output)
            self.assertEqual(recovered.returncode, 0, recovered.stderr)
            check_static_root(output)
            self.assertFalse(marker.exists())
            self.assertFalse(lock.exists())

    def test_recovery_restores_valid_backup_over_invalid_live(self) -> None:
        with tempfile.TemporaryDirectory(prefix="codesignal-publication-") as directory:
            output = Path(directory) / "static"
            self.assertEqual(self._build(output).returncode, 0)
            crashed = self._build(
                output,
                extra_environment={"ASSET_PUBLISH_CRASH_AT": "after-old-moved"},
            )
            self.assertEqual(crashed.returncode, 91, crashed.stderr)
            marker = output.parent / ".static.publish.json"
            transaction = json.loads(marker.read_text())
            stage = Path(transaction["stage"])
            output.mkdir()
            (output / "manifest.json").write_text("{}", encoding="utf-8")
            (stage / "manifest.json").write_text("{}", encoding="utf-8")
            recovered = self._recover(output)
            self.assertEqual(recovered.returncode, 0, recovered.stderr)
            check_static_root(output)
            self.assertFalse(marker.exists())

    def test_recovery_prefers_valid_backup_over_bad_self_metadata_stage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="codesignal-publication-") as directory:
            output = Path(directory) / "static"
            self.assertEqual(self._build(output).returncode, 0)
            crashed = self._build(
                output,
                extra_environment={"ASSET_PUBLISH_CRASH_AT": "after-old-moved"},
            )
            self.assertEqual(crashed.returncode, 91, crashed.stderr)
            marker = output.parent / ".static.publish.json"
            transaction = json.loads(marker.read_text())
            stage = Path(transaction["stage"])
            stage_manifest = json.loads((stage / "manifest.json").read_text())
            stage_manifest["manifest.json"]["media_type"] = "text/plain; charset=utf-8"
            (stage / "manifest.json").write_text(
                json.dumps(stage_manifest),
                encoding="utf-8",
            )
            expected = (Path(transaction["backup"]) / "index.html").read_bytes()
            recovered = self._recover(output)
            self.assertEqual(recovered.returncode, 0, recovered.stderr)
            check_static_root(output)
            self.assertEqual((output / "index.html").read_bytes(), expected)

    def test_recovery_prefers_valid_backup_over_stage_missing_required_asset(self) -> None:
        with tempfile.TemporaryDirectory(prefix="codesignal-publication-") as directory:
            output = Path(directory) / "static"
            self.assertEqual(self._build(output).returncode, 0)
            crashed = self._build(
                output,
                extra_environment={"ASSET_PUBLISH_CRASH_AT": "after-old-moved"},
            )
            self.assertEqual(crashed.returncode, 91, crashed.stderr)
            marker = output.parent / ".static.publish.json"
            transaction = json.loads(marker.read_text())
            stage = Path(transaction["stage"])
            (stage / "favicon.svg").unlink()
            expected = (Path(transaction["backup"]) / "index.html").read_bytes()
            recovered = self._recover(output)
            self.assertEqual(recovered.returncode, 0, recovered.stderr)
            check_static_root(output)
            self.assertEqual((output / "index.html").read_bytes(), expected)

    def test_recover_only_promotes_one_valid_orphan_over_invalid_live(self) -> None:
        with tempfile.TemporaryDirectory(prefix="codesignal-publication-") as directory:
            output = Path(directory) / "static"
            self.assertEqual(self._build(output).returncode, 0)
            expected_index = (output / "index.html").read_bytes()
            stage = output.parent / ".static.stage-orphan"
            shutil.copytree(output, stage)
            (output / "manifest.json").write_text("{}", encoding="utf-8")

            recovered = self._recover(output)

            self.assertEqual(recovered.returncode, 0, recovered.stderr)
            check_static_root(output)
            self.assertEqual((output / "index.html").read_bytes(), expected_index)
            self.assertFalse(stage.exists())

    def test_publication_rejects_symlinked_parent_without_writing_through_it(self) -> None:
        with tempfile.TemporaryDirectory(prefix="codesignal-publication-") as directory:
            root = Path(directory)
            real_parent = root / "real-parent"
            real_parent.mkdir()
            sentinel = real_parent / "sentinel"
            sentinel.write_text("preserve", encoding="utf-8")
            linked_parent = root / "linked-parent"
            try:
                linked_parent.symlink_to(real_parent, target_is_directory=True)
            except (NotImplementedError, OSError):
                self.skipTest("directory symlinks are unavailable on this platform")

            output = linked_parent / "static"
            built = self._build(output)

            self.assertNotEqual(built.returncode, 0)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve")
            self.assertEqual(tuple(real_parent.iterdir()), (sentinel,))

    def test_publication_rejects_immediate_and_nested_symlink_ancestors(self) -> None:
        for depth in (1, 2):
            with self.subTest(depth=depth), tempfile.TemporaryDirectory(
                prefix="codesignal-publication-"
            ) as directory:
                root = Path(directory)
                target = root / "target"
                target.mkdir()
                sentinel = target / "sentinel"
                sentinel.write_text("preserve", encoding="utf-8")
                if depth == 1:
                    linked_output = root / "linked"
                    output = linked_output / "static"
                else:
                    safe_parent = root / "safe"
                    safe_parent.mkdir()
                    linked_output = safe_parent / "linked"
                    output = linked_output / "nested" / "static"
                try:
                    linked_output.symlink_to(target, target_is_directory=True)
                except (NotImplementedError, OSError):
                    self.skipTest("directory symlinks are unavailable on this platform")
                before = _tree_bytes(target)
                built = self._build(output)
                self.assertNotEqual(built.returncode, 0, built.stderr)
                self.assertEqual(_tree_bytes(target), before)
                self.assertEqual(
                    {
                        path.name
                        for path in root.rglob("*")
                        if path.name.startswith(".static.")
                    },
                    set(),
                )

    def test_recovery_fails_closed_when_no_generation_is_valid(self) -> None:
        with tempfile.TemporaryDirectory(prefix="codesignal-publication-") as directory:
            output = Path(directory) / "static"
            self.assertEqual(self._build(output).returncode, 0)
            crashed = self._build(
                output,
                extra_environment={"ASSET_PUBLISH_CRASH_AT": "after-old-moved"},
            )
            self.assertEqual(crashed.returncode, 91, crashed.stderr)
            marker = output.parent / ".static.publish.json"
            transaction = json.loads(marker.read_text())
            stage = Path(transaction["stage"])
            (Path(transaction["backup"]) / "manifest.json").write_text(
                "{}", encoding="utf-8"
            )
            (stage / "manifest.json").write_text("{}", encoding="utf-8")
            recovered = self._recover(output)
            self.assertNotEqual(recovered.returncode, 0)
            self.assertTrue(marker.exists())
            self.assertTrue(Path(transaction["backup"]).exists())
            self.assertTrue(stage.exists())

    def test_recovery_rejects_external_stage_path_without_touching_it(self) -> None:
        with tempfile.TemporaryDirectory(prefix="codesignal-publication-") as directory:
            root = Path(directory)
            output = root / "static"
            self.assertEqual(self._build(output).returncode, 0)
            external = root / "external-stage"
            external.mkdir()
            (external / "sentinel").write_text("preserve", encoding="utf-8")
            marker = output.parent / ".static.publish.json"
            marker.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "backup": str(output.parent / ".static.previous"),
                        "stage": str(external / ".." / "external-stage"),
                        "phase": "prepared",
                    }
                ),
                encoding="utf-8",
            )
            recovered = self._recover(output)
            self.assertEqual(recovered.returncode, 0, recovered.stderr)
            self.assertEqual((external / "sentinel").read_text(), "preserve")
            check_static_root(output)

    def test_multiple_concurrent_builds_wait_and_complete_serially(self) -> None:
        with tempfile.TemporaryDirectory(prefix="codesignal-publication-") as directory:
            output = Path(directory) / "static"
            self.assertEqual(self._build(output).returncode, 0)
            npm = shutil.which("npm")
            assert npm is not None
            environment = os.environ.copy()
            environment.update(
                {
                    "ASSET_OUTPUT_DIR": str(output),
                    "ASSET_PUBLISH_HOLD_LOCK_MS": "1500",
                }
            )
            first = subprocess.Popen(
                [npm, "run", "build"],
                cwd=WEBUI,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            lock = output.parent / ".static.publish.lock"
            try:
                deadline = time.monotonic() + 10
                while not lock.exists() and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue(lock.exists(), "first build never acquired lock")
                waiters = [
                    subprocess.Popen(
                        [npm, "run", "build"],
                        cwd=WEBUI,
                        env=environment,
                        text=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    for _ in range(2)
                ]
                started = time.monotonic()
                results = [process.communicate(timeout=20) for process in waiters]
                self.assertTrue(
                    all(process.returncode == 0 for process in waiters),
                    results,
                )
                self.assertGreaterEqual(time.monotonic() - started, 1.0)
                check_static_root(output)
                self.assertFalse(
                    (output.parent / ".static.publish.lock.reclaimer").exists()
                )
            finally:
                stdout, stderr = first.communicate(timeout=20)
                self.assertEqual(first.returncode, 0, stdout + stderr)

    def test_builder_waits_for_python_reader(self) -> None:
        from codesignal_practice_simulator.web import resources

        with tempfile.TemporaryDirectory(prefix="codesignal-publication-") as directory:
            output = Path(directory) / "static"
            self.assertEqual(self._build(output).returncode, 0)
            npm = shutil.which("npm")
            assert npm is not None
            environment = os.environ.copy()
            environment["ASSET_OUTPUT_DIR"] = str(output)
            with patch.object(resources, "_resource_root", return_value=output):
                with resources._publication_reader_lock(output):
                    process = subprocess.Popen(
                        [npm, "run", "build"],
                        cwd=WEBUI,
                        env=environment,
                        text=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    time.sleep(0.4)
                    self.assertIsNone(process.poll())
                stdout, stderr = process.communicate(timeout=20)
            self.assertEqual(process.returncode, 0, stdout + stderr)
            check_static_root(output)

    def test_reader_waits_for_live_swap_and_reads_a_complete_generation(self) -> None:
        from codesignal_practice_simulator.web.resources import read_asset

        static_module = importlib.import_module(
            "codesignal_practice_simulator.web.static"
        )
        marker = (
            STATIC.parent / ".static.publish.json"
        )
        lock = STATIC.parent / ".static.publish.lock"
        build = self._build(
            STATIC,
            extra_environment={"ASSET_PUBLISH_HOLD_LOCK_MS": "1200"},
        )
        self.assertEqual(build.returncode, 0, build.stderr)
        npm = shutil.which("npm")
        assert npm is not None
        environment = os.environ.copy()
        environment.update(
            {
                "ASSET_PUBLISH_HOLD_LOCK_MS": "1200",
                "ASSET_OUTPUT_DIR": str(STATIC),
            }
        )
        process = subprocess.Popen(
            [npm, "run", "build"],
            cwd=WEBUI,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            deadline = time.monotonic() + 10
            while (
                (not marker.exists() or "old-moved" not in marker.read_text())
                and time.monotonic() < deadline
            ):
                time.sleep(0.02)
            self.assertTrue(marker.exists())
            sys.modules.pop("codesignal_practice_simulator.web.static", None)
            try:
                started = time.monotonic()
                asset = read_asset("index.html")
                elapsed = time.monotonic() - started
                self.assertGreater(elapsed, 0.2)
                self.assertIn(b"Practice Simulator", asset.body)
            finally:
                sys.modules["codesignal_practice_simulator.web.static"] = static_module
        finally:
            stdout, stderr = process.communicate(timeout=20)
            self.assertEqual(process.returncode, 0, stdout + stderr)
            self.assertFalse(marker.exists())
            self.assertFalse(lock.exists())

    def test_two_clean_lockfile_builds_have_identical_outputs(self) -> None:
        npm = shutil.which("npm")
        if npm is None:
            self.skipTest("npm is required for the clean build check")
        with tempfile.TemporaryDirectory(prefix="codesignal-assets-") as directory:
            root = Path(directory)
            npm_cache = root / "npm-cache"
            outputs: list[dict[str, bytes]] = []
            for index in (1, 2):
                checkout = root / f"checkout-{index}"
                shutil.copytree(
                    PROJECT / "webui",
                    checkout,
                    ignore=shutil.ignore_patterns(
                        "node_modules",
                        ".tmp",
                        ".cache",
                        "playwright-report",
                        "test-results",
                    ),
                )
                output = root / f"static-{index}"
                environment = os.environ.copy()
                environment.update(
                    {
                        "ASSET_OUTPUT_DIR": str(output),
                        "npm_config_cache": str(npm_cache),
                    }
                )
                installed = _run(
                    [npm, "ci", "--ignore-scripts", "--no-audit", "--no-fund"],
                    cwd=checkout,
                    env=environment,
                )
                self.assertEqual(installed.returncode, 0, installed.stderr)
                built = _run(
                    [npm, "run", "build"],
                    cwd=checkout,
                    env=environment,
                )
                self.assertEqual(built.returncode, 0, built.stderr)
                check_static_root(output)
                outputs.append(_tree_bytes(output))
            self.assertEqual(outputs[0], outputs[1])


class DistributionTests(unittest.TestCase):
    def test_built_archives_contain_only_valid_packaged_assets(self) -> None:
        builder = discover_packaging_interpreter(require_build=True)
        if builder is None:
            self.skipTest("no interpreter with importable build is installed")
        with tempfile.TemporaryDirectory(prefix="codesignal-package-") as directory:
            root = Path(directory)
            checkout = root / "checkout"
            checkout.mkdir()
            shutil.copy2(PROJECT / "pyproject.toml", checkout / "pyproject.toml")
            shutil.copy2(PROJECT / "README.md", checkout / "README.md")
            shutil.copytree(
                PROJECT / "src",
                checkout / "src",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            dist = root / "dist"
            built = _run(
                [
                    builder,
                    "-m",
                    "build",
                    "--sdist",
                    "--wheel",
                    "--no-isolation",
                    "--outdir",
                    str(dist),
                ],
                cwd=checkout,
            )
            self.assertEqual(built.returncode, 0, built.stderr)
            wheel = next(dist.glob("*.whl"))
            source = next(dist.glob("*.tar.gz"))
            expected = _packaged_static_bytes()
            with zipfile.ZipFile(wheel) as archive:
                members = archive.namelist()
                self.assertEqual(len(members), len(set(members)))
                _assert_archive_is_clean(self, members)
                packaged = _static_members(members)
                self.assertEqual(packaged, set(expected))
                for name, body in expected.items():
                    packaged_body = archive.read(
                        f"codesignal_practice_simulator/web/static/{name}"
                    )
                    self.assertEqual(packaged_body, body, name)
                    _assert_clean_asset_bytes(self, name, packaged_body)
            with tarfile.open(source, "r:gz") as archive:
                members = archive.getnames()
                self.assertEqual(len(members), len(set(members)))
                _assert_archive_is_clean(self, members)
                static_members = {
                    member.split(
                        "/src/codesignal_practice_simulator/web/static/", 1
                    )[1]
                    for member in members
                    if "/src/codesignal_practice_simulator/web/static/" in member
                    and not member.endswith("/")
                }
                self.assertEqual(static_members, set(expected))
                for member in archive.getmembers():
                    if not member.isfile():
                        continue
                    if "/src/codesignal_practice_simulator/web/static/" not in member.name:
                        continue
                    contents = archive.extractfile(member).read()
                    name = member.name.split(
                        "/src/codesignal_practice_simulator/web/static/", 1
                    )[1]
                    self.assertEqual(contents, expected[name], name)
                    _assert_clean_asset_bytes(self, member.name, contents)

    def test_archive_path_policy_rejects_every_forbidden_class(self) -> None:
        for part in sorted(ARCHIVE_FORBIDDEN_PARTS):
            with self.subTest(part=part):
                with self.assertRaises(AssetCheckError):
                    _reject_forbidden_archive_paths([f"package/{part}/asset.js"])

    def test_installed_wheel_reads_exact_static_bytes_outside_checkout(self) -> None:
        wheel_builder = discover_packaging_interpreter()
        if wheel_builder is None:
            self.skipTest("a Python interpreter with setuptools is required")
        with tempfile.TemporaryDirectory(prefix="codesignal-wheel-") as directory:
            root = Path(directory)
            wheel_directory = root / "wheel"
            built = _run(
                [
                    wheel_builder,
                    "-m",
                    "pip",
                    "wheel",
                    "--no-deps",
                    "--no-build-isolation",
                    "--wheel-dir",
                    str(wheel_directory),
                    str(PROJECT),
                ],
                cwd=root,
            )
            self.assertEqual(built.returncode, 0, built.stderr)
            wheel = next(wheel_directory.glob("*.whl"))
            environment = root / "environment"
            created = _run([wheel_builder, "-m", "venv", str(environment)], cwd=root)
            self.assertEqual(created.returncode, 0, created.stderr)
            executable_dir = environment / ("Scripts" if os.name == "nt" else "bin")
            environment_python = executable_dir / (
                "python.exe" if os.name == "nt" else "python"
            )
            environment_pip = executable_dir / (
                "pip.exe" if os.name == "nt" else "pip"
            )
            installed = _run(
                [
                    str(environment_pip),
                    "install",
                    "--no-deps",
                    str(wheel),
                ],
                cwd=root,
            )
            self.assertEqual(installed.returncode, 0, installed.stderr)
            clean_environment = os.environ.copy()
            clean_environment.pop("PYTHONPATH", None)
            clean_environment["ASSET_SOURCE_ROOT"] = str(PROJECT)
            clean_environment["EXPECTED_MANIFEST"] = json.dumps(_manifest())
            expected_hashes = {
                name: record["sha256"]
                for name, record in _manifest().items()
                if "sha256" in record
            }
            expected_hashes["manifest.json"] = hashlib.sha256(
                (STATIC / "manifest.json").read_bytes()
            ).hexdigest()
            clean_environment["EXPECTED_HASHES"] = json.dumps(expected_hashes)
            probe = _run(
                [
                    str(environment_python),
                    "-c",
                    (
                        "import hashlib, importlib, json, os, sys; "
                        "from pathlib import Path; "
                        "import codesignal_practice_simulator as package; "
                        "from codesignal_practice_simulator.web import resources; "
                        "from codesignal_practice_simulator.web.resources import "
                        "STATIC_PACKAGE, asset_names, read_asset; "
                        "expected = json.loads(os.environ['EXPECTED_MANIFEST']); "
                        "names = asset_names(); "
                        "assert set(names) == set(expected), (names, expected); "
                        "hashes = {name: hashlib.sha256(read_asset(name).body).hexdigest() "
                        "for name in names}; "
                        "expected_hashes = json.loads(os.environ['EXPECTED_HASHES']); "
                        "assert hashes == expected_hashes, (hashes, expected_hashes); "
                        "prefix = Path(sys.prefix).resolve(); "
                        "source = Path(os.environ['ASSET_SOURCE_ROOT']).resolve(); "
                        "origins = [Path(package.__file__).resolve(), "
                        "Path(resources.__file__).resolve(), "
                        "Path(importlib.import_module(STATIC_PACKAGE).__file__).resolve()]; "
                        "assert all(origin.is_relative_to(prefix) for origin in origins), origins; "
                        "assert all(not origin.is_relative_to(source) for origin in origins), origins; "
                        "print(json.dumps({'names': sorted(names), 'hashes': hashes, "
                        "'origins': [str(origin) for origin in origins]}, sort_keys=True))"
                    ),
                ],
                cwd=root,
                env=clean_environment,
            )
            self.assertEqual(probe.returncode, 0, probe.stderr)
            installed = json.loads(probe.stdout)
            self.assertEqual(set(installed["names"]), set(_manifest()))
            self.assertEqual(installed["hashes"], expected_hashes)
            self.assertTrue(
                all(
                    Path(origin).is_relative_to(environment.resolve())
                    and not Path(origin).is_relative_to(PROJECT)
                    for origin in installed["origins"]
                ),
                installed["origins"],
            )


if __name__ == "__main__":
    unittest.main()
