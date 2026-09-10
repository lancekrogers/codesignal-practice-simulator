"""Guard the supported CLI documentation and optional Just recipes."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))


class DocumentationTests(unittest.TestCase):
    def test_readme_documents_the_session_based_cli_without_requiring_just(self) -> None:
        readme = (PROJECT / "README.md").read_text(encoding="utf-8")
        normalized_readme = " ".join(readme.split())

        self.assertIn("`attempts/<uuid>/session.json`", readme)
        self.assertIn("codesignal-sim fetch --workspace-root", readme)
        self.assertIn("codesignal-sim start --workspace-root", readme)
        self.assertIn("python3 -m codesignal_practice_simulator --help", readme)
        self.assertIn("Just recipes are optional shortcuts", readme)
        self.assertIn("`full-90m`", readme)
        self.assertIn("`drill-30m`", readme)
        self.assertIn("canonical lowercase UUID takes precedence", readme)
        self.assertIn("python3 scripts/run_legacy_checks.py", readme)
        self.assertIn("It does not run the fetched\nupstream compatibility test.", readme)
        self.assertIn("0 (success), 2", readme)
        self.assertIn(
            "exits 5 only when `test` ran and one or more groups were non-passing",
            normalized_readme,
        )
        self.assertIn(
            "`submit` always exits 0 when it successfully finalizes",
            normalized_readme,
        )
        self.assertNotIn("attempt.json", readme)
        self.assertNotIn("`just level", readme)
        self.assertNotIn("`just score`", readme)
        self.assertNotIn("`just submit`", readme)

    def test_contract_covers_envelopes_lifecycle_and_profiles(self) -> None:
        contract = (PROJECT / "docs" / "cli-contract.md").read_text(encoding="utf-8")
        normalized_contract = " ".join(contract.split())
        profiles = (PROJECT / "docs" / "drill-profiles.md").read_text(encoding="utf-8")

        for command in (
            "fetch",
            "start",
            "resume",
            "status",
            "time",
            "task",
            "test",
            "submit",
            "context",
        ):
            self.assertIn(command, contract)
        for exit_code in ("| 0 |", "| 2 |", "| 3 |", "| 4 |", "| 5 |"):
            self.assertIn(exit_code, contract)
        self.assertIn("cli/v1", contract)
        self.assertIn("takes precedence over the active pointer", contract)
        self.assertIn("Return the exact stored result; no scoring", contract)
        self.assertIn(
            "every successfully finalized `submit`, even when stored groups failed or errored",
            normalized_contract,
        )
        self.assertIn(
            "Only the `test` command returns this exit: it ran and at least one group was non-passing",
            normalized_contract,
        )
        self.assertIn("`test`", profiles)
        self.assertIn("`submit`", profiles)
        self.assertIn("`drill-30m`", profiles)

    def test_just_recipes_are_optional_cli_shortcuts_and_verify_the_project(self) -> None:
        justfile = (PROJECT / "justfile").read_text(encoding="utf-8")
        practice = (PROJECT / "justfiles" / "practice.just").read_text(encoding="utf-8")
        verify = (PROJECT / "justfiles" / "verify.just").read_text(encoding="utf-8")

        self.assertIn("simulator :=", justfile)
        self.assertIn("codesignal-sim", justfile)
        self.assertIn("{{simulator}} start", practice)
        self.assertIn("{{simulator}} task", practice)
        self.assertIn("{{simulator}} test", practice)
        self.assertIn("{{simulator}} submit", practice)
        self.assertIn("{{simulator}} context", practice)
        self.assertIn("only this recipe returns exit 5", practice)
        self.assertNotIn("new_attempt.py", practice)
        self.assertNotIn("scorecard.py", practice)
        self.assertIn("verify:", verify)
        self.assertIn("python3 scripts/run_legacy_checks.py", verify)
        self.assertIn("unittest discover -s tests -v", verify)
        self.assertIn("unittest tests.test_end_to_end -v", verify)
        self.assertIn("git diff --check", verify)
        self.assertIn("test-compat:", verify)
        self.assertIn("study-stages:", verify)
        self.assertIn("study-check", verify)
        self.assertIn("Deprecated post-attempt compatibility", verify)

    def test_agent_and_legacy_documents_preserve_live_attempt_boundaries(self) -> None:
        policy = (PROJECT / "AGENTS.md").read_text(encoding="utf-8")
        safety = (PROJECT / "docs" / "agent-safety.md").read_text(encoding="utf-8")
        legacy = (PROJECT / "docs" / "legacy" / "explore-README.md").read_text(
            encoding="utf-8"
        )
        walkthrough = (PROJECT / "notes" / "walkthrough.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("codesignal-sim context", policy)
        self.assertIn("explicit permission", policy)
        self.assertIn("not a security sandbox", policy)
        self.assertIn("codesignal-sim context", safety)
        self.assertIn("not a security sandbox", " ".join(safety.split()))
        self.assertIn("Deprecated historical archive", legacy)
        self.assertIn("retired and unsupported", legacy)
        self.assertIn("## Layout", legacy)
        self.assertIn("## Provenance", legacy)
        self.assertIn("`ROLLBACK` restores the state", legacy)
        self.assertIn("Do not test a submitted attempt.", walkthrough)
        self.assertIn("start a new drill or attempt", walkthrough)
        self.assertIn("post-attempt checkers", walkthrough)

    def test_coaching_policy_surfaces_agree_without_claiming_isolation(self) -> None:
        template = (PROJECT / "src/codesignal_practice_simulator/workspace.py").read_text(
            encoding="utf-8"
        )
        surfaces = {
            "root policy": (PROJECT / "AGENTS.md").read_text(encoding="utf-8"),
            "safety guide": (PROJECT / "docs" / "agent-safety.md").read_text(
                encoding="utf-8"
            ),
            "readme": (PROJECT / "README.md").read_text(encoding="utf-8"),
            "attempt template": template,
        }
        required = (
            "STATUS.md",
            "COACHING.md",
            "explicit permission",
            "source history",
            "reference",
            "study",
            "vendor",
            "fixture cache",
            "copied tests",
            "hidden-test",
            "simulation.py",
            "session.json",
            "events.jsonl",
            "locks",
            "same-user",
        )
        for name, document in surfaces.items():
            normalized = " ".join(document.lower().split())
            with self.subTest(surface=name):
                for phrase in required:
                    self.assertIn(phrase.lower(), normalized)
                self.assertIn("not a security sandbox", normalized)

        self.assertIn("browser ui", surfaces["readme"].lower())
        self.assertIn("direct cli", surfaces["readme"].lower())
        self.assertIn("timer, scoring, and lifecycle", surfaces["readme"].lower())
        self.assertIn("post-attempt", surfaces["safety guide"].lower())


if __name__ == "__main__":
    unittest.main()
