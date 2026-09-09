"""Validated fixture-cache contracts used by workspace creation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .assessments import FILE_STORAGE
from .errors import FixtureSetupRequiredError
from .filesystem import Filesystem
from .fixture_setup import FixtureSetupError, load_runtime_manifest, runtime_cache_root


CACHE_INPUTS = FILE_STORAGE.copied_filenames
_CACHE_README = "vendor-readme.md"
_EXPECTED_CACHE_PATHS = frozenset(
    (_CACHE_README, *(f"assessment/file_storage/{name}" for name in CACHE_INPUTS))
)


@dataclass(frozen=True, slots=True)
class ValidatedFixtureCache:
    """The complete seven-file cache contract used before workspace mutation."""

    root: Path
    hashes: dict[str, str]

    @classmethod
    def from_manifest(cls, manifest_path: Path) -> ValidatedFixtureCache:
        """Build a cache contract from the project's fetch-only manifest."""
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            cache_relative = manifest["fixture_cache_root"]
            fetches = manifest["fetches"]
        except (
            OSError,
            KeyError,
            TypeError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as error:
            raise FixtureSetupRequiredError(
                f"fixture setup is required: cannot read manifest {manifest_path}"
            ) from error
        if not isinstance(cache_relative, str) or not isinstance(fetches, list):
            raise FixtureSetupRequiredError("fixture setup is required: invalid manifest")
        project_root = manifest_path.resolve().parent.parent
        root = (project_root / cache_relative).resolve()
        if root != project_root and project_root not in root.parents:
            raise FixtureSetupRequiredError("fixture setup is required: cache escapes project")
        return cls._from_fetches(root, fetches)

    @classmethod
    def from_runtime_manifest(cls, workspace_root: Path) -> ValidatedFixtureCache:
        """Build a wheel-safe cache contract from packaged non-vendor metadata."""
        try:
            manifest = load_runtime_manifest()
            root = runtime_cache_root(workspace_root, manifest)
            fetches = manifest["fetches"]
        except (FixtureSetupError, KeyError, TypeError) as error:
            raise FixtureSetupRequiredError(
                "fixture setup is required: installed fixture metadata is invalid"
            ) from error
        return cls._from_fetches(root, fetches)

    @classmethod
    def _from_fetches(
        cls, root: Path, fetches: object
    ) -> ValidatedFixtureCache:
        """Validate the seven cache records shared by source and wheel manifests."""
        if not isinstance(fetches, list):
            raise FixtureSetupRequiredError("fixture setup is required: invalid manifest")
        hashes: dict[str, str] = {}
        for record in fetches:
            if not isinstance(record, dict):
                raise FixtureSetupRequiredError("fixture setup is required: invalid manifest")
            path = record.get("cache_path")
            digest = record.get("sha256")
            if (
                not isinstance(path, str)
                or not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
                or path in hashes
            ):
                raise FixtureSetupRequiredError("fixture setup is required: invalid manifest")
            hashes[path] = digest
        if set(hashes) != _EXPECTED_CACHE_PATHS:
            raise FixtureSetupRequiredError(
                "fixture setup is required: manifest does not define seven cache records"
            )
        return cls(root=root, hashes=hashes)

    def validate(self, filesystem: Filesystem) -> None:
        """Verify the complete cache and all hashes before any attempt write."""
        if set(self.hashes) != _EXPECTED_CACHE_PATHS:
            raise FixtureSetupRequiredError(
                "fixture setup is required: cache contract lacks seven records"
            )
        if not self.root.is_dir() or self.root.is_symlink():
            raise FixtureSetupRequiredError(
                f"fixture setup is required: cache is absent at {self.root}"
            )
        actual = self._file_names()
        if actual != set(self.hashes):
            raise FixtureSetupRequiredError(
                "fixture setup is required: cache does not contain exactly seven files"
            )
        self._validate_hashes(filesystem)

    def _file_names(self) -> set[str]:
        actual: set[str] = set()
        try:
            for path in self.root.rglob("*"):
                if path.is_symlink():
                    raise FixtureSetupRequiredError(
                        f"fixture setup is required: cache contains symlink {path}"
                    )
                if path.is_file():
                    actual.add(path.relative_to(self.root).as_posix())
        except OSError as error:
            raise FixtureSetupRequiredError(
                f"fixture setup is required: cannot inspect cache {self.root}"
            ) from error
        return actual

    def _validate_hashes(self, filesystem: Filesystem) -> None:
        for relative, expected_hash in self.hashes.items():
            path = self.root.joinpath(*relative.split("/"))
            try:
                actual_hash = hashlib.sha256(filesystem.read_bytes(path)).hexdigest()
            except OSError as error:
                raise FixtureSetupRequiredError(
                    f"fixture setup is required: cannot read cache file {relative}"
                ) from error
            if actual_hash != expected_hash:
                raise FixtureSetupRequiredError(
                    f"fixture setup is required: cache hash mismatch for {relative}"
                )


__all__ = ["CACHE_INPUTS", "ValidatedFixtureCache"]
