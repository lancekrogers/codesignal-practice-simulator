"""Bundled original exercises: packaging, runner contract, and correctness proofs."""

from __future__ import annotations

import hashlib
import importlib
import json
import sys
import tempfile
import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from tests.workspace_test_support import PROJECT, ValidatedFixtureCache, WorkspaceManager

from codesignal_practice_simulator.assessments import (
    ACCOUNT_LEDGER,
    DEFAULT_ASSESSMENT_REGISTRY,
    IN_MEMORY_RECORDS,
    PACKAGED_ORIGINAL,
    AssessmentDefinition,
    AssessmentMetadata,
)
from codesignal_practice_simulator.catalog import CatalogService
from codesignal_practice_simulator.input_providers import (
    PACKAGE_MANIFEST_NAME,
    PackagedOriginalProvider,
)
from codesignal_practice_simulator.lifecycle import LifecycleService
from codesignal_practice_simulator.models import ACTIVE, LevelResult, ScoreSummary
from codesignal_practice_simulator.scoring import IsolatedAttemptScorer

sys.path.insert(0, str(PROJECT / "scripts"))
import check_content  # noqa: E402

from tests.oracles import account_ledger_reference, in_memory_records_reference  # noqa: E402


RESOURCES = PROJECT / "src" / "codesignal_practice_simulator" / "resources"
START = datetime(2026, 9, 8, 19, tzinfo=timezone.utc)


class FakeClock:
    def now(self) -> datetime:
        return START


@dataclass(frozen=True)
class Mutant:
    """A deliberately wrong implementation derived from the reference."""

    label: str
    old: str
    new: str
    first_failing_group: int


@dataclass(frozen=True)
class Track:
    definition: AssessmentDefinition
    reference: object
    mutants: tuple[Mutant, ...]
    spec_examples: tuple[tuple[list[list[str]], list[str]], ...]

    @property
    def directory(self) -> Path:
        return RESOURCES.joinpath(*self.definition.cache_directory.split("/"))

    @property
    def reference_source(self) -> str:
        return Path(self.reference.__file__).read_text(encoding="utf-8")


def _q(text: str) -> list[list[str]]:
    return [line.split() for line in text.strip().splitlines() if line.strip()]


TRACKS = (
    Track(
        IN_MEMORY_RECORDS,
        in_memory_records_reference,
        (
            Mutant(
                "scan order ignores case",
                "names = sorted(name for name in live if name.startswith(prefix))  # SCAN_ORDER",
                "names = sorted((name for name in live if name.startswith(prefix)), key=str.lower)",
                2,
            ),
            Mutant(
                "expiry is inclusive",
                "if expiry is None or now < expiry  # EXPIRY_RULE",
                "if expiry is None or now <= expiry",
                3,
            ),
            Mutant(
                "restore does not rebase lifetimes",
                "for name, (value, remaining) in fields.items()\n            }\n            for record, fields in chosen.items()",
                "for name, (value, remaining) in fields.items()\n            }\n            for record, fields in chosen.items()\n        }\n        self.records = {\n            record: {\n                name: (value, None if remaining is None else at + remaining)\n                for name, (value, remaining) in fields.items()\n            }\n            for record, fields in chosen.items()",
                4,
            ),
        ),
        (
            (
                _q("""
                SET users alice admin
                GET users alice
                DELETE users alice
                DELETE users alice
                """),
                ["true", "admin", "true", "false"],
            ),
            (
                _q("""
                SET_AT_WITH_TTL 1 r x 1 10
                SET_AT 2 r y 2
                BACKUP 5
                RESTORE 20 6
                SCAN_AT 20 r
                GET_AT 26 r x
                """),
                ["true", "false", "1", "true", "x(1), y(2)", ""],
            ),
        ),
    ),
    Track(
        ACCOUNT_LEDGER,
        account_ledger_reference,
        (
            Mutant(
                "ties keep insertion order",
                "key=lambda item: (-item[1].outgoing, item[0]))  # RANK_KEY",
                "key=lambda item: -item[1].outgoing)",
                2,
            ),
            Mutant(
                "schedules execute strictly after their time",
                "schedule.execute_at <= now),  # SCHEDULE_DUE",
                "schedule.execute_at < now),",
                3,
            ),
            Mutant(
                "history excludes changes at the query time",
                "if changed_at <= at:  # HISTORY_RULE",
                "if changed_at < at:",
                4,
            ),
            Mutant(
                "schedules ordered by number instead of due time",
                "key=lambda schedule: (schedule.execute_at, schedule.number),",
                "key=lambda schedule: schedule.number,",
                3,
            ),
            Mutant(
                "closing an account cancels the heir's schedules too",
                'if schedule.source == account and schedule.status == "PENDING":',
                'if schedule.source in (account, heir) and schedule.status == "PENDING":',
                4,
            ),
            Mutant(
                "a schedule to a closed target is treated as executed",
                "            if source is None or target is None or source.balance < schedule.amount:\n"
                '                schedule.status = "FAILED"\n'
                "                continue",
                "            if source is None or source.balance < schedule.amount:\n"
                '                schedule.status = "FAILED"\n'
                "                continue\n"
                "            if target is None:\n"
                '                schedule.status = "EXECUTED"\n'
                "                continue",
                4,
            ),
        ),
        (
            (
                _q("""
                CREATE_ACCOUNT 1 acc1
                DEPOSIT 3 acc1 500
                TRANSFER 4 acc1 acc1 1
                """),
                ["true", "500", ""],
            ),
            (
                _q("""
                CREATE_ACCOUNT 1 src
                CREATE_ACCOUNT 1 dst
                DEPOSIT 2 src 100
                SCHEDULE_TRANSFER 3 src dst 60 10
                TRANSFER 10 src dst 1
                GET_SCHEDULE_STATUS 10 src schedule1
                """),
                ["true", "true", "100", "schedule1", "39", "EXECUTED"],
            ),
        ),
    ),
)


