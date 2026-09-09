"""Guard the documented timed workflow against legacy attempt commands."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))


class DocumentationTests(unittest.TestCase):
    def test_readme_documents_the_session_based_cli_as_the_timed_workflow(self) -> None:
        readme = (PROJECT / "README.md").read_text(encoding="utf-8")

        self.assertIn("`attempts/<uuid>/session.json`", readme)
        self.assertIn("just practice\n", readme)
        self.assertIn("just task 1\n", readme)
        self.assertNotIn("attempt.json", readme)
        self.assertNotIn("`just level", readme)
        self.assertNotIn("`just score`", readme)
        self.assertNotIn("`just submit`", readme)

    def test_just_recipes_separate_timed_cli_from_post_attempt_study(self) -> None:
        practice = (PROJECT / "justfiles" / "practice.just").read_text(encoding="utf-8")
        verify = (PROJECT / "justfiles" / "verify.just").read_text(encoding="utf-8")

        self.assertIn("codesignal-sim start", practice)
        self.assertIn("codesignal-sim task", practice)
        self.assertNotIn("new_attempt.py", practice)
        self.assertNotIn("scorecard.py", practice)
        self.assertIn("test-compat:", verify)
        self.assertIn("study-stages:", verify)
        self.assertIn("study-check", verify)


if __name__ == "__main__":
    unittest.main()
