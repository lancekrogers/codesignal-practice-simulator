"""Registry-driven catalog, its HTTP/CLI exposure, and packaging allowlists."""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_input_providers import (
    ORIGINAL,
    FakeClock,
    RecordingScorer,
    write_package,
)
from tests.workspace_test_support import (
    PROJECT,
    ValidatedFixtureCache,
    WorkspaceManager,
    make_cache,
    tree_snapshot,
)

try:
    from .web_server_test_support import WebServerTestCase
except ImportError:
    from web_server_test_support import WebServerTestCase

from codesignal_practice_simulator import cli
from codesignal_practice_simulator.application import RuntimeApplication
from codesignal_practice_simulator.assessments import (
    DRILL_PROFILE,
    FILE_STORAGE,
    FULL_PROFILE,
    PACKAGED_ORIGINAL,
    PINNED_FETCHED,
    AssessmentDefinition,
    AssessmentRegistry,
)
from codesignal_practice_simulator.catalog import (
    FETCH_REQUIRED,
    PACKAGED_CONTENT_INVALID,
    PROVIDER_UNAVAILABLE,
    CatalogService,
)
from codesignal_practice_simulator.errors import InvalidInputError
from codesignal_practice_simulator.input_providers import (
    PACKAGE_MANIFEST_NAME,
    InputProviders,
    PackagedOriginalProvider,
    PinnedFetchedProvider,
)
from codesignal_practice_simulator.models import AssessmentMetadata

sys.path.insert(0, str(PROJECT / "scripts"))
import run_packaged_browser  # noqa: E402


PACKAGE = run_packaged_browser.PACKAGE_NAME


class CatalogTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workspace_root = self.root / "workspace"
        self.workspace_root.mkdir()
        self.package_root = self.root / "resources"
        self.package = write_package(self.package_root)
        self.cache: ValidatedFixtureCache = make_cache(self.root)
        self.registry = AssessmentRegistry((FILE_STORAGE, ORIGINAL))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def missing_cache(self) -> ValidatedFixtureCache:
        return ValidatedFixtureCache(
            self.root / "never-fetched", dict(self.cache.hashes), "upstream-0000000"
        )

    def providers(self, cache: ValidatedFixtureCache) -> InputProviders:
        return InputProviders(
            {
                PINNED_FETCHED: PinnedFetchedProvider(cache),
                PACKAGED_ORIGINAL: PackagedOriginalProvider(self.package_root),
            }
        )

    def manager(self, cache: ValidatedFixtureCache) -> WorkspaceManager:
        return WorkspaceManager(
            self.workspace_root, cache, registry=self.registry, providers=self.providers(cache)
        )


