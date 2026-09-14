"""Build-time check of bundled original exercises.

Fails when a packaged exercise directory contains anything but the allowlisted
candidate-facing files and its manifest, when a manifest hash does not match
the bundled bytes, when the registry and the directory disagree, or when
``test_simulation.py`` does not define exactly ``test_group_1`` through
``test_group_4`` on ``TestSimulateCodingFramework`` importing only ``unittest``
and ``simulation``. Run through ``just check content``.
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from codesignal_practice_simulator.assessments import (  # noqa: E402
    DEFAULT_ASSESSMENT_REGISTRY,
    PACKAGED_ORIGINAL,
    AssessmentDefinition,
)
from codesignal_practice_simulator.input_providers import (  # noqa: E402
    PACKAGE_MANIFEST_NAME,
    PACKAGE_MANIFEST_SCHEMA_VERSION,
)

RESOURCES = PROJECT / "src" / "codesignal_practice_simulator" / "resources"
ASSESSMENTS = RESOURCES / "assessments"
TEST_CLASS = "TestSimulateCodingFramework"
GROUP_METHODS = tuple(f"test_group_{group}" for group in (1, 2, 3, 4))
ALLOWED_IMPORTS = frozenset({"unittest", "simulation"})
# Vendor names and festival identifiers never belong in candidate-facing content.
FORBIDDEN_TEXT = ("codesignal", "cp0002")


class ContentCheckError(RuntimeError):
    """A bundled exercise does not satisfy the content contract."""


def check_bundled_content(resources: Path = RESOURCES) -> dict[str, object]:
    """Validate every packaged-original definition and every bundled directory."""
    assessments = resources / "assessments"
    definitions = {
        definition.metadata.assessment_id: definition
        for definition in DEFAULT_ASSESSMENT_REGISTRY.definitions()
        if definition.provider_kind == PACKAGED_ORIGINAL
    }
    directories = sorted(path.name for path in assessments.iterdir()) if assessments.exists() else []
    if set(directories) != set(definitions):
        raise ContentCheckError(
            f"bundled directories {directories} do not match packaged definitions {sorted(definitions)}"
        )
    checked: dict[str, object] = {}
    for assessment_id, definition in sorted(definitions.items()):
        checked[assessment_id] = _check_directory(assessments / assessment_id, definition)
    return checked


def _check_directory(directory: Path, definition: AssessmentDefinition) -> dict[str, object]:
    if directory.is_symlink() or not directory.is_dir():
        raise ContentCheckError(f"{definition.metadata.assessment_id}: bundled directory is missing")
    expected = f"assessments/{definition.metadata.assessment_id}"
    if definition.cache_directory != expected:
        raise ContentCheckError(f"{definition.metadata.assessment_id}: input directory must be {expected}")
    allowed = {*definition.copied_filenames, PACKAGE_MANIFEST_NAME}
    present = sorted(path.name for path in directory.iterdir())
    if set(present) != allowed:
        raise ContentCheckError(
            f"{definition.metadata.assessment_id}: directory contents {present} must be exactly {sorted(allowed)}"
        )
    for name in present:
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ContentCheckError(f"{definition.metadata.assessment_id}: {name} must be a regular file")
    # The runner contract is checked before hashes so a renamed group is
    # reported as such, not as a stale manifest.
    _check_test_module(directory / definition.test_filename, definition.metadata.assessment_id)
    manifest = json.loads((directory / PACKAGE_MANIFEST_NAME).read_text(encoding="utf-8"))
    if manifest.get("schema_version") != PACKAGE_MANIFEST_SCHEMA_VERSION:
        raise ContentCheckError(f"{definition.metadata.assessment_id}: manifest schema version is wrong")
    if manifest.get("assessment_id") != definition.metadata.assessment_id:
        raise ContentCheckError(f"{definition.metadata.assessment_id}: manifest names another assessment")
    files = manifest.get("files")
    if not isinstance(files, dict) or set(files) != set(definition.copied_filenames):
        raise ContentCheckError(f"{definition.metadata.assessment_id}: manifest must declare every candidate file")
    for name, declared in files.items():
        actual = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        if actual != declared:
            raise ContentCheckError(f"{definition.metadata.assessment_id}: hash mismatch for {name}")
    for name in definition.prompt_filenames:
        if not (directory / name).read_text(encoding="utf-8").strip():
            raise ContentCheckError(f"{definition.metadata.assessment_id}: {name} is empty")
    for name in definition.copied_filenames:
        text = (directory / name).read_text(encoding="utf-8")
        for marker in FORBIDDEN_TEXT:
            if marker.lower() in text.lower():
                raise ContentCheckError(
                    f"{definition.metadata.assessment_id}: {name} contains forbidden text {marker!r}"
                )
    return {"files": present, "content_version": manifest.get("content_version")}


def _check_test_module(path: Path, assessment_id: str) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    if not imported <= ALLOWED_IMPORTS:
        raise ContentCheckError(f"{assessment_id}: test module imports {sorted(imported - ALLOWED_IMPORTS)}")
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == TEST_CLASS]
    if len(classes) != 1:
        raise ContentCheckError(f"{assessment_id}: test module must define exactly one {TEST_CLASS}")
    methods = tuple(
        node.name
        for node in classes[0].body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test")
    )
    if methods != GROUP_METHODS:
        raise ContentCheckError(
            f"{assessment_id}: {TEST_CLASS} must define exactly {list(GROUP_METHODS)}, found {list(methods)}"
        )


def main() -> int:
    try:
        checked = check_bundled_content()
    except ContentCheckError as error:
        print(f"content check failed: {error}", file=sys.stderr)
        return 1
    for assessment_id, detail in checked.items():
        print(f"{assessment_id}: {detail['content_version']} ({len(detail['files'])} files)")  # type: ignore[index]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