def _apply(source: str, mutant: Mutant) -> str:
    if source.count(mutant.old) != 1:
        raise AssertionError(f"mutation anchor not unique for {mutant.label}")
    return source.replace(mutant.old, mutant.new)


def _outcomes(score: ScoreSummary) -> list[str]:
    return [result.outcome for result in score.levels]


class PackagedContentTests(unittest.TestCase):
    def test_bundled_directories_satisfy_the_content_contract(self) -> None:
        checked = check_content.check_bundled_content(RESOURCES)
        self.assertEqual(sorted(checked), ["account_ledger", "in_memory_records"])
        self.assertEqual(checked["in_memory_records"]["content_version"], "records-1")
        self.assertEqual(checked["account_ledger"]["content_version"], "ledger-1")
        provider = PackagedOriginalProvider.installed()
        for track in TRACKS:
            with self.subTest(track=track.definition.metadata.assessment_id):
                provider.validate(track.definition, WorkspaceManager.__init__.__globals__["LocalFilesystem"]())
                pinned = provider.pinned_assessment(track.definition)
                manifest = json.loads((track.directory / PACKAGE_MANIFEST_NAME).read_text())
                self.assertEqual(pinned.content_version, manifest["content_version"])
                for name, digest in manifest["files"].items():
                    self.assertEqual(hashlib.sha256((track.directory / name).read_bytes()).hexdigest(), digest)
                for prompt in track.definition.prompt_filenames:
                    text = (track.directory / prompt).read_text(encoding="utf-8")
                    self.assertIn(track.definition.metadata.display_name, text)
                    self.assertNotIn("CodeSignal", text)
                    self.assertNotIn("CP0002", text)
                self.assertIn("return []", (track.directory / "simulation.py").read_text())

    def test_content_check_rejects_a_renamed_group_a_stray_file_and_a_stale_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "resources"
            for track in TRACKS:
                target = root / "assessments" / track.definition.metadata.assessment_id
                target.mkdir(parents=True)
                for path in track.directory.iterdir():
                    (target / path.name).write_bytes(path.read_bytes())
            check_content.check_bundled_content(root)

            ledger = root / "assessments" / "account_ledger"
            tests = ledger / "test_simulation.py"
            original = tests.read_text(encoding="utf-8")
            tests.write_text(original.replace("def test_group_4", "def test_level_4"), encoding="utf-8")
            with self.assertRaisesRegex(check_content.ContentCheckError, "must define exactly"):
                check_content.check_bundled_content(root)
            tests.write_text(original, encoding="utf-8")

            (ledger / "solution.py").write_text("print('oracle')\n", encoding="utf-8")
            with self.assertRaisesRegex(check_content.ContentCheckError, "must be exactly"):
                check_content.check_bundled_content(root)
            (ledger / "solution.py").unlink()

            (ledger / "level2.md").write_text("changed\n", encoding="utf-8")
            with self.assertRaisesRegex(check_content.ContentCheckError, "hash mismatch for level2.md"):
                check_content.check_bundled_content(root)

            tests.write_text(original.replace("import unittest", "import unittest\nimport os"), encoding="utf-8")
            with self.assertRaisesRegex(check_content.ContentCheckError, "imports \\['os'\\]"):
                check_content.check_bundled_content(root)

    def test_registry_and_catalog_expose_the_originals_offline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            workspace.mkdir()
            never_fetched = ValidatedFixtureCache(
                Path(directory) / "never-fetched",
                {path: "0" * 64 for path in (
                    "vendor-readme.md",
                    *(f"assessment/file_storage/{name}" for name in (
                        "level1.md", "level2.md", "level3.md", "level4.md", "simulation.py", "test_simulation.py"
                    )),
                )},
                "upstream-0000000",
            )
            manager = WorkspaceManager(workspace, never_fetched)
            catalog = {entry.assessment_id: entry for entry in CatalogService(manager).list_assessments().entries}
        self.assertEqual(sorted(catalog), ["account_ledger", "file_storage", "in_memory_records"])
        self.assertFalse(catalog["file_storage"].available)
        for assessment_id in ("in_memory_records", "account_ledger"):
            self.assertTrue(catalog[assessment_id].available, catalog[assessment_id].setup_message)
            self.assertEqual(catalog[assessment_id].provider_kind, PACKAGED_ORIGINAL)
        self.assertIs(DEFAULT_ASSESSMENT_REGISTRY.require("in_memory_records"), IN_MEMORY_RECORDS)


