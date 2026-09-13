"""Validated input providers that supply an assessment's candidate-facing files (D003).

A provider owns one kind of input source. It validates that source before any
workspace mutation, computes the content identity a new attempt pins, reports
the declared hash each staged copy must match, and stages exactly the
allowlisted candidate-facing files. Nothing here reads solutions, study or
reference material, and nothing here touches an attempt that already exists.

- ``pinned-fetched`` wraps the existing File Storage fixture cache and its
  provenance validation unchanged; the identity it computes is the same digest
  003/01/02 introduced.
- ``packaged-original`` reads original exercises bundled with the installed
  package, verified against their own declared manifest, so they work offline
  and without the fetched cache.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Protocol

from .assessments import (
    PACKAGED_ORIGINAL,
    PINNED_FETCHED,
    AssessmentDefinition,
    content_identity,
)
from .errors import FixtureSetupRequiredError, InvalidInputError
from .filesystem import Filesystem
from .models import PinnedAssessment
from .workspace_cache import ValidatedFixtureCache


PACKAGE_MANIFEST_NAME = "content-manifest.json"
PACKAGE_MANIFEST_SCHEMA_VERSION = "assessment-package/v1"
PACKAGED_RESOURCES_PACKAGE = "codesignal_practice_simulator.resources"
MAX_PACKAGE_MANIFEST_BYTES = 64 * 1024
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_CONTENT_VERSION = re.compile(r"[a-z][a-z0-9-]{0,63}\Z")


class InputProvider(Protocol):
    """One validated source of candidate-facing inputs for a definition."""

    kind: str

    def validate(self, definition: AssessmentDefinition, filesystem: Filesystem) -> None:
        """Fail before any mutation when the source is missing or tampered."""

    def pinned_assessment(self, definition: AssessmentDefinition) -> PinnedAssessment:
        """Return the content identity a new attempt of this definition pins."""

    def declared_hash(self, definition: AssessmentDefinition, filename: str) -> str:
        """Return the SHA-256 a staged copy of ``filename`` must have."""

    def stage_file(
        self,
        definition: AssessmentDefinition,
        filename: str,
        destination: Path,
        filesystem: Filesystem,
    ) -> None:
        """Copy one allowlisted candidate-facing file into transaction-owned staging."""


@dataclass(frozen=True, slots=True)
class PinnedFetchedProvider:
    """The File Storage cache contract, unchanged behind the provider boundary."""

    cache: ValidatedFixtureCache
    kind: str = PINNED_FETCHED

    def validate(self, definition: AssessmentDefinition, filesystem: Filesystem) -> None:
        _require_kind(definition, self.kind)
        self.cache.validate(filesystem)

    def pinned_assessment(self, definition: AssessmentDefinition) -> PinnedAssessment:
        _require_kind(definition, self.kind)
        return self.cache.pinned_assessment(definition)

    def declared_hash(self, definition: AssessmentDefinition, filename: str) -> str:
        return self.cache.declared_hash(definition, filename)

    def stage_file(
        self,
        definition: AssessmentDefinition,
        filename: str,
        destination: Path,
        filesystem: Filesystem,
    ) -> None:
        source = self.cache.root.joinpath(*definition.cache_directory.split("/"), filename)
        filesystem.copyfile(source, destination)


@dataclass(frozen=True, slots=True)
class PackageManifest:
    """The declared content of one bundled original exercise."""

    assessment_id: str
    content_version: str
    file_hashes: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class PackagedOriginalProvider:
    """Original exercises bundled with the package, verified against their manifest.

    ``root`` is the directory that holds one subdirectory per definition
    (``definition.cache_directory`` relative to it). Each subdirectory contains
    exactly the definition's candidate-facing files plus ``content-manifest.json``;
    anything else (a solution, a stray note) fails validation so development
    material can never be staged into an attempt by accident.
    """

    root: Path
    kind: str = PACKAGED_ORIGINAL

    @classmethod
    def installed(cls) -> PackagedOriginalProvider:
        """Locate bundled originals inside the installed package."""
        try:
            traversable = resources.files(PACKAGED_RESOURCES_PACKAGE)
        except ModuleNotFoundError as error:
            raise FixtureSetupRequiredError(
                "packaged content is unavailable: resources package is missing"
            ) from error
        if not isinstance(traversable, Path):
            raise FixtureSetupRequiredError(
                "packaged content is unavailable: resources must be installed as files"
            )
        return cls(root=traversable)

    def validate(self, definition: AssessmentDefinition, filesystem: Filesystem) -> None:
        _require_kind(definition, self.kind)
        manifest = self._manifest(definition)
        directory = self._directory(definition)
        try:
            entries = sorted(entry.name for entry in directory.iterdir())
        except OSError as error:
            raise _invalid(definition, "cannot inspect packaged directory") from error
        allowed = {*definition.copied_filenames, PACKAGE_MANIFEST_NAME}
        unexpected = sorted(set(entries) - allowed)
        if unexpected:
            raise _invalid(definition, f"unexpected packaged file: {unexpected[0]}")
        for filename in definition.copied_filenames:
            path = directory / filename
            if path.is_symlink() or not path.is_file():
                raise _invalid(definition, f"missing packaged file: {filename}")
            try:
                actual = hashlib.sha256(filesystem.read_bytes(path)).hexdigest()
            except OSError as error:
                raise _invalid(definition, f"cannot read packaged file: {filename}") from error
            if actual != manifest.file_hashes[filename]:
                raise _invalid(definition, f"packaged file does not match its declared hash: {filename}")

    def pinned_assessment(self, definition: AssessmentDefinition) -> PinnedAssessment:
        _require_kind(definition, self.kind)
        manifest = self._manifest(definition)
        try:
            return content_identity(
                definition,
                content_version=manifest.content_version,
                file_hashes=manifest.file_hashes,
            )
        except InvalidInputError as error:
            raise _invalid(definition, "manifest content identity is invalid") from error

    def declared_hash(self, definition: AssessmentDefinition, filename: str) -> str:
        hashes = self._manifest(definition).file_hashes
        try:
            return hashes[filename]
        except KeyError as error:
            raise _invalid(definition, f"manifest lacks a hash for {filename}") from error

    def stage_file(
        self,
        definition: AssessmentDefinition,
        filename: str,
        destination: Path,
        filesystem: Filesystem,
    ) -> None:
        if filename not in definition.copied_filenames:
            raise InvalidInputError(f"file is not a candidate-facing input: {filename}")
        source = self._directory(definition) / filename
        filesystem.write_bytes(destination, filesystem.read_bytes(source))

    def _directory(self, definition: AssessmentDefinition) -> Path:
        # Every segment below the resources root is checked, not only the last
        # one, so a symlinked intermediate directory cannot lead out of the
        # installed package.
        directory = self.root
        for segment in definition.cache_directory.split("/"):
            directory = directory / segment
            if directory.is_symlink() or not directory.is_dir():
                raise _invalid(definition, "packaged directory is missing")
        return directory

    def _manifest(self, definition: AssessmentDefinition) -> PackageManifest:
        path = self._directory(definition) / PACKAGE_MANIFEST_NAME
        if path.is_symlink() or not path.is_file():
            raise _invalid(definition, "content manifest is missing")
        try:
            with path.open("rb") as stream:
                raw = stream.read(MAX_PACKAGE_MANIFEST_BYTES + 1)
            if len(raw) > MAX_PACKAGE_MANIFEST_BYTES:
                raise ValueError("manifest too large")
            data = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeDecodeError, ValueError) as error:
            raise _invalid(definition, "content manifest is unreadable") from error
        if not isinstance(data, dict) or set(data) != {
            "schema_version",
            "assessment_id",
            "content_version",
            "files",
        }:
            raise _invalid(definition, "content manifest has an invalid field set")
        if data["schema_version"] != PACKAGE_MANIFEST_SCHEMA_VERSION:
            raise _invalid(definition, "content manifest schema version is unsupported")
        if data["assessment_id"] != definition.metadata.assessment_id:
            raise _invalid(definition, "content manifest names another assessment")
        version = data["content_version"]
        if not isinstance(version, str) or not _CONTENT_VERSION.fullmatch(version):
            raise _invalid(definition, "content manifest version is invalid")
        files = data["files"]
        if (
            not isinstance(files, dict)
            or set(files) != set(definition.copied_filenames)
            or any(
                not isinstance(digest, str) or not _SHA256.fullmatch(digest)
                for digest in files.values()
            )
        ):
            raise _invalid(definition, "content manifest must declare every candidate-facing file")
        return PackageManifest(
            assessment_id=definition.metadata.assessment_id,
            content_version=version,
            file_hashes=dict(files),
        )


class InputProviders:
    """Resolve the provider a definition declares; unknown kinds fail closed."""

    def __init__(self, providers: Mapping[str, InputProvider]) -> None:
        if not providers:
            raise InvalidInputError("input providers cannot be empty")
        for kind, provider in providers.items():
            if provider.kind != kind:
                raise InvalidInputError(f"input provider kind mismatch: {kind}")
        self._providers = dict(providers)

    @classmethod
    def default(cls, cache: ValidatedFixtureCache) -> InputProviders:
        """The production set: the fetched cache plus installed originals."""
        providers: dict[str, InputProvider] = {PINNED_FETCHED: PinnedFetchedProvider(cache)}
        try:
            providers[PACKAGED_ORIGINAL] = PackagedOriginalProvider.installed()
        except FixtureSetupRequiredError:
            # No bundled originals in this installation: only fetched content
            # is startable, and a packaged definition fails when it is selected.
            pass
        return cls(providers)

    def for_definition(self, definition: AssessmentDefinition) -> InputProvider:
        try:
            return self._providers[definition.provider_kind]
        except KeyError as error:
            raise FixtureSetupRequiredError(
                "fixture setup is required: no input provider for "
                f"{definition.provider_kind} content"
            ) from error


def _require_kind(definition: AssessmentDefinition, kind: str) -> None:
    if definition.provider_kind != kind:
        raise InvalidInputError(
            f"definition {definition.metadata.assessment_id} is not {kind} content"
        )


def _invalid(definition: AssessmentDefinition, reason: str) -> FixtureSetupRequiredError:
    return FixtureSetupRequiredError(
        f"packaged content is invalid for {definition.metadata.assessment_id}: {reason}"
    )


__all__ = [
    "InputProvider",
    "InputProviders",
    "MAX_PACKAGE_MANIFEST_BYTES",
    "PACKAGE_MANIFEST_NAME",
    "PACKAGE_MANIFEST_SCHEMA_VERSION",
    "PACKAGED_RESOURCES_PACKAGE",
    "PackageManifest",
    "PackagedOriginalProvider",
    "PinnedFetchedProvider",
]