class CatalogEnumerationTests(CatalogTestCase):
    def test_catalog_reports_readiness_per_provider_without_side_effects(self) -> None:
        before = tree_snapshot(self.root)

        catalog = CatalogService(self.manager(self.missing_cache())).list_assessments()

        self.assertEqual(tree_snapshot(self.root), before)
        self.assertFalse((self.workspace_root / "attempts").exists())
        by_id = {entry.assessment_id: entry for entry in catalog.entries}
        self.assertEqual(list(by_id), ["file_storage", "records_demo"])  # stable ID order
        fetched = by_id["file_storage"]
        self.assertEqual((fetched.available, fetched.setup), (False, FETCH_REQUIRED))
        self.assertIn("codesignal-sim fetch", fetched.setup_message)
        self.assertEqual(fetched.provider_kind, PINNED_FETCHED)
        # Identity is declared by the manifest, so it is known even before fetch.
        self.assertEqual(fetched.content_version, "upstream-0000000")
        self.assertEqual(fetched.content_digest, self.cache.pinned_assessment(FILE_STORAGE).content_digest)
        original = by_id["records_demo"]
        self.assertEqual((original.available, original.setup, original.setup_message), (True, None, None))
        self.assertEqual(original.content_version, "records-demo-1")
        self.assertEqual(original.provider_kind, PACKAGED_ORIGINAL)
        self.assertEqual(original.description, ORIGINAL.description)
        self.assertEqual([level["level"] for level in original.to_dict()["levels"]], [1, 2, 3, 4])
        self.assertEqual(
            [profile["profile_id"] for profile in original.to_dict()["profiles"]],
            [FULL_PROFILE, DRILL_PROFILE],
        )
        document = json.dumps(catalog.to_dict())
        self.assertNotIn(str(self.root), document)

        # With the cache fetched, File Storage becomes available.
        fetched_ready = {
            entry.assessment_id: entry
            for entry in CatalogService(self.manager(self.cache)).list_assessments().entries
        }
        self.assertTrue(fetched_ready["file_storage"].available)

    def test_tampered_or_unprovided_content_is_reported_not_hidden(self) -> None:
        (self.package / "level2.md").write_bytes(b"tampered\n")
        tampered = {
            entry.assessment_id: entry
            for entry in CatalogService(self.manager(self.cache)).list_assessments().entries
        }
        self.assertEqual(tampered["records_demo"].available, False)
        self.assertEqual(tampered["records_demo"].setup, PACKAGED_CONTENT_INVALID)
        self.assertNotIn(str(self.root), tampered["records_demo"].setup_message)
        # Identity is still declared by the manifest even when bytes disagree.
        self.assertEqual(tampered["records_demo"].content_version, "records-demo-1")

        (self.package / PACKAGE_MANIFEST_NAME).unlink()
        no_manifest = {
            entry.assessment_id: entry
            for entry in CatalogService(self.manager(self.cache)).list_assessments().entries
        }
        self.assertEqual(no_manifest["records_demo"].setup, PACKAGED_CONTENT_INVALID)
        self.assertIsNone(no_manifest["records_demo"].content_version)

        without_provider = WorkspaceManager(
            self.workspace_root,
            self.cache,
            registry=self.registry,
            providers=InputProviders({PINNED_FETCHED: PinnedFetchedProvider(self.cache)}),
        )
        unprovided = {
            entry.assessment_id: entry
            for entry in CatalogService(without_provider).list_assessments().entries
        }
        self.assertEqual(unprovided["records_demo"].setup, PROVIDER_UNAVAILABLE)
        self.assertTrue(unprovided["file_storage"].available)

    def test_duplicate_identity_and_wrong_profiles_never_reach_the_catalog(self) -> None:
        with self.assertRaisesRegex(InvalidInputError, "duplicate IDs"):
            AssessmentRegistry((FILE_STORAGE, FILE_STORAGE))
        twin = AssessmentDefinition(
            metadata=AssessmentMetadata("records_demo", "Twin"),
            cache_directory="assessments/records_twin",
            prompt_filenames=ORIGINAL.prompt_filenames,
            candidate_filename="simulation.py",
            test_filename="test_simulation.py",
            level_groups=(1, 2, 3, 4),
            profile_ids=ORIGINAL.profile_ids,
            provider_kind=PACKAGED_ORIGINAL,
        )
        with self.assertRaisesRegex(InvalidInputError, "duplicate IDs"):
            AssessmentRegistry((ORIGINAL, twin))
        for profiles in (frozenset((FULL_PROFILE,)), frozenset((FULL_PROFILE, DRILL_PROFILE, "sprint-5m"))):
            with self.assertRaisesRegex(InvalidInputError, "profiles are invalid"):
                AssessmentDefinition(
                    metadata=AssessmentMetadata("bad_profiles", "Bad"),
                    cache_directory="assessments/bad_profiles",
                    prompt_filenames=ORIGINAL.prompt_filenames,
                    candidate_filename="simulation.py",
                    test_filename="test_simulation.py",
                    level_groups=(1, 2, 3, 4),
                    profile_ids=profiles,
                    provider_kind=PACKAGED_ORIGINAL,
                )
        with self.assertRaisesRegex(InvalidInputError, "groups 1 through 4"):
            AssessmentDefinition(
                metadata=AssessmentMetadata("bad_groups", "Bad"),
                cache_directory="assessments/bad_groups",
                prompt_filenames=ORIGINAL.prompt_filenames,
                candidate_filename="simulation.py",
                test_filename="test_simulation.py",
                level_groups=(1, 2, 3),
                profile_ids=ORIGINAL.profile_ids,
                provider_kind=PACKAGED_ORIGINAL,
            )


class CatalogTransportTests(CatalogTestCase):
    def test_cli_catalog_and_application_agree(self) -> None:
        application = RuntimeApplication(
            self.workspace_root,
            clock=FakeClock(),
            cache=self.missing_cache(),
            registry=self.registry,
            providers=self.providers(self.missing_cache()),
            scorer_factory=lambda _definition: RecordingScorer(),
        )
        output = io.StringIO()
        code = cli.execute(
            ["catalog", "--workspace-root", str(self.workspace_root), "--json"],
            application_factory=lambda _root: application,
            output=output,
        )
        self.assertEqual(code, 0)
        document = json.loads(output.getvalue())
        self.assertEqual(document["result"], application.catalog().to_dict())
        entries = {entry["assessment_id"]: entry for entry in document["result"]["assessments"]}
        self.assertEqual(entries["records_demo"]["available"], True)
        self.assertEqual(entries["file_storage"]["setup"], FETCH_REQUIRED)
        bootstrap = application.bootstrap()
        self.assertEqual(bootstrap["assessment"]["assessment_id"], "file_storage")
        self.assertEqual([entry["assessment_id"] for entry in bootstrap["catalog"]], ["file_storage", "records_demo"])
        self.assertFalse((self.workspace_root / "attempts").exists())


