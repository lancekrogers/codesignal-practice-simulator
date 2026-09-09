"""Shared validation helpers for the fetch-only fixture contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath


EXPECTED_FETCH_PATHS = {
    ("README.md", "vendor-readme.md"),
    ("practice_assessments/file_storage/level1.md", "assessment/file_storage/level1.md"),
    ("practice_assessments/file_storage/level2.md", "assessment/file_storage/level2.md"),
    ("practice_assessments/file_storage/level3.md", "assessment/file_storage/level3.md"),
    ("practice_assessments/file_storage/level4.md", "assessment/file_storage/level4.md"),
    ("practice_assessments/file_storage/simulation.py", "assessment/file_storage/simulation.py"),
    (
        "practice_assessments/file_storage/test_simulation.py",
        "assessment/file_storage/test_simulation.py",
    ),
}

EXPECTED_REPOSITORY_PATHS = {
    "README.md": "Readme.md",
    **{
        f"practice_assessments/file_storage/{name}": (
            f"practice_assessments/file_storage/{name}"
        )
        for name in (
            "level1.md",
            "level2.md",
            "level3.md",
            "level4.md",
            "simulation.py",
            "test_simulation.py",
        )
    },
}

UPSTREAM_REPOSITORY = "PaulLockett/CodeSignal_Practice_Industry_Coding_Framework"
UPSTREAM_COMMIT = "6aab304"
FIXTURE_CACHE_ROOT = ".cache/codesignal-fixtures/6aab304"
SHA256_LENGTH = 64


class FixtureError(Exception):
    """Raised when fixture metadata or bytes do not meet the contract."""


def read_manifest(path: Path) -> dict:
    """Read and validate a fetch-only manifest."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FixtureError(f"cannot read manifest {path}: {error}") from error
    validate_manifest(data)
    return data


