"""Browser, CLI, and derived-context continuity tests."""

from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import patch

try:
    from .web_server_test_support import WebServerTestCase
except ImportError:
    from web_server_test_support import WebServerTestCase

from codesignal_practice_simulator import cli


CONTEXT_KEYS = {
    "schema_version",
    "attempt_id",
    "assessment",
    "lifecycle",
    "score",
    "events",
    "next_legal_commands",
}
ASSESSMENT_KEYS = {"id", "display_name", "mode", "profile"}
LIFECYCLE_KEYS = {"status", "started_at", "deadline_at", "submitted_at"}
SCORE_KEYS = {"levels", "passed_levels", "highest_contiguous_level"}
EVENT_KEYS = {"revision", "occurred_at", "name", "outcome"}
LEVEL_SCORE_KEYS = {"level", "outcome"}


class TestWebContinuity(WebServerTestCase):
    def test_web_lifecycle_refreshes_safe_context_without_leaking_workspace_inputs(self) -> None:
        attempt_id, _etag = self.start_attempt()
        attempt = self.workspace / "attempts" / attempt_id
        source, etag, forbidden = self._install_forbidden_inputs(attempt, attempt_id)
        self._assert_started_surface(attempt_id, attempt, forbidden)
        self._assert_read_operations_do_not_change_state(
            attempt_id, attempt, forbidden
        )
        tested = self._run_test(attempt_id, source, etag)
        self._assert_tested_surface(attempt_id, attempt, forbidden)
        self._assert_submitted_surface(attempt_id, attempt, source, tested, forbidden)

    def test_failed_web_test_refreshes_status_with_persisted_score(self) -> None:
        attempt_id, etag = self.start_attempt()
        attempt = self.workspace / "attempts" / attempt_id

        status, _headers, document = self.request(
            "POST",
            f"/api/test?attempt_id={attempt_id}",
            body={"content": "candidate failure\n"},
            origin=self.origin,
            headers={"If-Match": etag},
        )

        self.assertEqual(status, 200)
        self.assertEqual(document["data"]["session"]["status"], "active")
        self.assertEqual(
            [level["outcome"] for level in document["data"]["practice"]["levels"]],
            ["failed", "failed", "failed", "failed"],
        )
        status_text = (attempt / "STATUS.md").read_text(encoding="utf-8")
        self.assertIn("- Passed levels: 0 of 4", status_text)
        self.assertIn("- Revision 1: `tested` (succeeded)", status_text)
        context = self._context_document(attempt_id)
        self.assertEqual(context["lifecycle"]["status"], "active")
        self.assertEqual(context["score"], self._failed_score())
        self.assertEqual(
            [event["name"] for event in context["events"]],
            ["started", "tested"],
        )

    def _install_forbidden_inputs(
        self, attempt: Path, attempt_id: str
    ) -> tuple[str, str, set[str]]:
        reference = self.workspace / "study-reference.txt"
        reference.write_text("reference-only secret\n", encoding="utf-8")
        (attempt / "simulation.py").write_text(
            "candidate source secret\n", encoding="utf-8"
        )
        (attempt / "test_simulation.py").write_text(
            "copied test secret\n", encoding="utf-8"
        )
        (attempt / "level1.md").write_text("prompt secret\n", encoding="utf-8")
        self.application.workspace.cache.root.joinpath("vendor-readme.md").write_text(
            "fixture cache secret\n", encoding="utf-8"
        )
        source = self.application.source(attempt_id=attempt_id)
        forbidden = {
            "candidate source secret",
            "copied test secret",
            "prompt secret",
            "fixture cache secret",
            "reference-only secret",
            str(attempt / "simulation.py"),
            str(attempt / "test_simulation.py"),
            str(attempt / "level1.md"),
            str(self.workspace / ".cache"),
            str(reference),
        }
        return source.content, source.etag, forbidden

    def _assert_started_surface(
        self, attempt_id: str, attempt: Path, forbidden: set[str]
    ) -> None:
        self._assert_context_surface(
            attempt_id,
            status="active",
            score=self._empty_score(),
            events=["started"],
            forbidden=forbidden,
        )
        status_text = (attempt / "STATUS.md").read_text(encoding="utf-8")
        self.assertIn("started", status_text)
        self._assert_safe_context(status_text, forbidden)

    def _assert_read_operations_do_not_change_state(
        self, attempt_id: str, attempt: Path, forbidden: set[str]
    ) -> None:
        authoritative_before = self._authoritative_bytes(attempt)
        for path in ("/api/session", "/api/time"):
            status, _headers, _document = self.request(
                "GET", f"{path}?attempt_id={attempt_id}"
            )
            self.assertEqual(status, 200)
        self.assertEqual(self._authoritative_bytes(attempt), authoritative_before)
        self._assert_context_surface(
            attempt_id,
            status="active",
            score=self._empty_score(),
            events=["started"],
            forbidden=forbidden,
        )

    def _run_test(self, attempt_id: str, source: str, etag: str) -> object:
        status, _headers, document = self.request(
            "POST",
            f"/api/test?attempt_id={attempt_id}",
            body={"content": source},
            origin=self.origin,
            headers={"If-Match": etag},
        )
        self.assertEqual(status, 200)
        return document

    def _assert_tested_surface(
        self, attempt_id: str, attempt: Path, forbidden: set[str]
    ) -> None:
        self.assertEqual(self._event_names(attempt), ["started", "tested"])
        self._assert_context_surface(
            attempt_id,
            status="active",
            score=self._failed_score(),
            events=["started", "tested"],
            forbidden=forbidden,
        )
        status_text = (attempt / "STATUS.md").read_text(encoding="utf-8")
        self.assertIn("tested", status_text)
        self._assert_safe_context(status_text, forbidden)

    def _assert_submitted_surface(
        self,
        attempt_id: str,
        attempt: Path,
        source: str,
        tested: object,
        forbidden: set[str],
    ) -> None:
        status, _headers, submitted = self.request(
            "POST",
            f"/api/submit?attempt_id={attempt_id}",
            body={"content": source},
            origin=self.origin,
            headers={"If-Match": tested["data"]["source"]["etag"]},
        )
        self.assertEqual(status, 200)
        self.assertTrue(submitted["data"]["newly_submitted"])
        self.assertEqual(
            self._event_names(attempt),
            ["started", "tested", "submitted"],
        )
        self._assert_context_surface(
            attempt_id,
            status="submitted",
            score=self._failed_score(),
            events=["started", "tested", "submitted"],
            forbidden=forbidden,
        )
        status_text = (attempt / "STATUS.md").read_text(encoding="utf-8")
        self.assertIn("submitted", status_text)
        self._assert_safe_context(status_text, forbidden)

        terminal_context = self._context_document(attempt_id)
        terminal_status = status_text
        authoritative_after_submit = self._authoritative_bytes(attempt)
        status, _headers, repeated = self.request(
            "POST",
            f"/api/submit?attempt_id={attempt_id}",
            body={"content": "must not replace final source\n"},
            origin=self.origin,
            headers={"If-Match": "sha256:" + "f" * 64},
        )
        self.assertEqual(status, 200)
        self.assertFalse(repeated["data"]["newly_submitted"])
        self.assertEqual(
            self._authoritative_bytes(attempt), authoritative_after_submit
        )
        self.assertEqual(self._context_document(attempt_id), terminal_context)
        self.assertEqual(
            (attempt / "STATUS.md").read_text(encoding="utf-8"),
            terminal_status,
        )

    def test_web_operation_success_survives_derived_render_failure(self) -> None:
        with patch.object(self.application.derived_status, "refresh", side_effect=OSError):
            status, _headers, document = self.request(
                "POST",
                "/api/attempts",
                body={"mode": "drill", "drill_duration_seconds": 60},
                origin=self.origin,
            )

        self.assertEqual(status, 201)
        attempt_id = document["data"]["session"]["attempt_id"]
        attempt = self.workspace / "attempts" / attempt_id
        self.assertTrue((attempt / "session.json").is_file())
        self.assertFalse((attempt / "STATUS.md").exists())
        context = self._context_document(attempt_id)
        self.assertEqual(context["lifecycle"]["status"], "active")

    def _context_document(self, attempt_id: str) -> dict[str, object]:
        output = io.StringIO()
        code = cli.execute(
            [
                "context",
                "--workspace-root",
                str(self.workspace),
                "--attempt",
                attempt_id,
                "--format",
                "json",
                "--json",
            ],
            application_factory=lambda _workspace_root: self.application,
            output=output,
        )
        self.assertEqual(code, 0, output.getvalue())
        document = json.loads(output.getvalue())
        self.assertEqual(document["schema_version"], "cli/v1")
        self.assertTrue(document["ok"])
        self.assertEqual(document["result"]["format"], "json")
        return document["result"]["context"]

    def _assert_context_surface(
        self,
        attempt_id: str,
        *,
        status: str,
        score: dict[str, object],
        events: list[str],
        forbidden: set[str],
    ) -> None:
        context = self._context_document(attempt_id)
        self._assert_context_schema(context)
        self.assertEqual(context["attempt_id"], attempt_id)
        self.assertEqual(context["lifecycle"]["status"], status)
        self.assertEqual(context["score"], score)
        self.assertEqual(
            [event["name"] for event in context["events"]],
            events,
        )
        self.assertEqual(
            context["next_legal_commands"],
            self._legal_commands(attempt_id, status),
        )
        self._assert_safe_context(json.dumps(context, sort_keys=True), forbidden)

    def _assert_context_schema(self, context: dict[str, object]) -> None:
        self.assertEqual(set(context), CONTEXT_KEYS)
        self.assertEqual(set(context["assessment"]), ASSESSMENT_KEYS)
        self.assertEqual(set(context["lifecycle"]), LIFECYCLE_KEYS)
        score = context["score"]
        self.assertEqual(set(score), SCORE_KEYS)
        for level in score["levels"]:
            self.assertEqual(set(level), LEVEL_SCORE_KEYS)
        for event in context["events"]:
            self.assertEqual(set(event), EVENT_KEYS)

    @staticmethod
    def _empty_score() -> dict[str, object]:
        return {
            "levels": [],
            "passed_levels": 0,
            "highest_contiguous_level": 0,
        }

    @staticmethod
    def _failed_score() -> dict[str, object]:
        return {
            "levels": [
                {"level": level, "outcome": "failed"} for level in range(1, 5)
            ],
            "passed_levels": 0,
            "highest_contiguous_level": 0,
        }

    @staticmethod
    def _legal_commands(attempt_id: str, status: str) -> list[str]:
        selected = f"--attempt {attempt_id}"
        commands = [
            f"codesignal-sim status {selected}",
            f"codesignal-sim context {selected}",
        ]
        if status == "active":
            commands.extend(
                [
                    f"codesignal-sim resume {selected}",
                    f"codesignal-sim time {selected}",
                    f"codesignal-sim test {selected}",
                    f"codesignal-sim submit {selected}",
                ]
            )
        return commands

    @staticmethod
    def _authoritative_bytes(attempt: Path) -> tuple[bytes, bytes]:
        return (
            (attempt / "session.json").read_bytes(),
            (attempt / "events.jsonl").read_bytes(),
        )

    @staticmethod
    def _event_names(attempt: Path) -> list[str]:
        return [
            json.loads(line)["name"]
            for line in (attempt / "events.jsonl").read_text(
                encoding="utf-8"
            ).splitlines()
        ]

    def _assert_safe_context(self, context: str, forbidden: set[str]) -> None:
        for value in forbidden:
            self.assertNotIn(value, context)


if __name__ == "__main__":
    import unittest

    unittest.main()