class CorrectnessTests(unittest.TestCase):
    """Score real attempts with the isolated scorer: starter, reference, mutants."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.cache = ValidatedFixtureCache(
            self.root / "never-fetched",
            {path: "0" * 64 for path in (
                "vendor-readme.md",
                *(f"assessment/file_storage/{name}" for name in (
                    "level1.md", "level2.md", "level3.md", "level4.md", "simulation.py", "test_simulation.py"
                )),
            )},
            "upstream-0000000",
        )
        self.manager = WorkspaceManager(self.workspace, self.cache)
        self.service = LifecycleService(self.manager, FakeClock(), None)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def attempt(self, track: Track, source: str | None = None) -> tuple[Path, IsolatedAttemptScorer]:
        state = self.service.start(track.definition.metadata)
        attempt = self.workspace / "attempts" / state.attempt_id
        if source is not None:
            (attempt / "simulation.py").write_text(source, encoding="utf-8")
        return attempt, IsolatedAttemptScorer(track.definition, timeout_seconds=30.0)

    def test_starter_fails_every_group_and_reference_passes_every_group(self) -> None:
        for track in TRACKS:
            with self.subTest(track=track.definition.metadata.assessment_id):
                attempt, scorer = self.attempt(track)
                self.assertEqual(_outcomes(scorer.score(attempt)), ["failed"] * 4)
                self.assertEqual(self.manager.persistence.read_session(attempt).status, ACTIVE)

                attempt, scorer = self.attempt(track, track.reference_source)
                first = scorer.score(attempt)
                second = scorer.score(attempt)
                self.assertEqual(_outcomes(first), ["passed"] * 4)
                self.assertEqual(first, second)  # deterministic

    def test_wrong_implementations_fail_from_their_level_onward_only(self) -> None:
        for track in TRACKS:
            for mutant in track.mutants:
                with self.subTest(track=track.definition.metadata.assessment_id, mutant=mutant.label):
                    attempt, scorer = self.attempt(track, _apply(track.reference_source, mutant))
                    outcomes = _outcomes(scorer.score(attempt))
                    self.assertEqual(
                        outcomes[: mutant.first_failing_group - 1],
                        ["passed"] * (mutant.first_failing_group - 1),
                        outcomes,
                    )
                    self.assertEqual(outcomes[mutant.first_failing_group - 1], "failed", outcomes)

    def test_reference_matches_the_specification_examples_and_rejects_bad_input(self) -> None:
        for track in TRACKS:
            with self.subTest(track=track.definition.metadata.assessment_id):
                simulate = track.reference.simulate
                for queries, expected in track.spec_examples:
                    self.assertEqual(simulate(queries), expected)
                    self.assertEqual(simulate(queries), expected)
                self.assertEqual(simulate([]), [])
                with self.assertRaises(ValueError):
                    simulate([["NOPE"]])
                with self.assertRaises(ValueError):
                    simulate([[]])

    def test_an_erroring_candidate_is_an_error_not_a_hang(self) -> None:
        track = TRACKS[0]
        attempt, scorer = self.attempt(track, "def simulate(queries):\n    raise RuntimeError('boom')\n")
        self.assertEqual(_outcomes(scorer.score(attempt)), ["error"] * 4)


if __name__ == "__main__":
    unittest.main()
