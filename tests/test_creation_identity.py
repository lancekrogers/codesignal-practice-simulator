"""Pinned content identity at creation and lifecycle parity across schemas."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from tests.workspace_test_support import (
    CACHE_INPUTS,
    PROJECT,
    ValidatedFixtureCache,
    WorkspaceManager,
    make_cache,
    session,
    submitted_with_review,
    tree_snapshot,
)

from codesignal_practice_simulator.assessments import (
    CONTENT_IDENTITY_SCHEMA_VERSION,
    FILE_STORAGE,
    RUNNER_CONTRACT,
    content_identity,
)
from codesignal_practice_simulator.cli import serialize_result
from codesignal_practice_simulator.errors import (
    AssessmentVersionUnavailableError,
    FixtureSetupRequiredError,
    InvalidInputError,
    SessionUnavailableError,
    UnsupportedSchemaVersionError,
)
from codesignal_practice_simulator.filesystem import LocalFilesystem
from codesignal_practice_simulator.lifecycle import LifecycleService
from codesignal_practice_simulator.models import (
    EVENT_SCHEMA_VERSION,
    EVENT_SCHEMA_VERSION_V2,
    EXPIRED,
    FULL_DURATION_SECONDS,
    SESSION_SCHEMA_VERSION,
    SESSION_SCHEMA_VERSION_V2,
    SUBMISSION_RECOVERY_SCHEMA_VERSION,
    SUBMISSION_RECOVERY_SCHEMA_VERSION_V2,
    SUBMITTED,
    AssessmentMetadata,
    LevelResult,
    ReviewSource,
    ScoreSummary,
    SessionState,
    SessionStateV2,
    SubmissionRecovery,
    adapt_session_record,
    session_event,
)
from codesignal_practice_simulator.persistence import (
    SUBMISSION_RECOVERY_FILENAME,
    Persistence,
)
from codesignal_practice_simulator.rendering import (
    AttemptContextService,
    load_attempt_context,
    render_markdown,
)
from codesignal_practice_simulator.workspace_cache import _EXPECTED_CACHE_PATHS


# workspace_test_support.session() starts every legacy fixture at this instant.
LEGACY_START = datetime(2026, 9, 8, 19, tzinfo=timezone.utc)
FILE_STORAGE_METADATA = AssessmentMetadata("file_storage", "File Storage")


class FakeClock:
    def __init__(self, value: datetime = LEGACY_START) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


class RecordingScorer:
    def __init__(self) -> None:
        self.calls: list[Path] = []

    def __call__(self, attempt: Path) -> ScoreSummary:
        self.calls.append(attempt)
        return ScoreSummary(
            tuple(LevelResult(level, "passed" if level < 3 else "failed") for level in range(1, 5))
        )


class TamperedCopyFilesystem(LocalFilesystem):
    """Simulate the cache changing after validation but before one staged copy."""

    def __init__(self, filename: str) -> None:
        self.filename = filename

    def copyfile(self, source: Path, destination: Path) -> None:
        super().copyfile(source, destination)
        if destination.name == self.filename:
            destination.write_bytes(b"changed after validation\n")


class FailOnceFilesystem(LocalFilesystem):
    """Fail one durable operation on one filename, optionally after it succeeds."""

    def __init__(self, operation: str, filename: str, *, after: bool = False) -> None:
        self.operation = operation
        self.filename = filename
        self.after = after
        self.failed = False

    def _should_fail(self, operation: str, path: Path) -> bool:
        return (
            not self.failed
            and operation == self.operation
            and path.name == self.filename
        )

    def replace(self, source: Path, destination: Path) -> None:
        if self._should_fail("replace", destination):
            self.failed = True
            if self.after:
                super().replace(source, destination)
            raise OSError(f"injected replace failure for {self.filename}")
        super().replace(source, destination)

    def unlink(self, path: Path) -> None:
        if self._should_fail("unlink", path):
            self.failed = True
            raise OSError(f"injected unlink failure for {self.filename}")
        super().unlink(path)


class EventUnavailableFilesystem(LocalFilesystem):
    """Make every events.jsonl append and replacement fail."""

    def append_bytes(self, path: Path, data: bytes) -> None:
        if path.name == "events.jsonl":
            raise OSError("injected event append failure")
        super().append_bytes(path, data)

    def replace(self, source: Path, destination: Path) -> None:
        if destination.name == "events.jsonl":
            raise OSError("injected event replacement failure")
        super().replace(source, destination)


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _event_versions(attempt: Path) -> list[tuple[str, str]]:
    return [
        (record["schema_version"], record["name"])
        for record in (
            json.loads(line)
            for line in (attempt / "events.jsonl").read_text(encoding="utf-8").splitlines()
        )
    ]


class IdentityTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workspace_root = self.root / "workspace"
        self.workspace_root.mkdir()
        self.cache = make_cache(self.root)
        self.clock = FakeClock()
        self.scorer = RecordingScorer()
        self.manager = WorkspaceManager(self.workspace_root, self.cache)
        self.service = LifecycleService(self.manager, self.clock, self.scorer)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def use_filesystem(self, filesystem: LocalFilesystem) -> Persistence:
        persistence = Persistence(filesystem)
        self.manager.filesystem = filesystem
        self.manager.persistence = persistence
        self.service.persistence = persistence
        return persistence

    def attempt(self, attempt_id: str) -> Path:
        return self.workspace_root / "attempts" / attempt_id


class ContentIdentityTests(IdentityTestCase):
    def file_hashes(self) -> dict[str, str]:
        return {
            name: self.cache.hashes[f"assessment/file_storage/{name}"]
            for name in CACHE_INPUTS
        }

    def test_digest_is_an_independent_hash_of_every_declared_input(self) -> None:
        pinned = self.cache.pinned_assessment(FILE_STORAGE)
        document = {
            "schema_version": CONTENT_IDENTITY_SCHEMA_VERSION,
            "assessment_id": "file_storage",
            "content_version": "upstream-0000000",
            "runner_contract": RUNNER_CONTRACT,
            "files": [
                {"path": name, "sha256": digest}
                for name, digest in sorted(self.file_hashes().items())
            ],
        }
        expected = hashlib.sha256(
            json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        self.assertEqual(pinned.content_digest, expected)
        self.assertEqual(pinned.content_version, "upstream-0000000")
        self.assertEqual(self.cache.pinned_assessment(FILE_STORAGE), pinned)
        self.assertNotIn(
            hashlib.sha256(b"vendor readme\n").hexdigest(),
            {entry["sha256"] for entry in document["files"]},
        )

    def test_any_changed_hash_or_version_changes_the_digest(self) -> None:
        baseline = content_identity(
            FILE_STORAGE,
            content_version="upstream-0000000",
            file_hashes=self.file_hashes(),
        ).content_digest
        for name in CACHE_INPUTS:
            with self.subTest(changed=name):
                changed = dict(self.file_hashes(), **{name: "f" * 64})
                self.assertNotEqual(
                    content_identity(
                        FILE_STORAGE,
                        content_version="upstream-0000000",
                        file_hashes=changed,
                    ).content_digest,
                    baseline,
                )
        self.assertNotEqual(
            content_identity(
                FILE_STORAGE,
                content_version="upstream-1111111",
                file_hashes=self.file_hashes(),
            ).content_digest,
            baseline,
        )

    def test_incomplete_or_malformed_file_hashes_are_rejected(self) -> None:
        hashes = self.file_hashes()
        cases = {
            "missing": {key: value for key, value in hashes.items() if key != "level4.md"},
            "extra": dict(hashes, **{"solution.py": "a" * 64}),
            "uppercase": dict(hashes, **{"level1.md": "A" * 64}),
            "short": dict(hashes, **{"level1.md": "a" * 63}),
        }
        for label, candidate in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(InvalidInputError):
                    content_identity(
                        FILE_STORAGE,
                        content_version="upstream-0000000",
                        file_hashes=candidate,
                    )

    def test_project_and_packaged_manifests_pin_the_same_file_storage_identity(self) -> None:
        project = ValidatedFixtureCache.from_manifest(
            PROJECT / "docs" / "migration-manifest.json"
        )
        packaged = ValidatedFixtureCache.from_runtime_manifest(self.workspace_root)

        self.assertEqual(project.content_version, "upstream-6aab304")
        self.assertEqual(
            project.pinned_assessment(FILE_STORAGE),
            packaged.pinned_assessment(FILE_STORAGE),
        )

    def test_manifest_without_a_pinned_hex_commit_is_setup_required(self) -> None:
        fetches = [
            {"cache_path": path, "sha256": "a" * 64} for path in sorted(_EXPECTED_CACHE_PATHS)
        ]
        manifest_path = self.root / "project" / "docs" / "manifest.json"
        manifest_path.parent.mkdir(parents=True)
        upstreams: dict[str, object] = {
            "absent": None,
            "no-commit": {"repository": "example/fixtures"},
            "word": {"commit": "synthetic"},
            "uppercase": {"commit": "ABCDEF1"},
            "short": {"commit": "abc12"},
            "number": {"commit": 1234567},
        }
        for label, upstream in upstreams.items():
            with self.subTest(label=label):
                manifest: dict[str, object] = {
                    "fixture_cache_root": "cache",
                    "fetches": fetches,
                }
                if upstream is not None:
                    manifest["upstream"] = upstream
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                with self.assertRaisesRegex(
                    FixtureSetupRequiredError, "does not pin an upstream commit"
                ):
                    ValidatedFixtureCache.from_manifest(manifest_path)

        manifest_path.write_text(
            json.dumps(
                {
                    "fixture_cache_root": "cache",
                    "fetches": fetches,
                    "upstream": {"commit": "0123abc"},
                }
            ),
            encoding="utf-8",
        )
        self.assertEqual(
            ValidatedFixtureCache.from_manifest(manifest_path).content_version,
            "upstream-0123abc",
        )
        with self.assertRaises(FixtureSetupRequiredError):
            ValidatedFixtureCache(self.cache.root, self.cache.hashes, "v1")

    def test_unversioned_cache_refuses_creation_before_any_mutation(self) -> None:
        unversioned = ValidatedFixtureCache(self.cache.root, dict(self.cache.hashes))
        manager = WorkspaceManager(self.workspace_root, unversioned)
        service = LifecycleService(manager, self.clock, self.scorer)

        with self.assertRaisesRegex(
            FixtureSetupRequiredError, "does not declare a content version"
        ):
            service.start(FILE_STORAGE_METADATA)

        self.assertEqual(list(self.workspace_root.iterdir()), [])


class CreationActivationTests(IdentityTestCase):
    def test_new_attempts_persist_v2_with_the_manifest_identity(self) -> None:
        state = self.service.start(FILE_STORAGE_METADATA)
        attempt = self.attempt(state.attempt_id)

        self.assertIsInstance(state, SessionStateV2)
        self.assertEqual(state.assessment, self.cache.pinned_assessment(FILE_STORAGE))
        persisted = _read_json(attempt / "session.json")
        self.assertEqual(persisted["schema_version"], SESSION_SCHEMA_VERSION_V2)
        self.assertEqual(
            persisted["assessment"]["content_digest"],  # type: ignore[index]
            state.assessment.content_digest,
        )
        self.assertIsNone(persisted["abandonment"])
        self.assertEqual(_event_versions(attempt), [(EVENT_SCHEMA_VERSION_V2, "started")])
        for name in CACHE_INPUTS:
            self.assertEqual(
                hashlib.sha256((attempt / name).read_bytes()).hexdigest(),
                self.cache.hashes[f"assessment/file_storage/{name}"],
            )
        self.assertEqual(serialize_result(state), {"session": state.to_dict()})
        markdown = render_markdown(load_attempt_context(attempt, self.manager.persistence))
        self.assertIn("File Storage (`file_storage`)", markdown)

    def test_cache_changed_between_validation_and_copy_is_rejected_before_publish(self) -> None:
        selected = self.service.start(FILE_STORAGE_METADATA)
        attempts = self.workspace_root / "attempts"
        before = tree_snapshot(attempts)

        for filename in ("level2.md", "simulation.py", "test_simulation.py"):
            with self.subTest(filename=filename):
                self.use_filesystem(TamperedCopyFilesystem(filename))
                with self.assertRaisesRegex(
                    FixtureSetupRequiredError, f"declared hash: {filename}"
                ):
                    self.service.start(FILE_STORAGE_METADATA)

                self.assertEqual(tree_snapshot(attempts), before)
                self.assertEqual(
                    _read_json(attempts / "active.json")["attempt_id"],
                    selected.attempt_id,
                )

    def test_caller_supplied_identity_must_equal_the_installed_identity(self) -> None:
        pinned = self.cache.pinned_assessment(FILE_STORAGE)
        started = LEGACY_START
        forged = SessionStateV2(
            schema_version=SESSION_SCHEMA_VERSION_V2,
            attempt_id=str(uuid4()),
            assessment=replace(pinned, content_digest="0" * 64),
            profile=session(str(uuid4())).profile,
            started_at=started,
            deadline_at=started + timedelta(seconds=FULL_DURATION_SECONDS),
            status="active",
            revision=0,
        )

        with self.assertRaisesRegex(InvalidInputError, "does not match the installed"):
            self.manager.create_attempt(forged)

        self.assertFalse((self.workspace_root / "attempts").exists())


class LegacyAttemptTests(IdentityTestCase):
    def legacy_attempt(self) -> tuple[SessionState, Path]:
        state = session(str(uuid4()))
        return state, self.manager.create_attempt(state)

    def test_legacy_attempt_completes_every_command_with_v1_records(self) -> None:
        state, attempt = self.legacy_attempt()

        self.assertEqual(self.service.status(state.attempt_id), state)
        self.clock.value = LEGACY_START + timedelta(minutes=5)
        self.assertEqual(self.service.time(state.attempt_id).remaining_seconds, 85 * 60)
        self.assertEqual(self.service.resume(state.attempt_id), state)
        tested = self.service.test(state.attempt_id)
        submitted = self.service.submit(state.attempt_id)

        self.assertIsInstance(tested, SessionState)
        self.assertIsInstance(submitted.state, SessionState)
        self.assertEqual(submitted.state.status, SUBMITTED)
        self.assertEqual(
            _read_json(attempt / "session.json")["schema_version"], SESSION_SCHEMA_VERSION
        )
        self.assertEqual(
            _event_versions(attempt),
            [
                (EVENT_SCHEMA_VERSION, "started"),
                (EVENT_SCHEMA_VERSION, "tested"),
                (EVENT_SCHEMA_VERSION, "submitted"),
            ],
        )
        adapted = adapt_session_record(self.manager.persistence.read_session(attempt))
        self.assertFalse(adapted.content_identity_available)
        self.assertIsNone(adapted.content_version)
        self.assertIsNone(adapted.content_digest)
        self.assertNotIn("content_version", (attempt / "session.json").read_text("utf-8"))

    def test_legacy_expiry_and_missing_event_recovery_write_v1_events(self) -> None:
        state, attempt = self.legacy_attempt()
        (attempt / "events.jsonl").write_bytes(b"")

        self.service.status(state.attempt_id)
        self.clock.value = state.deadline_at
        expired = self.service.status(state.attempt_id)

        self.assertEqual(expired.status, EXPIRED)
        self.assertEqual(
            _event_versions(attempt),
            [(EVENT_SCHEMA_VERSION, "recovered"), (EVENT_SCHEMA_VERSION, "expired")],
        )

    def test_legacy_submission_wal_stays_v1_and_replays_without_rescoring(self) -> None:
        state, attempt = self.legacy_attempt()
        self.use_filesystem(EventUnavailableFilesystem())

        with self.assertRaisesRegex(OSError, "event replacement failure"):
            self.service.submit(state.attempt_id)

        pending = _read_json(attempt / SUBMISSION_RECOVERY_FILENAME)
        self.assertEqual(pending["schema_version"], SUBMISSION_RECOVERY_SCHEMA_VERSION)
        self.use_filesystem(LocalFilesystem())
        recovered = self.service.status(state.attempt_id)

        self.assertIsInstance(recovered, SessionState)
        self.assertEqual(recovered.status, SUBMITTED)
        self.assertEqual(len(self.scorer.calls), 1)
        self.assertFalse((attempt / SUBMISSION_RECOVERY_FILENAME).exists())
        self.assertEqual(
            _event_versions(attempt),
            [(EVENT_SCHEMA_VERSION, "started"), (EVENT_SCHEMA_VERSION, "submitted")],
        )


class PinnedLifecycleTests(IdentityTestCase):
    def test_v2_test_missing_event_and_expiry_write_v2_events(self) -> None:
        state = self.service.start(FILE_STORAGE_METADATA)
        attempt = self.attempt(state.attempt_id)
        self.service.test(state.attempt_id)
        tested = self.manager.persistence.read_session(attempt)
        (attempt / "events.jsonl").write_bytes(
            (attempt / "events.jsonl").read_bytes().splitlines(keepends=True)[0]
        )

        self.service.status(state.attempt_id)
        self.clock.value = state.deadline_at
        expired = self.service.status(state.attempt_id)

        self.assertIsInstance(tested, SessionStateV2)
        self.assertEqual(expired.status, EXPIRED)
        self.assertEqual(expired.assessment, state.assessment)
        self.assertEqual(
            _event_versions(attempt),
            [
                (EVENT_SCHEMA_VERSION_V2, "started"),
                (EVENT_SCHEMA_VERSION_V2, "recovered"),
                (EVENT_SCHEMA_VERSION_V2, "expired"),
            ],
        )

    def test_v2_submission_recovers_at_each_durable_boundary_without_rescoring(self) -> None:
        boundaries = {
            "session replaced then reported failure": FailOnceFilesystem(
                "replace", "session.json", after=True
            ),
            "session replacement failed": FailOnceFilesystem("replace", "session.json"),
            "event unavailable": EventUnavailableFilesystem(),
            "recovery cleanup failed": FailOnceFilesystem(
                "unlink", SUBMISSION_RECOVERY_FILENAME
            ),
        }
        for label, filesystem in boundaries.items():
            with self.subTest(boundary=label):
                self.use_filesystem(LocalFilesystem())
                state = self.service.start(FILE_STORAGE_METADATA)
                attempt = self.attempt(state.attempt_id)
                calls_before = len(self.scorer.calls)
                self.use_filesystem(filesystem)

                # Durable-write failures surface as OSError; a failed WAL cleanup
                # after publication is reported as unavailable, not as success.
                with self.assertRaises((OSError, SessionUnavailableError)):
                    self.service.submit(state.attempt_id)

                pending = _read_json(attempt / SUBMISSION_RECOVERY_FILENAME)
                self.assertEqual(
                    pending["schema_version"], SUBMISSION_RECOVERY_SCHEMA_VERSION_V2
                )
                expected = SubmissionRecovery.from_dict(pending).state
                self.use_filesystem(LocalFilesystem())
                recovered = self.service.status(state.attempt_id)
                repeated = self.service.submit(state.attempt_id)

                self.assertEqual(recovered, expected)
                self.assertEqual(repeated.state, expected)
                self.assertFalse(repeated.newly_submitted)
                self.assertEqual(len(self.scorer.calls), calls_before + 1)
                self.assertFalse((attempt / SUBMISSION_RECOVERY_FILENAME).exists())
                self.assertEqual(
                    _event_versions(attempt),
                    [
                        (EVENT_SCHEMA_VERSION_V2, "started"),
                        (EVENT_SCHEMA_VERSION_V2, "submitted"),
                    ],
                )

    def test_uninstalled_pinned_identity_blocks_scoring_without_writes(self) -> None:
        state = self.service.start(FILE_STORAGE_METADATA)
        attempts = self.workspace_root / "attempts"
        before = tree_snapshot(attempts)
        upgraded = ValidatedFixtureCache(
            self.cache.root, dict(self.cache.hashes), "upstream-1111111"
        )
        service = LifecycleService(
            WorkspaceManager(self.workspace_root, upgraded), self.clock, self.scorer
        )

        for command in (service.test, service.submit, service.status):
            with self.subTest(command=command.__name__):
                with self.assertRaisesRegex(
                    AssessmentVersionUnavailableError, "stored results remain reviewable"
                ):
                    command(state.attempt_id)

        # The read-only context view renders stored fields without the definition.
        context = AttemptContextService(service.workspace).read(
            attempt_id=state.attempt_id, output_format="json"
        )
        self.assertEqual(context.context.state, state)

        self.assertEqual(self.scorer.calls, [])
        self.assertEqual(tree_snapshot(attempts), before)


class SubmissionRecoveryFamilyTests(IdentityTestCase):
    def submission_pair(self, state):
        submitted, review = submitted_with_review(
            state,
            RecordingScorer()(Path(".")),
            state.started_at + timedelta(minutes=1),
        )
        event = session_event(
            submitted,
            event_id=str(uuid4()),
            occurred_at=submitted.submitted_at,
            name="submitted",
            outcome="succeeded",
            arguments={},
        )
        return submitted, event, review

    def test_recovery_records_cannot_mix_schema_families(self) -> None:
        pinned = self.service.start(FILE_STORAGE_METADATA)
        legacy = session(str(uuid4()))
        pinned_submitted, pinned_event, pinned_review = self.submission_pair(pinned)
        legacy_submitted, legacy_event, legacy_review = self.submission_pair(legacy)

        round_trip = SubmissionRecovery.for_submission(
            pinned, pinned_submitted, pinned_event, pinned_review
        )
        self.assertEqual(round_trip.schema_version, SUBMISSION_RECOVERY_SCHEMA_VERSION_V2)
        self.assertEqual(SubmissionRecovery.from_dict(round_trip.to_dict()), round_trip)
        legacy_recovery = SubmissionRecovery.for_submission(
            legacy, legacy_submitted, legacy_event, legacy_review
        )
        self.assertEqual(
            legacy_recovery.schema_version, SUBMISSION_RECOVERY_SCHEMA_VERSION
        )

        # A pre-capture v1 file has no review key and still replays.
        pre_capture = legacy_recovery.to_dict()
        del pre_capture["review"]
        self.assertIsNone(SubmissionRecovery.from_dict(pre_capture).review)
        # A pinned submission must always carry the review its state identifies.
        with self.assertRaisesRegex(InvalidInputError, "requires its review"):
            SubmissionRecovery(
                SUBMISSION_RECOVERY_SCHEMA_VERSION_V2, pinned, pinned_submitted, pinned_event
            )
        with self.assertRaisesRegex(InvalidInputError, "does not identify its review"):
            SubmissionRecovery(
                SUBMISSION_RECOVERY_SCHEMA_VERSION_V2,
                pinned,
                pinned_submitted,
                pinned_event,
                # A review whose bytes differ no longer matches the state digest.
                replace(
                    pinned_review,
                    source=ReviewSource.capture("simulation.py", "print('changed')\n"),
                ),
            )

        mixed = (
            (SUBMISSION_RECOVERY_SCHEMA_VERSION, pinned, pinned_submitted, pinned_event, pinned_review),
            (SUBMISSION_RECOVERY_SCHEMA_VERSION_V2, legacy, legacy_submitted, legacy_event, legacy_review),
            (SUBMISSION_RECOVERY_SCHEMA_VERSION_V2, pinned, pinned_submitted, legacy_event, pinned_review),
        )
        for version, prior, submitted, event, review in mixed:
            with self.subTest(version=version, event=event.schema_version):
                with self.assertRaises(InvalidInputError):
                    SubmissionRecovery(version, prior, submitted, event, review)

        future = round_trip.to_dict()
        future["schema_version"] = "submission-recovery/v9"
        with self.assertRaises(UnsupportedSchemaVersionError):
            SubmissionRecovery.from_dict(future)


if __name__ == "__main__":
    unittest.main()
