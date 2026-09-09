"""Deterministic tests for the fetch-only fixture and Git boundary."""

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
from unittest.mock import Mock, patch


PROJECT = Path(__file__).resolve().parents[1]
SCRIPTS = PROJECT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from fetch_fixture import populate_fixture  # noqa: E402
from fixture_contract import FixtureError, fixture_cache_path, read_manifest  # noqa: E402
import scorecard  # noqa: E402
from verify_manifest import (  # noqa: E402
    verify_fixture_cache,
    verify_git_boundary,
    verify_tracked,
)


FETCH_PATHS = (
    ("README.md", "Readme.md", "vendor-readme.md"),
    (
        "practice_assessments/file_storage/level1.md",
        "practice_assessments/file_storage/level1.md",
        "assessment/file_storage/level1.md",
    ),
    (
        "practice_assessments/file_storage/level2.md",
        "practice_assessments/file_storage/level2.md",
        "assessment/file_storage/level2.md",
    ),
    (
        "practice_assessments/file_storage/level3.md",
        "practice_assessments/file_storage/level3.md",
        "assessment/file_storage/level3.md",
    ),
    (
        "practice_assessments/file_storage/level4.md",
        "practice_assessments/file_storage/level4.md",
        "assessment/file_storage/level4.md",
    ),
    (
        "practice_assessments/file_storage/simulation.py",
        "practice_assessments/file_storage/simulation.py",
        "assessment/file_storage/simulation.py",
    ),
    (
        "practice_assessments/file_storage/test_simulation.py",
        "practice_assessments/file_storage/test_simulation.py",
        "assessment/file_storage/test_simulation.py",
    ),
)


def synthetic_bytes(upstream_path: str) -> bytes:
    """Return non-vendor data with a deterministic unique digest."""
    return f"synthetic fixture for {upstream_path}\n".encode()