class CatalogRouteTests(WebServerTestCase):
    def test_catalog_route_is_read_only_and_authorized(self) -> None:
        attempt, _etag = self.start_attempt()
        before = tree_snapshot(self.workspace / "attempts")

        status, _headers, document = self.request("GET", "/api/catalog")
        self.assertEqual(status, 200)
        assessments = document["data"]["assessments"]
        # The default registry: fetched File Storage plus the two bundled originals.
        self.assertEqual(
            [entry["assessment_id"] for entry in assessments],
            ["account_ledger", "file_storage", "in_memory_records"],
        )
        by_id = {entry["assessment_id"]: entry for entry in assessments}
        self.assertTrue(all(entry["available"] for entry in assessments), assessments)
        self.assertEqual(by_id["file_storage"]["content_version"], "upstream-0000000")
        self.assertEqual(by_id["in_memory_records"]["provider_kind"], "packaged-original")
        self.assertNotIn(str(self.workspace), json.dumps(document))

        status, _headers, bootstrap = self.request("GET", "/api/bootstrap")
        self.assertEqual(status, 200)
        self.assertEqual(bootstrap["data"]["catalog"], assessments)
        self.assertEqual(bootstrap["data"]["assessment"]["assessment_id"], "file_storage")
        self.assertEqual(bootstrap["data"]["session"]["attempt_id"], attempt)

        status, _headers, denied = self.request("GET", "/api/catalog", token=None)
        self.assertEqual((status, denied["error"]["code"]), (401, "unauthorized"))
        status, _headers, wrong = self.request("POST", "/api/catalog", body={}, origin=self.origin)
        self.assertEqual(status, 405)
        status, _headers, bad = self.request("GET", "/api/catalog?x=1")
        self.assertEqual((status, bad["error"]["code"]), (400, "invalid_query"))
        self.assertEqual(tree_snapshot(self.workspace / "attempts"), before)


class PackagingAllowlistTests(unittest.TestCase):
    def check(self, members: list[str]) -> None:
        run_packaged_browser._assert_runtime_package_resources(
            members, prefix=f"{PACKAGE}/", static_prefix=run_packaged_browser.STATIC_PREFIX
        )

    def test_bundled_assessment_members_are_allowlisted_exactly(self) -> None:
        good = [
            f"{PACKAGE}/resources/assessments/records_demo/{name}"
            for name in run_packaged_browser.PACKAGED_ASSESSMENT_MEMBERS
        ] + [f"{PACKAGE}/resources/fixture-manifest.json", f"{PACKAGE}/__init__.py"]
        self.check(good)

        rejected = (
            "resources/assessments/records_demo/solution.py",
            "resources/assessments/records_demo/notes.md",
            "resources/assessments/records_demo/README.md",
            "resources/assessments/records_demo/nested/level1.md",
            "resources/assessments/level1.md",
            "resources/assessments/Records_Demo/level1.md",
            "resources/assessments/../level1.md",
            "resources/assessments/.hidden/level1.md",
        )
        for member in rejected:
            with self.subTest(member=member):
                with self.assertRaisesRegex(RuntimeError, "unexpected packaged assessment member"):
                    self.check([f"{PACKAGE}/{member}"])

    def test_archive_paths_reject_development_oracles(self) -> None:
        good = [f"{PACKAGE}/__init__.py", f"{PACKAGE}/resources/assessments/records_demo/simulation.py"]
        run_packaged_browser._assert_archive_paths(good)
        for member in (
            "package-0.1/tests/oracles/__init__.py",
            f"{PACKAGE}/account_ledger_reference.py",
            f"{PACKAGE}/resources/assessments/records_demo/records_solution.py",
        ):
            with self.subTest(member=member):
                with self.assertRaisesRegex(RuntimeError, "forbidden path|development oracle"):
                    run_packaged_browser._assert_archive_paths([member])

    def test_pyproject_ships_bundled_assessment_data(self) -> None:
        configuration = (PROJECT / "pyproject.toml").read_text(encoding="utf-8")
        for pattern in (
            '"resources/assessments/*/*.md"',
            '"resources/assessments/*/*.py"',
            '"resources/assessments/*/*.json"',
        ):
            self.assertIn(pattern, configuration)

    def test_installed_provider_locates_the_resources_package_as_files(self) -> None:
        provider = PackagedOriginalProvider.installed()
        self.assertTrue(provider.root.is_dir())
        self.assertEqual(provider.root.name, "resources")
        self.assertTrue((provider.root / "fixture-manifest.json").is_file())


if __name__ == "__main__":
    unittest.main()
