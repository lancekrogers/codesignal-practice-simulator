"""Validated input providers: unchanged File Storage identity, offline originals."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from tests.workspace_test_support import (
    PROJECT,
    RecordingFilesystem,
    ValidatedFixtureCache,
    WorkspaceManager,
    make_cache,
    tree_snapshot,
)

from codesignal_practice_simulator.application import RuntimeApplication
from codesignal_practice_simulator.assessments import (
    DRILL_PROFILE,
    FILE_STORAGE,
    FULL_PROFILE,
    PACKAGED_ORIGINAL,
    PINNED_FETCHED,
    RUNNER_CONTRACT,
    AssessmentDefinition,
    AssessmentRegistry,
    content_identity,
)
from codesignal_practice_simulator.attempt_history import AttemptHistoryService
from codesignal_practice_simulator.attempt_reviews import AttemptReviewService
from codesignal_practice_simulator.errors import (
    AssessmentVersionUnavailableError,
    FixtureSetupRequiredError,
    InvalidInputError,
)
from codesignal_practice_simulator.filesystem import LocalFilesystem
from codesignal_practice_simulator.input_providers import (
    PACKAGE_MANIFEST_NAME,
    PACKAGE_MANIFEST_SCHEMA_VERSION,
    InputProviders,
    PackagedOriginalProvider,
    PinnedFetchedProvider,
)
from codesignal_practice_simulator.lifecycle import LifecycleService
from codesignal_practice_simulator.models import (
    ACTIVE,
    SUBMITTED,
    AssessmentMetadata,
    LevelResult,
    ScoreSummary,
)
from codesignal_practice_simulator.workspace_cache import CACHE_INPUTS


START = datetime(2026, 9, 8, 19, tzinfo=timezone.utc)
# Recorded from ValidatedFixtureCache.from_manifest(docs/migration-manifest.json)
# before the provider refactor. The provider boundary must not change it.
PRE_REFACTOR_FILE_STORAGE = (
    "upstream-6aab304",
    "e9cb78d1cfa9a0124288bd9ffa32e039fb1c7aee4eacec720e350c82c9e0e61b",
)

ORIGINAL = AssessmentDefinition(
    metadata=AssessmentMetadata("records_demo", "Records Demo"),
    cache_directory="assessments/records_demo",
    prompt_filenames=("level1.md", "level2.md", "level3.md", "level4.md"),
    candidate_filename="simulation.py",
    test_filename="test_simulation.py",
    level_groups=(1, 2, 3, 4),
    profile_ids=frozenset((FULL_PROFILE, DRILL_PROFILE)),
    runner_contract=RUNNER_CONTRACT,
    provider_kind=PACKAGED_ORIGINAL,
    description="Synthetic bundled exercise used only by tests.",
)
ORIGINAL_CONTENT = {
    name: f"original {name}\n".encode("utf-8") for name in ORIGINAL.copied_filenames
}


class FakeClock:
    def __init__(self, value: datetime = START) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


class RecordingScorer:
    def __init__(self) -> None:
        self.calls: list[Path] = []

    def __call__(self, attempt: Path) -> ScoreSummary:
        self.calls.append(attempt)
        return ScoreSummary(tuple(LevelResult(level, "passed") for level in range(1, 5)))


def write_package(root: Path, *, version: str = "records-demo-1") -> Path:
    """Write a valid bundled original under ``root/assessments/records_demo``."""
    directory = root.joinpath(*ORIGINAL.cache_directory.split("/"))
    directory.mkdir(parents=True, exist_ok=True)
    for name, data in ORIGINAL_CONTENT.items():
        (directory / name).write_bytes(data)
    manifest = {
        "schema_version": PACKAGE_MANIFEST_SCHEMA_VERSION,
        "assessment_id": ORIGINAL.metadata.assessment_id,
        "content_version": version,
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in ORIGINAL_CONTENT.items()},
    }
    (directory / PACKAGE_MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    return directory


class ProviderTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workspace_root = self.root / "workspace"
        self.workspace_root.mkdir()
        self.package_root = self.root / "resources"
        self.package = write_package(self.package_root)
        self.cache: ValidatedFixtureCache = make_cache(self.root)
        self.registry = AssessmentRegistry((FILE_STORAGE, ORIGINAL))
        self.clock = FakeClock()
        self.scorer = RecordingScorer()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def providers(self, cache: ValidatedFixtureCache | None = None) -> InputProviders:
        return InputProviders(
            {
                PINNED_FETCHED: PinnedFetchedProvider(self.cache if cache is None else cache),
                PACKAGED_ORIGINAL: PackagedOriginalProvider(self.package_root),
            }
        )

    def manager(self, *, cache: ValidatedFixtureCache | None = None, filesystem=None) -> WorkspaceManager:
        selected = self.cache if cache is None else cache
        return WorkspaceManager(
            self.workspace_root,
            selected,
            filesystem=filesystem,
            registry=self.registry,
            providers=self.providers(selected),
        )

    def service(self, manager: WorkspaceManager | None = None) -> LifecycleService:
        return LifecycleService(manager or self.manager(), self.clock, self.scorer)

    def missing_cache(self) -> ValidatedFixtureCache:
        """A cache contract whose directory was never fetched."""
        return ValidatedFixtureCache(
            self.root / "never-fetched", dict(self.cache.hashes), "upstream-0000000"
        )

    def attempts(self) -> Path:
        return self.workspace_root / "attempts"


class FileStorageIdentityTests(ProviderTestCase):
    def test_file_storage_digest_is_unchanged_behind_the_provider_boundary(self) -> None:
        project_cache = ValidatedFixtureCache.from_manifest(PROJECT / "docs" / "migration-manifest.json")
        provider = PinnedFetchedProvider(project_cache)

        pinned = provider.pinned_assessment(FILE_STORAGE)

        self.assertEqual((pinned.content_version, pinned.content_digest), PRE_REFACTOR_FILE_STORAGE)
        self.assertEqual(pinned, project_cache.pinned_assessment(FILE_STORAGE))
        self.assertEqual(
            WorkspaceManager(self.workspace_root, project_cache).pinned_assessment(
                FILE_STORAGE.metadata
            ),
            pinned,
        )

    def test_legacy_file_storage_creation_is_unchanged(self) -> None:
        recording = RecordingFilesystem()
        manager = self.manager(filesystem=recording)
        service = self.service(manager)

        state = service.start(FILE_STORAGE.metadata)

        # Files are still copied from the cache (six copyfile calls), staged
        # bytes still verified against manifest hashes, identity still pinned.
        self.assertEqual(recording.calls.get("copyfile"), len(CACHE_INPUTS))
        self.assertEqual(state.assessment, self.cache.pinned_assessment(FILE_STORAGE))
        attempt = self.attempts() / state.attempt_id
        for name in CACHE_INPUTS:
            self.assertEqual(
                hashlib.sha256((attempt / name).read_bytes()).hexdigest(),
                self.cache.hashes[f"assessment/file_storage/{name}"],
            )

    def test_fetched_content_still_requires_the_complete_cache(self) -> None:
        service = self.service(self.manager(cache=self.missing_cache()))

        with self.assertRaisesRegex(FixtureSetupRequiredError, "cache is absent"):
            service.start(FILE_STORAGE.metadata)
        self.assertFalse(self.attempts().exists())

        # A tampered cache file is still rejected before any attempt exists.
        cache_file = self.cache.root / "assessment" / "file_storage" / "level1.md"
        cache_file.write_bytes(b"tampered\n")
        with self.assertRaisesRegex(FixtureSetupRequiredError, "hash mismatch"):
            self.service().start(FILE_STORAGE.metadata)
        self.assertFalse(self.attempts().exists())


class PackagedOriginalTests(ProviderTestCase):
    def test_original_starts_offline_without_the_fetched_cache(self) -> None:
        manager = self.manager(cache=self.missing_cache())
        service = self.service(manager)

        state = service.start(ORIGINAL.metadata, mode="drill", drill_duration_seconds=600)

        self.assertEqual(state.status, ACTIVE)
        self.assertEqual(state.assessment.content_version, "records-demo-1")
        self.assertEqual(
            state.assessment,
            content_identity(
                ORIGINAL,
                content_version="records-demo-1",
                file_hashes={n: hashlib.sha256(d).hexdigest() for n, d in ORIGINAL_CONTENT.items()},
            ),
        )
        attempt = self.attempts() / state.attempt_id
        for name, data in ORIGINAL_CONTENT.items():
            self.assertEqual((attempt / name).read_bytes(), data)
        self.assertFalse((attempt / PACKAGE_MANIFEST_NAME).exists())
        self.assertFalse((self.root / "never-fetched").exists())
        # The attempt is a normal live attempt for every lifecycle command.
        self.assertEqual(service.status(state.attempt_id), state)
        tested = service.test(state.attempt_id)
        self.assertEqual(tested.revision, 1)
        self.clock.value = START + timedelta(minutes=1)
        result = service.restart(state.attempt_id, operation_id=str(uuid4()), expected_revision=1)
        self.assertEqual(result.replacement_state.assessment, state.assessment)
        self.assertEqual(
            (self.attempts() / result.replacement_attempt_id / "level4.md").read_bytes(),
            ORIGINAL_CONTENT["level4.md"],
        )

    def test_tampered_or_incomplete_packages_are_rejected_before_any_mutation(self) -> None:
        manifest_path = self.package / PACKAGE_MANIFEST_NAME
        valid_manifest = manifest_path.read_text(encoding="utf-8")

        def restore() -> None:
            for name, data in ORIGINAL_CONTENT.items():
                (self.package / name).write_bytes(data)
            manifest_path.write_text(valid_manifest, encoding="utf-8")
            for stray in ("solution.py", "notes.md"):
                (self.package / stray).unlink(missing_ok=True)

        def tampered_manifest(**changes: object) -> None:
            data = json.loads(valid_manifest)
            data.update(changes)
            manifest_path.write_text(json.dumps(data), encoding="utf-8")

        cases = {
            "tampered file": (lambda: (self.package / "level2.md").write_bytes(b"changed\n"), "declared hash: level2.md"),
            "tampered manifest hash": (
                lambda: tampered_manifest(files={**json.loads(valid_manifest)["files"], "simulation.py": "0" * 64}),
                "declared hash: simulation.py",
            ),
            "missing prompt": (lambda: (self.package / "level3.md").unlink(), "missing packaged file: level3.md"),
            "development solution shipped": (lambda: (self.package / "solution.py").write_text("x"), "unexpected packaged file: solution.py"),
            "stray note shipped": (lambda: (self.package / "notes.md").write_text("x"), "unexpected packaged file: notes.md"),
            "wrong assessment": (lambda: tampered_manifest(assessment_id="file_storage"), "names another assessment"),
            "bad version": (lambda: tampered_manifest(content_version="Records 1"), "version is invalid"),
            "wrong schema": (lambda: tampered_manifest(schema_version="assessment-package/v9"), "schema version is unsupported"),
            "incomplete files": (
                lambda: tampered_manifest(files={k: v for k, v in json.loads(valid_manifest)["files"].items() if k != "level1.md"}),
                "declare every candidate-facing file",
            ),
            "manifest missing": (lambda: manifest_path.unlink(), "content manifest is missing"),
            "manifest unreadable": (lambda: manifest_path.write_text("{bad"), "content manifest is unreadable"),
        }
        for label, (mutate, message) in cases.items():
            with self.subTest(case=label):
                restore()
                mutate()
                service = self.service(self.manager(cache=self.missing_cache()))
                with self.assertRaisesRegex(FixtureSetupRequiredError, message):
                    service.start(ORIGINAL.metadata)
                self.assertFalse(self.attempts().exists())
        restore()
        # File Storage is unaffected by any of it.
        self.assertEqual(self.service().start(FILE_STORAGE.metadata).status, ACTIVE)

    def test_symlinked_packaged_content_is_rejected_at_every_level(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        for name, data in ORIGINAL_CONTENT.items():
            (outside / name).write_bytes(data)
        (outside / PACKAGE_MANIFEST_NAME).write_text(
            (self.package / PACKAGE_MANIFEST_NAME).read_text(encoding="utf-8"), encoding="utf-8"
        )
        manifest_text = (self.package / PACKAGE_MANIFEST_NAME).read_text(encoding="utf-8")

        def restore() -> None:
            if self.package_root.is_symlink():
                self.package_root.unlink()
                self.package_root.mkdir()
            assessments = self.package_root / "assessments"
            if assessments.is_symlink():
                assessments.unlink()
            write_package(self.package_root)
            for name in (*ORIGINAL_CONTENT, PACKAGE_MANIFEST_NAME):
                path = self.package / name
                if path.is_symlink():
                    path.unlink()
            for name, data in ORIGINAL_CONTENT.items():
                (self.package / name).write_bytes(data)
            (self.package / PACKAGE_MANIFEST_NAME).write_text(manifest_text, encoding="utf-8")

        def symlink_file(name: str) -> None:
            (self.package / name).unlink()
            os.symlink(outside / name, self.package / name)

        def symlink_final_directory() -> None:
            LocalFilesystem().remove_tree(self.package)
            os.symlink(outside, self.package)

        def symlink_intermediate_directory() -> None:
            LocalFilesystem().remove_tree(self.package_root / "assessments")
            (outside / "records_demo").mkdir(exist_ok=True)
            for name in (*ORIGINAL_CONTENT, PACKAGE_MANIFEST_NAME):
                (outside / "records_demo" / name).write_bytes((outside / name).read_bytes())
            os.symlink(outside, self.package_root / "assessments")

        cases = {
            "symlinked prompt": (lambda: symlink_file("level1.md"), "missing packaged file: level1.md"),
            "symlinked starter": (lambda: symlink_file("simulation.py"), "missing packaged file: simulation.py"),
            "symlinked manifest": (lambda: symlink_file(PACKAGE_MANIFEST_NAME), "content manifest is missing"),
            "symlinked directory": (symlink_final_directory, "packaged directory is missing"),
            "symlinked intermediate": (symlink_intermediate_directory, "packaged directory is missing"),
        }
        for label, (mutate, message) in cases.items():
            with self.subTest(case=label):
                restore()
                mutate()
                service = self.service(self.manager(cache=self.missing_cache()))
                with self.assertRaisesRegex(FixtureSetupRequiredError, message):
                    service.start(ORIGINAL.metadata)
                self.assertFalse(self.attempts().exists())
        restore()
        self.assertEqual(
            self.service(self.manager(cache=self.missing_cache())).start(ORIGINAL.metadata).status,
            ACTIVE,
        )

    def test_package_changed_after_validation_is_caught_on_staged_bytes(self) -> None:
        class SwapAfterReadFilesystem(LocalFilesystem):
            """Return tampered bytes for one packaged file at staging time only."""

            def __init__(self, target: Path) -> None:
                self.target = target
                self.reads = 0

            def read_bytes(self, path: Path) -> bytes:
                data = super().read_bytes(path)
                if path == self.target:
                    self.reads += 1
                    if self.reads > 1:  # first read is validation, second is staging
                        return b"swapped after validation\n"
                return data

        manager = self.manager(filesystem=SwapAfterReadFilesystem(self.package / "simulation.py"))

        with self.assertRaisesRegex(FixtureSetupRequiredError, "declared hash: simulation.py"):
            self.service(manager).start(ORIGINAL.metadata)

        # Only the workspace lock file exists: no attempt, no staging residue.
        self.assertEqual(
            [child.name for child in self.attempts().iterdir() if not child.name.endswith(".lock")],
            [],
        )
        self.assertIsNone(manager.persistence.read_active_pointer(self.attempts()))

    def test_restart_validates_packaged_inputs_before_touching_the_old_attempt(self) -> None:
        service = self.service(self.manager(cache=self.missing_cache()))
        state = service.start(ORIGINAL.metadata)
        (self.package / "level1.md").write_bytes(b"tampered\n")
        before = tree_snapshot(self.attempts())
        self.clock.value = START + timedelta(minutes=1)

        with self.assertRaisesRegex(FixtureSetupRequiredError, "declared hash: level1.md"):
            service.restart(state.attempt_id, operation_id=str(uuid4()), expected_revision=0)

        self.assertEqual(tree_snapshot(self.attempts()), before)
        self.assertEqual(service.status(state.attempt_id).status, ACTIVE)

    def test_invalid_profile_and_unknown_provider_fail_before_mutation(self) -> None:
        service = self.service()
        with self.assertRaises(InvalidInputError):
            service.start(ORIGINAL.metadata, mode="full", drill_duration_seconds=30)
        with self.assertRaises(InvalidInputError):
            service.start(ORIGINAL.metadata, mode="sprint")  # type: ignore[arg-type]
        only_fetched = InputProviders({PINNED_FETCHED: PinnedFetchedProvider(self.cache)})
        manager = WorkspaceManager(
            self.workspace_root, self.cache, registry=self.registry, providers=only_fetched
        )
        with self.assertRaisesRegex(FixtureSetupRequiredError, "no input provider"):
            LifecycleService(manager, self.clock, self.scorer).start(ORIGINAL.metadata)
        self.assertFalse(self.attempts().exists())
        with self.assertRaises(InvalidInputError):
            InputProviders({PACKAGED_ORIGINAL: PinnedFetchedProvider(self.cache)})
        with self.assertRaises(InvalidInputError):
            AssessmentDefinition(
                metadata=AssessmentMetadata("bad_kind", "Bad"),
                cache_directory="assessments/bad_kind",
                prompt_filenames=ORIGINAL.prompt_filenames,
                candidate_filename="simulation.py",
                test_filename="test_simulation.py",
                level_groups=(1, 2, 3, 4),
                profile_ids=ORIGINAL.profile_ids,
                provider_kind="downloaded",
            )
        with self.assertRaisesRegex(InvalidInputError, "duplicate input directories"):
            AssessmentRegistry(
                (ORIGINAL, AssessmentDefinition(
                    metadata=AssessmentMetadata("records_twin", "Twin"),
                    cache_directory=ORIGINAL.cache_directory,
                    prompt_filenames=ORIGINAL.prompt_filenames,
                    candidate_filename="simulation.py",
                    test_filename="test_simulation.py",
                    level_groups=(1, 2, 3, 4),
                    profile_ids=ORIGINAL.profile_ids,
                    provider_kind=PACKAGED_ORIGINAL,
                ))
            )

    def test_stored_results_stay_readable_when_the_definition_is_gone(self) -> None:
        service = self.service(self.manager(cache=self.missing_cache()))
        state = service.start(ORIGINAL.metadata)
        submitted = service.submit(state.attempt_id).state
        self.assertEqual(submitted.status, SUBMITTED)
        # Simulate a later install that no longer ships this exercise.
        without = WorkspaceManager(
            self.workspace_root,
            self.missing_cache(),
            registry=AssessmentRegistry((FILE_STORAGE,)),
            providers=InputProviders({PINNED_FETCHED: PinnedFetchedProvider(self.missing_cache())}),
        )
        blocked = LifecycleService(without, self.clock, self.scorer)
        before = tree_snapshot(self.attempts())

        with self.assertRaisesRegex(AssessmentVersionUnavailableError, "stored results remain reviewable"):
            blocked.status(state.attempt_id)
        review = AttemptReviewService(self.attempts()).get_review(state.attempt_id)
        listing = AttemptHistoryService(self.attempts(), clock=self.clock).list_attempts()

        self.assertEqual(review.assessment.content_version, "records-demo-1")
        self.assertEqual(review.source_binding, "captured")
        self.assertEqual([item.attempt_id for item in listing.items], [state.attempt_id])
        self.assertEqual(listing.items[0].assessment.assessment_id, "records_demo")
        self.assertEqual(tree_snapshot(self.attempts()), before)

        # A newer package version leaves the old pinned attempt unscorable but reviewable.
        write_package(self.package_root, version="records-demo-2")
        upgraded = self.service(self.manager(cache=self.missing_cache()))
        with self.assertRaises(AssessmentVersionUnavailableError):
            upgraded.status(state.attempt_id)
        fresh = upgraded.start(ORIGINAL.metadata)
        self.assertEqual(fresh.assessment.content_version, "records-demo-2")


class ApplicationProviderTests(ProviderTestCase):
    def test_application_starts_originals_offline_and_names_fetch_only_for_fetched(self) -> None:
        application = RuntimeApplication(
            self.workspace_root,
            clock=self.clock,
            cache=self.missing_cache(),
            registry=self.registry,
            providers=self.providers(self.missing_cache()),
            scorer_factory=lambda _definition: self.scorer,
        )

        with self.assertRaises(FixtureSetupRequiredError) as fetched:
            application.start(assessment="file_storage", mode="full", drill_duration_seconds=None)
        self.assertIn("codesignal-sim fetch", fetched.exception.message)
        self.assertFalse(self.attempts().exists())

        state = application.start(assessment="records_demo", mode="full", drill_duration_seconds=None)

        self.assertEqual(state.assessment.assessment_id, "records_demo")
        self.assertEqual(application.status(attempt_id=None).attempt_id, state.attempt_id)
        (self.package / "level1.md").write_bytes(b"tampered\n")
        application.abandon(attempt_id=state.attempt_id, expected_revision=0)
        with self.assertRaises(FixtureSetupRequiredError) as broken:
            application.start(assessment="records_demo", mode="full", drill_duration_seconds=None)
        self.assertNotIn("codesignal-sim fetch", broken.exception.message)

    def test_default_providers_serve_fetched_content_without_bundled_originals(self) -> None:
        # The production default has no bundled originals yet: fetched content
        # works, and a packaged definition fails closed instead of guessing.
        providers = InputProviders.default(self.cache)
        self.assertEqual(providers.for_definition(FILE_STORAGE).kind, PINNED_FETCHED)
        manager = WorkspaceManager(self.workspace_root, self.cache, registry=self.registry)
        with self.assertRaises(FixtureSetupRequiredError):
            LifecycleService(manager, self.clock, self.scorer).start(ORIGINAL.metadata)
        self.assertFalse(self.attempts().exists())


if __name__ == "__main__":
    unittest.main()