def write_test_manifest(project: Path) -> Path:
    """Create a valid contract manifest whose expected bytes are synthetic."""
    fetches = []
    files = []
    for upstream_path, repository_path, cache_path in FETCH_PATHS:
        digest = hashlib.sha256(synthetic_bytes(upstream_path)).hexdigest()
        fetches.append(
            {
                "upstream_path": upstream_path,
                "repository_path": repository_path,
                "cache_path": cache_path,
                "sha256": digest,
            }
        )
        files.append(
            {
                "source_path": f"synthetic/{cache_path}",
                "sha256": digest,
                "classification": "vendor",
                "decision": "exclude",
                "destination_path": None,
                "cache_path": cache_path,
            }
        )
    files.append(
        {
            "source_path": "notes/example.md",
            "sha256": hashlib.sha256(b"notes\n").hexdigest(),
            "classification": "user_authored",
            "decision": "include",
            "destination_path": "docs/example.md",
            "cache_path": None,
        }
    )
    manifest = {
        "schema_version": 2,
        "upstream": {
            "repository": "PaulLockett/CodeSignal_Practice_Industry_Coding_Framework",
            "commit": "6aab304",
        },
        "license": {"licenseInfo": None, "license_endpoint_status": 404},
        "license_decision": "FETCH_ONLY",
        "fixture_cache_root": ".cache/codesignal-fixtures/6aab304",
        "files": files,
        "fetches": fetches,
    }
    path = project / "docs" / "migration-manifest.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def write_complete_source(root: Path) -> None:
    """Write the exact offline source tree expected by the fetcher."""
    for upstream_path, _repository_path, _cache_path in FETCH_PATHS:
        path = root.joinpath(*upstream_path.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(synthetic_bytes(upstream_path))


def hermetic_subprocess_environment(root: Path) -> dict[str, str]:
    """Isolate temporary repositories from host Git and Python configuration."""
    home = root / "home"
    home.mkdir(exist_ok=True)
    environment = os.environ.copy()
    for name in tuple(environment):
        if name.startswith(("GIT_", "PYTHON")):
            environment.pop(name)
    environment.update(
        {
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(root / "xdg-config"),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    return environment


def git(repository: Path, *arguments: str) -> None:
    """Run Git deterministically in a temporary repository."""
    subprocess.run(
        ("git", "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
        env=hermetic_subprocess_environment(repository.parent),
    )


def initialize_repository(root: Path) -> tuple[Path, Path]:
    """Initialize a temporary Git repository with a safe initial commit."""
    repository = root / "repository"
    repository.mkdir()
    git(repository, "init", "--quiet")
    git(repository, "config", "user.email", "tests@example.invalid")
    git(repository, "config", "user.name", "Fixture Tests")
    manifest_path = write_test_manifest(repository)
    (repository / "safe.txt").write_text("safe\n", encoding="utf-8")
    git(repository, "add", "safe.txt")
    git(repository, "commit", "--quiet", "-m", "safe initial state")
    return repository, manifest_path


def install_git_boundary_hooks(repository: Path) -> None:
    """Install the production wrappers with their local Python dependencies."""
    for relative in (
        ".githooks/pre-commit",
        ".githooks/pre-push",
        "scripts/fixture_contract.py",
        "scripts/verify_manifest.py",
    ):
        source = PROJECT / relative
        destination = repository / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    git(repository, "config", "core.hooksPath", ".githooks")


def git_result(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run Git without converting an expected hook rejection into an exception."""
    return subprocess.run(
        ("git", "-C", str(repository), *arguments),
        text=True,
        capture_output=True,
        check=False,
        env=hermetic_subprocess_environment(repository.parent),
    )


class FetchFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary_directory.name) / "project"
        self.project.mkdir()
        self.manifest_path = write_test_manifest(self.project)
        self.source = Path(self.temporary_directory.name) / "source"
        write_complete_source(self.source)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_complete_source_setup_includes_vendor_readme(self) -> None:
        cache_root = populate_fixture(self.manifest_path, self.source)

        self.assertEqual(
            (cache_root / "vendor-readme.md").read_bytes(),
            synthetic_bytes("README.md"),
        )
        manifest = read_manifest(self.manifest_path)
        verify_fixture_cache(self.manifest_path, manifest)

    def test_absent_cache_requires_setup(self) -> None:
        manifest = read_manifest(self.manifest_path)

        with self.assertRaisesRegex(FixtureError, "fixture cache is absent"):
            verify_fixture_cache(self.manifest_path, manifest)

    def test_incomplete_local_source_does_not_publish_cache(self) -> None:
        (self.source / "practice_assessments/file_storage/level4.md").unlink()

        with self.assertRaisesRegex(FixtureError, "missing regular file"):
            populate_fixture(self.manifest_path, self.source)

        manifest = read_manifest(self.manifest_path)
        self.assertFalse(fixture_cache_path(self.manifest_path, manifest).exists())

    def test_mocked_downloader_failure_does_not_publish_cache(self) -> None:
        fail_downloader = Mock(side_effect=FixtureError("simulated network failure"))

        with self.assertRaisesRegex(FixtureError, "simulated network failure"):
            populate_fixture(self.manifest_path, downloader=fail_downloader)

        manifest = read_manifest(self.manifest_path)
        self.assertFalse(fixture_cache_path(self.manifest_path, manifest).exists())
        fail_downloader.assert_called_once()

    def test_hash_mismatch_preserves_existing_cache(self) -> None:
        cache_root = populate_fixture(self.manifest_path, self.source)
        original_readme = (cache_root / "vendor-readme.md").read_bytes()
        (self.source / "README.md").write_bytes(b"not the expected synthetic bytes\n")

        with self.assertRaisesRegex(FixtureError, "hash mismatch"):
            populate_fixture(self.manifest_path, self.source)

        self.assertEqual((cache_root / "vendor-readme.md").read_bytes(), original_readme)

    def test_invalid_manifest_path_is_rejected(self) -> None:
        data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        data["fetches"][0]["cache_path"] = "../outside"
        self.manifest_path.write_text(json.dumps(data), encoding="utf-8")

        with self.assertRaisesRegex(FixtureError, "normalized relative path"):
            populate_fixture(self.manifest_path, self.source)


class ManifestVerifierTests(unittest.TestCase):
    def test_real_project_does_not_track_fixture_contents(self) -> None:
        manifest_path = PROJECT / "docs" / "migration-manifest.json"
        manifest = read_manifest(manifest_path)
        verify_tracked(manifest_path, manifest)

    def test_git_boundary_safe_control(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository, manifest_path = initialize_repository(Path(temporary_directory))
            verify_git_boundary(manifest_path, read_manifest(manifest_path))

    def test_git_boundary_rejects_staged_vendor_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository, manifest_path = initialize_repository(Path(temporary_directory))
            (repository / "copy.txt").write_bytes(synthetic_bytes("README.md"))
            git(repository, "add", "copy.txt")

            with self.assertRaisesRegex(FixtureError, "staged index: known vendor hash"):
                verify_git_boundary(manifest_path, read_manifest(manifest_path))

    def test_git_boundary_rejects_staged_vendor_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository, manifest_path = initialize_repository(Path(temporary_directory))
            forbidden = repository / "synthetic" / "assessment" / "file_storage"
            forbidden.mkdir(parents=True)
            (forbidden / "level1.md").write_text("different bytes\n", encoding="utf-8")
            git(repository, "add", "synthetic/assessment/file_storage/level1.md")

            with self.assertRaisesRegex(FixtureError, "forbidden vendor path"):
                verify_git_boundary(manifest_path, read_manifest(manifest_path))

    def test_git_boundary_rejects_head_vendor_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository, manifest_path = initialize_repository(Path(temporary_directory))
            (repository / "old-copy.txt").write_bytes(synthetic_bytes("README.md"))
            git(repository, "add", "old-copy.txt")
            git(repository, "commit", "--quiet", "-m", "bad historical copy")

            with self.assertRaisesRegex(FixtureError, "HEAD: known vendor hash"):
                verify_git_boundary(manifest_path, read_manifest(manifest_path))

    def test_git_boundary_rejects_head_vendor_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository, manifest_path = initialize_repository(Path(temporary_directory))
            forbidden = repository / "synthetic" / "assessment" / "file_storage"
            forbidden.mkdir(parents=True)
            (forbidden / "level1.md").write_text("different bytes\n", encoding="utf-8")
            git(repository, "add", "synthetic/assessment/file_storage/level1.md")
            git(repository, "commit", "--quiet", "-m", "bad historical path")

            with self.assertRaisesRegex(FixtureError, "HEAD: forbidden vendor path"):
                verify_git_boundary(manifest_path, read_manifest(manifest_path))

    def test_installed_pre_commit_hook_rejects_a_staged_vendor_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository, _manifest_path = initialize_repository(Path(temporary_directory))
            install_git_boundary_hooks(repository)

            safe = git_result(repository, "commit", "--allow-empty", "-m", "hook control")
            self.assertEqual(safe.returncode, 0, safe.stderr)

            (repository / "copy.txt").write_bytes(synthetic_bytes("README.md"))
            git(repository, "add", "copy.txt")
            rejected = git_result(repository, "commit", "-m", "known vendor hash")

            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn(
                "staged index: known vendor hash at copy.txt",
                rejected.stdout + rejected.stderr,
            )

    def test_hook_tests_ignore_inherited_global_git_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            hostile_global = root / "hostile.gitconfig"
            hostile_global.write_text("[commit]\n\tgpgSign = true\n", encoding="utf-8")
            with patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(hostile_global)}):
                repository, _manifest_path = initialize_repository(root)
                install_git_boundary_hooks(repository)

                committed = git_result(
                    repository, "commit", "--allow-empty", "-m", "hook control"
                )

            self.assertEqual(committed.returncode, 0, committed.stderr)

    def test_installed_pre_push_hook_rejects_a_head_vendor_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            repository, _manifest_path = initialize_repository(root)
            install_git_boundary_hooks(repository)
            remote = root / "remote.git"
            subprocess.run(
                ("git", "init", "--bare", "--quiet", str(remote)),
                check=True,
                capture_output=True,
                env=hermetic_subprocess_environment(root),
            )
            git(repository, "remote", "add", "origin", str(remote))

            safe = git_result(repository, "push", "--quiet", "-u", "origin", "HEAD")
            self.assertEqual(safe.returncode, 0, safe.stderr)

            forbidden = repository / "synthetic" / "assessment" / "file_storage"
            forbidden.mkdir(parents=True)
            (forbidden / "level1.md").write_text("different bytes\n", encoding="utf-8")
            git(repository, "add", "synthetic/assessment/file_storage/level1.md")
            git(repository, "commit", "--quiet", "--no-verify", "-m", "known vendor path")
            rejected = git_result(repository, "push", "--quiet", "origin", "HEAD")

            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn(
                "HEAD: forbidden vendor path synthetic/assessment/file_storage/level1.md",
                rejected.stdout + rejected.stderr,
            )


class ScorecardFixtureTests(unittest.TestCase):
    def test_solution_uses_cached_tests_with_solution_as_the_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            cached_tests = Path(temporary_directory)
            (cached_tests / "test_simulation.py").write_text("", encoding="utf-8")
            completed = subprocess.CompletedProcess((), 0, "", "")

            with (
                patch.object(scorecard, "SOLUTION_TESTS", cached_tests),
                patch.object(scorecard.subprocess, "run", return_value=completed) as run,
            ):
                self.assertEqual(
                    scorecard.resolve_target(str(scorecard.SOLUTION)),
                    scorecard.SOLUTION,
                )
                self.assertEqual(scorecard.run_level(scorecard.SOLUTION, 1), (True, ""))

        self.assertEqual(run.call_args.kwargs["cwd"], scorecard.SOLUTION)
        self.assertEqual(
            run.call_args.kwargs["env"]["PYTHONPATH"], str(cached_tests)
        )
        self.assertEqual(run.call_args.kwargs["env"]["PYTHONDONTWRITEBYTECODE"], "1")

    def test_attempt_uses_its_copied_tests(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            attempt = Path(temporary_directory).resolve()
            (attempt / "simulation.py").write_text("", encoding="utf-8")
            (attempt / "test_simulation.py").write_text("", encoding="utf-8")
            completed = subprocess.CompletedProcess((), 0, "", "")

            with patch.object(scorecard.subprocess, "run", return_value=completed) as run:
                self.assertEqual(scorecard.resolve_target(str(attempt)), attempt)
                self.assertEqual(scorecard.run_level(attempt, 1), (True, ""))

        self.assertEqual(run.call_args.kwargs["cwd"], attempt)
        self.assertIsNone(run.call_args.kwargs["env"])


if __name__ == "__main__":
    unittest.main()
