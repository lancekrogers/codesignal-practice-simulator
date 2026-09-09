#!/usr/bin/env python3
"""Verify fetch-only metadata, cache contents, and Git boundaries."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

from fixture_contract import (
    FIXTURE_CACHE_ROOT,
    FixtureError,
    fixture_cache_path,
    forbidden_vendor_paths,
    read_manifest,
    sha256_file,
    vendor_hashes,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the fetch-only fixture policy.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--scope",
        choices=("tracked", "fixture-cache", "git-boundary"),
        required=True,
    )
    return parser.parse_args()


def run_git(repository: Path, *arguments: str) -> bytes:
    """Run Git in a repository and convert command failures to FixtureError."""
    command = ("git", "-C", str(repository), *arguments)
    result = subprocess.run(command, capture_output=True)
    if result.returncode:
        message = result.stderr.decode(errors="replace").strip()
        raise FixtureError(f"Git command failed ({' '.join(command)}): {message}")
    return result.stdout


def repository_root(manifest_path: Path) -> Path:
    """Find the Git repository containing this manifest."""
    root = run_git(manifest_path.parent, "rev-parse", "--show-toplevel")
    return Path(root.decode().strip())


def is_forbidden_path(path: str, forbidden_paths: set[str]) -> bool:
    """Return whether path is a known vendor path or fixture-cache path."""
    return (
        path in forbidden_paths
        or path == FIXTURE_CACHE_ROOT
        or path.startswith(f"{FIXTURE_CACHE_ROOT}/")
    )


def verify_tracked(manifest_path: Path, manifest: dict) -> None:
    """Verify manifest mappings and reject tracked vendor destinations."""
    repository = repository_root(manifest_path)
    tracked_paths = {
        entry.decode()
        for entry in run_git(repository, "ls-files", "-z").split(b"\0")
        if entry
    }
    forbidden_paths = forbidden_vendor_paths(manifest)
    rejected = sorted(
        path for path in tracked_paths if is_forbidden_path(path, forbidden_paths)
    )
    if rejected:
        raise FixtureError(
            "tracked vendor paths are prohibited: " + ", ".join(rejected)
        )


def cache_files(cache_root: Path) -> set[str]:
    """List and validate all regular files under a fixture cache."""
    if not cache_root.is_dir():
        raise FixtureError(
            f"fixture cache is absent: {cache_root}. Run scripts/fetch_fixture.py first."
        )
    files = set()
    for path in cache_root.rglob("*"):
        if path.is_symlink():
            raise FixtureError(f"fixture cache must not contain symlinks: {path}")
        if path.is_file():
            files.add(path.relative_to(cache_root).as_posix())
    return files


def verify_fixture_cache(manifest_path: Path, manifest: dict) -> None:
    """Verify all and only declared cache files against their expected hashes."""
    cache_root = fixture_cache_path(manifest_path, manifest)
    expected = {record["cache_path"]: record["sha256"] for record in manifest["fetches"]}
    actual = cache_files(cache_root)
    if actual != set(expected):
        missing = sorted(set(expected) - actual)
        extra = sorted(actual - set(expected))
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if extra:
            details.append("unexpected " + ", ".join(extra))
        raise FixtureError("fixture cache has an invalid file set: " + "; ".join(details))

    for relative_path, expected_hash in expected.items():
        path = cache_root.joinpath(*relative_path.split("/"))
        actual_hash = sha256_file(path)
        if actual_hash != expected_hash:
            raise FixtureError(
                f"fixture cache hash mismatch for {relative_path}: "
                f"expected {expected_hash}, got {actual_hash}"
            )


def parse_index_entries(raw_entries: bytes) -> list[tuple[str, str]]:
    """Parse `git ls-files -s -z` output into (hash, path) pairs."""
    parsed = []
    for entry in raw_entries.split(b"\0"):
        if not entry:
            continue
        metadata, path = entry.split(b"\t", 1)
        _mode, blob_hash, _stage = metadata.decode().split()
        parsed.append((blob_hash, path.decode()))
    return parsed


def parse_head_entries(raw_entries: bytes) -> list[tuple[str, str]]:
    """Parse `git ls-tree -r -z HEAD` output into (hash, path) pairs."""
    parsed = []
    for entry in raw_entries.split(b"\0"):
        if not entry:
            continue
        metadata, path = entry.split(b"\t", 1)
        _mode, object_type, blob_hash = metadata.decode().split()
        if object_type == "blob":
            parsed.append((blob_hash, path.decode()))
    return parsed


def sha256_blob(repository: Path, blob_id: str) -> str:
    """Return the SHA-256 digest of Git blob content, not its Git object ID."""
    return hashlib.sha256(
        run_git(repository, "cat-file", "blob", blob_id)
    ).hexdigest()


def verify_git_boundary(manifest_path: Path, manifest: dict) -> None:
    """Reject vendor hashes and paths in both the index and HEAD."""
    repository = repository_root(manifest_path)
    known_hashes = vendor_hashes(manifest)
    forbidden_paths = forbidden_vendor_paths(manifest)
    scopes = {
        "staged index": parse_index_entries(
            run_git(repository, "ls-files", "-s", "-z")
        ),
        "HEAD": parse_head_entries(run_git(repository, "ls-tree", "-r", "-z", "HEAD")),
    }
    violations = []
    digests_by_blob_id = {}
    for scope, entries in scopes.items():
        for blob_id, path in entries:
            if blob_id not in digests_by_blob_id:
                digests_by_blob_id[blob_id] = sha256_blob(repository, blob_id)
            blob_hash = digests_by_blob_id[blob_id]
            if blob_hash in known_hashes:
                violations.append(f"{scope}: known vendor hash at {path}")
            if is_forbidden_path(path, forbidden_paths):
                violations.append(f"{scope}: forbidden vendor path {path}")
    if violations:
        raise FixtureError("Git boundary violation(s): " + "; ".join(violations))


def main() -> int:
    arguments = parse_arguments()
    manifest_path = arguments.manifest.resolve()
    try:
        manifest = read_manifest(manifest_path)
        if arguments.scope == "tracked":
            verify_tracked(manifest_path, manifest)
        elif arguments.scope == "fixture-cache":
            verify_fixture_cache(manifest_path, manifest)
        else:
            verify_git_boundary(manifest_path, manifest)
    except FixtureError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Manifest verification passed: {arguments.scope}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