def validate_manifest(data: object) -> None:
    """Validate the parts of the manifest needed to enforce this boundary."""
    if not isinstance(data, dict):
        raise FixtureError("manifest must be a JSON object")
    if data.get("schema_version") != 2:
        raise FixtureError("manifest schema_version must be 2")
    if data.get("license_decision") != "FETCH_ONLY":
        raise FixtureError("manifest license_decision must be FETCH_ONLY")
    if data.get("fixture_cache_root") != FIXTURE_CACHE_ROOT:
        raise FixtureError(f"fixture_cache_root must be {FIXTURE_CACHE_ROOT}")

    upstream = data.get("upstream")
    if not isinstance(upstream, dict):
        raise FixtureError("manifest upstream must be an object")
    if upstream.get("repository") != UPSTREAM_REPOSITORY:
        raise FixtureError(f"upstream repository must be {UPSTREAM_REPOSITORY}")
    if upstream.get("commit") != UPSTREAM_COMMIT:
        raise FixtureError(f"upstream commit must be {UPSTREAM_COMMIT}")

    license_info = data.get("license")
    if not isinstance(license_info, dict):
        raise FixtureError("manifest license must be an object")
    if license_info.get("licenseInfo") is not None:
        raise FixtureError("manifest licenseInfo must be null")
    if license_info.get("license_endpoint_status") != 404:
        raise FixtureError("manifest license endpoint status must be 404")

    fetches = data.get("fetches")
    if not isinstance(fetches, list) or len(fetches) != len(EXPECTED_FETCH_PATHS):
        raise FixtureError("manifest must declare exactly seven fetch records")

    fetch_by_cache_path = {}
    for record in fetches:
        if not isinstance(record, dict):
            raise FixtureError("each fetch record must be an object")
        upstream_path = require_relative_path(record.get("upstream_path"), "upstream_path")
        cache_path = require_relative_path(record.get("cache_path"), "cache_path")
        repository_path = require_relative_path(
            record.get("repository_path"), "repository_path"
        )
        require_sha256(record.get("sha256"), f"fetch hash for {cache_path}")
        if repository_path != EXPECTED_REPOSITORY_PATHS.get(upstream_path):
            raise FixtureError(f"unexpected repository_path for {upstream_path}")
        if cache_path in fetch_by_cache_path:
            raise FixtureError(f"duplicate fetch cache path: {cache_path}")
        fetch_by_cache_path[cache_path] = record

    pairs = {
        (record["upstream_path"], record["cache_path"]) for record in fetches
    }
    if pairs != EXPECTED_FETCH_PATHS:
        raise FixtureError("manifest fetch paths do not match the seven-file contract")

    files = data.get("files")
    if not isinstance(files, list):
        raise FixtureError("manifest files must be a list")

    destinations = set()
    vendor_by_cache_path = {}
    for record in files:
        if not isinstance(record, dict):
            raise FixtureError("each file record must be an object")
        source_path = require_relative_path(record.get("source_path"), "source_path")
        classification = record.get("classification")
        decision = record.get("decision")
        destination = record.get("destination_path")
        cache_path = record.get("cache_path")
        require_sha256(record.get("sha256"), f"file hash for {source_path}")

        if classification == "vendor":
            if decision != "exclude" or destination is not None:
                raise FixtureError(f"vendor record must be excluded: {source_path}")
            if cache_path is not None:
                cache_path = require_relative_path(cache_path, "cache_path")
                if cache_path in vendor_by_cache_path:
                    raise FixtureError(f"duplicate vendor cache path: {cache_path}")
                vendor_by_cache_path[cache_path] = record
        elif decision == "include":
            if classification != "user_authored":
                raise FixtureError(f"included file is not user-authored: {source_path}")
            destination = require_relative_path(destination, "destination_path")
            if destination in destinations:
                raise FixtureError(f"duplicate included destination: {destination}")
            destinations.add(destination)
        elif decision != "exclude":
            raise FixtureError(f"unknown file decision for {source_path}: {decision!r}")

    if set(vendor_by_cache_path) != set(fetch_by_cache_path):
        raise FixtureError("fetch records must exactly match vendor cache records")
    for cache_path, fetch in fetch_by_cache_path.items():
        if vendor_by_cache_path[cache_path]["sha256"] != fetch["sha256"]:
            raise FixtureError(f"hash disagreement for {cache_path}")


def require_relative_path(value: object, field_name: str) -> str:
    """Return a normalized, portable relative path or raise FixtureError."""
    if not isinstance(value, str) or not value:
        raise FixtureError(f"{field_name} must be a non-empty path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise FixtureError(f"{field_name} must be a normalized relative path: {value!r}")
    if str(path) != value:
        raise FixtureError(f"{field_name} is not normalized: {value!r}")
    return value


def require_sha256(value: object, field_name: str) -> str:
    """Return a SHA-256 hex digest or raise FixtureError."""
    if (
        not isinstance(value, str)
        or len(value) != SHA256_LENGTH
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise FixtureError(f"{field_name} must be a lowercase SHA-256 digest")
    return value


def sha256_file(path: Path) -> str:
    """Calculate a file's SHA-256 digest without loading it all into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fixture_cache_path(manifest_path: Path, manifest: dict) -> Path:
    """Return the validated cache location under this project's root."""
    project_root = manifest_path.resolve().parent.parent
    cache_root = (project_root / manifest["fixture_cache_root"]).resolve()
    if project_root not in cache_root.parents:
        raise FixtureError("fixture cache escapes the project root")
    return cache_root


def vendor_hashes(manifest: dict) -> set[str]:
    """Return every manifest-known vendor digest, including non-fetchable ones."""
    return {
        record["sha256"]
        for record in manifest["files"]
        if record["classification"] == "vendor"
    }


def forbidden_vendor_paths(manifest: dict) -> set[str]:
    """Return project paths that may not contain manifest-known vendor files."""
    return {
        record["source_path"]
        for record in manifest["files"]
        if record["classification"] == "vendor"
    }
