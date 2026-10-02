# Cursor scaffold review

Reviewer: Composer 2.5, read-only bounded comparison of generated tasks against
the accepted implementation plan and D001–D005. Coordinator verified findings
against the worktree before adopting them.

Adopted: explicitly require pending-restart rows without GET recovery; assign
shared lifecycle/CLI to 003/02 and HTTP wiring to 003/03; require transaction-only
v1 upgrades and the legacy identity adapter; activate v2 creation only when real
provider identities are available; document unsupported mixed-version writers;
replace nonexistent build-wheel/npm-test recipes; require asset build before
integrity check. Offline verification now explicitly uses the existing harness
and a unique temporary venv, not a fixed directory/global pip.

Rejected or clarified:

- Three total assessments versus two new originals is consistent: File Storage
  plus two proposed originals. D005 remains awaiting the user's topic choice.
- just check unit exists in .justfiles/check.just. The browser recipe explicitly
  forwards positional arguments, so --grep restart is valid Playwright filtering.
- Full wheel verification belongs to the immediately following offline/docs task;
  repeating it in the acceptance-matrix task is unnecessary.
- Content acceptance is already a sequence prerequisite; later references to
  accepted originals do not bypass it.
- Preparation is coordinator-owned: project AGENTS.md read, dedicated worktree
  linked, fest next selected 003/01/01. Existing CLI/server lifecycle regression
  tests ran: python3 -m unittest tests.test_web_server_lifecycle tests.test_cli -q,
  36 passed. This is not proof of new UI behavior.

No review finding is treated as runtime verification. Implementation is pending
its own tests/review and publication gates.
