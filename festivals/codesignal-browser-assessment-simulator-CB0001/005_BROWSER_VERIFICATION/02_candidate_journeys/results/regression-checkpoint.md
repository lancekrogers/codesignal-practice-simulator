# Regression checkpoint — task 01

Coordinator execution against `be5389b` plus the task-01 editor contribution and
rebuilt static assets, 2026-09-10. This is a regression check, not completion of
the later sequence testing gate.

Command from the linked project:

```sh
ASSET_BUILDER=/private/tmp/cb0001-release.HTxOTs/builder/bin/python just verify
```

Exit 0. Python 3.14: 275 discovered tests passed, no skips, followed by 4 explicit
end-to-end tests passed. Canonical legacy checks passed: tracked manifest,
hash-validated existing ignored fixture cache, Git boundary, 26 spec checks,
12 staged checks, and all four study-level checks. `git diff --check` passed.

The temporary builder supplies build/setuptools/wheel to packaging tests. No
fixture cache was copied or fetched into a clone by this command. No actual
candidate attempt was used; maintained runtime tests use synthetic workspaces.

## Additional interpreter regression

Python 3.12: 275 tests passed. The coordinator initially ran 3.10, 3.11, and
3.12 concurrently in the same checkout. That was unsuitable: distribution
tests build into the checkout's shared setuptools output, so the 3.10/3.11
wheel checks collided (missing package members/build failure). A 3.10 timed
publication check also failed under that load. These are failed runs, not
passing matrix evidence. Serial 3.10/3.11 reruns are required and in progress;
future full suites must use separate checkouts or run serially.

Serial reruns completed: Python 3.10 passed 275 tests (104.718 seconds), and
Python 3.11 passed 275 tests (100.303 seconds), both with no skips and exit 0.
Python 3.12 passed 275 tests (112.139 seconds), no skips. Python 3.14's full
canonical check is recorded above. The failures were not hidden or counted as
passing evidence.
