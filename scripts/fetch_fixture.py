#!/usr/bin/env python3
"""Fetch and atomically validate the pinned, ignored fixture cache."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen

from fixture_contract import (
    FixtureError,
    fixture_cache_path,
    read_manifest,
    sha256_file,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Populate the ignored CodeSignal fixture cache from pinned sources."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="path to the fetch-only migration manifest",
    )
    parser.add_argument(
        "--source",
        type=Path,
        help="complete offline tree using declared upstream_path names",
    )
    return parser.parse_args()


def read_url(url: str) -> bytes:
    """Download one pinned file."""
    try:
        with urlopen(url, timeout=30) as response:
            return response.read()
    except (OSError, URLError) as error:
        raise FixtureError(f"download failed for {url}: {error}") from error


def source_file(source_root: Path, upstream_path: str) -> Path:
    """Return a regular, in-tree file from an offline source tree."""
    source_root = source_root.resolve()
    if not source_root.is_dir():
        raise FixtureError(f"offline source is not a directory: {source_root}")
    candidate = source_root.joinpath(*upstream_path.split("/"))
    if candidate.is_symlink() or not candidate.is_file():
        raise FixtureError(f"offline source is missing regular file: {upstream_path}")
    resolved = candidate.resolve()
    if source_root not in resolved.parents:
        raise FixtureError(f"offline source file escapes its root: {upstream_path}")
    return candidate


def fetch_records(
    manifest: dict,
    staging_root: Path,
    source_root: Path | None,
    downloader=read_url,
) -> None:
    """Fetch every declared record to a staging tree and validate its hash."""
    repository = manifest["upstream"]["repository"]
    commit = manifest["upstream"]["commit"]

    for record in manifest["fetches"]:
        upstream_path = record["upstream_path"]
        destination = staging_root.joinpath(*record["cache_path"].split("/"))
        destination.parent.mkdir(parents=True, exist_ok=True)

        if source_root is not None:
            shutil.copyfile(source_file(source_root, upstream_path), destination)
        else:
            url = (
                f"https://raw.githubusercontent.com/{repository}/{commit}/"
                f"{quote(record['repository_path'])}"
            )
            destination.write_bytes(downloader(url))

        actual = sha256_file(destination)
        if actual != record["sha256"]:
            raise FixtureError(
                f"hash mismatch for {upstream_path}: expected {record['sha256']}, "
                f"got {actual}"
            )


def verify_staging_tree(manifest: dict, staging_root: Path) -> None:
    """Ensure staging contains exactly the seven declared regular files."""
    expected = {record["cache_path"] for record in manifest["fetches"]}
    actual = {
        path.relative_to(staging_root).as_posix()
        for path in staging_root.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    if actual != expected:
        raise FixtureError("staging cache does not contain exactly the seven declared files")


def publish_cache(staging_root: Path, cache_root: Path) -> None:
    """Replace the cache only after all files have been validated."""
    cache_root.parent.mkdir(parents=True, exist_ok=True)
    backup_root = cache_root.with_name(f".{cache_root.name}.previous")
    if backup_root.exists() or backup_root.is_symlink():
        shutil.rmtree(backup_root)

    moved_existing = False
    try:
        if cache_root.exists() or cache_root.is_symlink():
            os.replace(cache_root, backup_root)
            moved_existing = True
        os.replace(staging_root, cache_root)
    except OSError as error:
        if moved_existing and not (cache_root.exists() or cache_root.is_symlink()):
            os.replace(backup_root, cache_root)
        raise FixtureError(f"could not atomically publish fixture cache: {error}") from error
    if moved_existing:
        shutil.rmtree(backup_root)


def populate_fixture(
    manifest_path: Path, source_root: Path | None = None, downloader=read_url
) -> Path:
    """Build and atomically publish a validated fixture cache."""
    manifest_path = manifest_path.resolve()
    manifest = read_manifest(manifest_path)
    cache_root = fixture_cache_path(manifest_path, manifest)
    cache_root.parent.mkdir(parents=True, exist_ok=True)
    staging_root = Path(
        tempfile.mkdtemp(prefix=f".{cache_root.name}.staging-", dir=cache_root.parent)
    )
    try:
        fetch_records(manifest, staging_root, source_root, downloader)
        verify_staging_tree(manifest, staging_root)
        publish_cache(staging_root, cache_root)
    except Exception:
        if staging_root.exists() or staging_root.is_symlink():
            shutil.rmtree(staging_root)
        raise
    return cache_root


def main() -> int:
    arguments = parse_arguments()
    try:
        cache_root = populate_fixture(arguments.manifest, arguments.source)
    except FixtureError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        print(
            "Fixture setup is required. Re-run with a complete validated --source "
            "tree or check network access to the pinned upstream commit.",
            file=sys.stderr,
        )
        return 1
    print(f"Validated fixture cache: {cache_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
