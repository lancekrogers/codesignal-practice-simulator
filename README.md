# CodeSignal Practice Simulator

Practice four-level, timed CodeSignal-style assessments on your machine.
The browser IDE and the CLI drive the same attempt: one timer, one score.
A practice library offers two original exercises that work offline out of the
box (In-Memory Records, Account Ledger) plus the fetched File Storage
assessment; every attempt is kept, browsable and reviewable, and can be
ended or restarted without losing saved work.

![Local practice IDE with the prompt, Monaco editor, timer, and test controls](docs/assets/practice-simulator.png)

## Quick start

Python 3.10+, from this directory (tested with Just 1.58):

```sh
just setup                 # Install the editable Python app
just dev                   # Open the local browser IDE (practice library)
just fetch                 # Optional: download the pinned File Storage assessment
```

`just dev` serves the bundled UI from a Python loopback server and opens the
**practice library**. It does not start a timer. Pick an exercise card (the two
original exercises are ready immediately; File Storage shows "Setup required"
until you fetch it), choose a format, then **Start practice** and
**Confirm and start**. There is no pause. Stop the server with Ctrl-C. Keep the
printed URL private.

Just recipes are optional shortcuts. Without `just`:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --no-deps -e .
codesignal-sim fetch --workspace-root "$PWD"
codesignal-sim web --workspace-root "$PWD" --port 0
python3 -m codesignal_practice_simulator --help
```

The app has no Python runtime dependencies, and you do not need Node to run
it.

## How this was built

The simulator was built through **Festival Methodology**. The completed
festivals are included in [`festivals/`](festivals/), with their requirements,
plans, tasks, review findings, verification evidence, and progress records:

| Festival | What it built | Completed |
| --- | --- | --- |
| [CP0001 — Practice simulator](festivals/codesignal-practice-simulator-CP0001/FESTIVAL_OVERVIEW.md) | The Python CLI, timed attempts, scoring engine, and post-attempt study material | September 9, 2026 |
| [CB0001 — Browser assessment simulator](festivals/codesignal-browser-assessment-simulator-CB0001/FESTIVAL_OVERVIEW.md) | The local browser IDE on top of the shared Python engine | September 10, 2026 |
| [CP0002 — Practice library](festivals/codesignal-practice-library-CP0002/FESTIVAL_OVERVIEW.md) | Original exercises, fresh attempts, restart and abandonment, durable history, and read-only submission review | September 18, 2026 |

Work moved through the `fest next` loop, with task completion, testing, review,
and traceable commits. The browser festival organized its build into six
phases: requirements intake, architecture and planning, the shared application
backend, the assessment IDE, browser verification, and release review. Cursor
agents handled implementation and independent architecture, security, and UI
reviews; review findings fed back into fixes before release.

The result pairs a Python loopback server with a locally bundled TypeScript UI
and Monaco editor. The browser and CLI share one server-authoritative attempt
lifecycle. Verification covered unit and HTTP tests, real Playwright browser
journeys, offline operation, and installed Python packages.

**Browser IDE build — CB0001**

![CB0001 build progress across six phases, finishing at 100% completion](festivals/codesignal-browser-assessment-simulator-CB0001/codesignal-browser-assessment-simulator-CB0001.gif)

**Practice library build — CP0002**

![CP0002 festival replay for the practice library build](festivals/codesignal-practice-library-CP0002/festival-replay.gif)

These clips show festival build progress, rather than practice attempts.

## Practice

### The library

`codesignal-sim catalog` and the library screen list every installed exercise
with its readiness:

| Exercise | Source | Ready when |
| --- | --- | --- |
| In-Memory Records (`in_memory_records`, content `records-1`) | Original, bundled in the package | Always; works offline |
| Account Ledger (`account_ledger`, content `ledger-1`) | Original, bundled in the package | Always; works offline |
| File Storage (`file_storage`, content `upstream-6aab304`) | Fetched, FETCH_ONLY | After `codesignal-sim fetch`; otherwise `setup: fetch_required` |

The originals are first-party: specifications live in
[docs/content/](docs/content/), the packaged files are exactly the four level
prompts, the starter `simulation.py`, the visible `test_simulation.py` and a
content manifest with their hashes. Nothing else ships (`just check content`
and the wheel check refuse anything more).

File Storage is FETCH_ONLY: this repo does not ship it, and there is no
license to redistribute its README, prompts, starter, or bundled test. Fetch
writes seven pinned files into the ignored cache
`.cache/codesignal-fixtures/6aab304/`. Do not commit that cache. The installed
package contains only first-party pinned paths and hashes, but never fixture bytes.
A wheel does not include pinned fixtures; offline, pass `--source` a complete
approved tree. Without a fetch, File Storage stays explicitly unavailable and
the originals keep working.

```sh
codesignal-sim catalog --workspace-root "$PWD" --json
codesignal-sim start --workspace-root "$PWD" --assessment in_memory_records --mode drill
codesignal-sim fetch --workspace-root "$PWD"                         # only for File Storage
codesignal-sim start --workspace-root "$PWD" --assessment file_storage
codesignal-sim web --workspace-root "$PWD" --port 0 --no-open
```

`start` defaults to File Storage in `full-90m` (90 minutes). `--mode drill`
uses `drill-30m` (30 minutes unless you pass `--drill-duration-seconds`). See
[drill profiles](docs/drill-profiles.md). Every attempt records which exercise
and content version it used (`content_identity: pinned`).

### During an attempt: Reset source, End attempt, Restart

The attempt screen has three distinct controls, each behind a confirmation:

- **Reset source** replaces your source with the exercise starter. The attempt,
  its timer and its ID are unchanged.
- **End attempt** ends the attempt without a score. Saved work stays readable
  in history; the record becomes `abandoned` (shown as "Ended").
- **Restart** ends the attempt and opens a fresh one for the same exercise and
  format. Saved work in the old attempt is kept; nothing is copied into the new
  one, and the timer starts over only there.

Unsaved editor text is saved first. If it cannot be saved, you are asked to
discard it explicitly or cancel. The CLI equivalents read the attempt's
revision so a stale view can never end or restart the wrong state:

```text
$ codesignal-sim abandon --workspace-root "$PWD" --expected-revision 9 --json
{"ok": false, "error": {"code": "stale_revision",
  "message": "attempt changed since it was read; refresh and retry (expected revision 9, current 1)"}}   # exit 4

$ codesignal-sim restart --workspace-root "$PWD" --expected-revision 1 --operation-id 6f1c2d3e-4a5b-4c6d-8e9f-0a1b2c3d4e5f --json
{"ok": true, "result": {"replayed": false, "replacement_attempt_id": "029ff4d5-…", "abandoned_session": {"status": "abandoned", …}, "session": {"status": "active", …}}}

$ codesignal-sim restart --workspace-root "$PWD" --attempt 2e250f47-… --expected-revision 1 --operation-id 6f1c2d3e-4a5b-4c6d-8e9f-0a1b2c3d4e5f --json
{"ok": true, "result": {"replayed": true, "replacement_attempt_id": "029ff4d5-…", "session": null, "abandoned_session": null}}  # same operation: replayed, no second attempt

$ codesignal-sim restart … --operation-id 6f1c2d3e-… --mode full --json
{"ok": false, "error": {"code": "operation_conflict",
  "message": "operation ID was already used with different arguments: 6f1c2d3e-…"}}                        # exit 4

$ codesignal-sim start --workspace-root "$PWD" --assessment account_ledger --json
{"ok": false, "error": {"code": "live_selection",
  "message": "an active attempt is already selected; resume it, or end or restart it first: 029ff4d5-…"}}  # exit 4
```

A restart is a journaled transaction: if the process dies after the journal is
written, the next selection or the same `restart` command with the same
`--operation-id` finishes it (`recovery_pending`, exit 3, means "retry the
same operation"; nothing is lost and no second replacement is created).

### History and review

The **History** screen (and `codesignal-sim history`) lists every stored
attempt from its metadata only, newest first, with exercise, status, format,
start time, result summary and review availability. Filter by exercise or
status, page with `--cursor`/`--limit` (default 25, maximum 100). Corrupt or
unsafe entries are counted or shown as unavailable instead of hidden.

**Review** (and `codesignal-sim review --attempt UUID`) is read-only and never
selects, rescores or rewrites anything. A submission shows its exact scored
bytes and their digest; an expired or ended attempt shows its saved work and
last practice result, never a fabricated final result; a record submitted by an
older release shows its stored score with a "submitted-source binding
unavailable" label and its current file marked "not proven submitted".
**Retry this exercise** starts a new attempt from the current library, tells
you when the exercise version differs from the one reviewed, and, when another
attempt is live, asks whether to resume it or end it first.

```text
$ codesignal-sim test --workspace-root "$PWD" --json
{"ok": false, "error": {"code": "candidate_failure", "message": "one or more test groups did not pass"}}  # exit 5; score stored

$ codesignal-sim history --workspace-root "$PWD" --status abandoned --json
{"ok": true, "result": {"items": [{"attempt_id": "2e250f47-…", "status": "abandoned",
  "practice_score": {"passed_levels": 0, …}, "review_available": false, …}], "next_cursor": null, "warnings": []}}

$ codesignal-sim review --workspace-root "$PWD" --attempt 2e250f47-… --no-source --json
{"ok": true, "result": {"status": "abandoned", "score": null, "practice_score": {…}, "source_binding": "not_applicable",
  "assessment": {"content_identity": "pinned", "content_version": "records-1", …}}}

$ codesignal-sim review --workspace-root "$PWD" --attempt 0f1c2d3e-4a5b-4c6d-8e9f-0a1b2c3d4e5f --json
{"ok": false, "error": {"code": "session_unavailable", "message": "attempt is unavailable: 0f1c2d3e-…"}}  # exit 3

$ codesignal-sim history --workspace-root "$PWD" --status active --cursor <cursor issued for another filter> --json
{"ok": false, "error": {"code": "invalid_input", "message": "history cursor is invalid"}}                  # exit 2
```

### Record compatibility

This release reads `session/v1` records written by earlier releases and writes
`session/v2`. Older binaries do not need to read v2 records, and running
different releases as writers against the same workspace is unsupported. No
claim is made that an older binary can safely work in a workspace this release
has written to.

Open the complete printed `127.0.0.1` URL, including the `#...` fragment. That
fragment is a private per-launch capability. Do not paste the URL into chat,
tickets, screenshots, or logs.

The browser UI and direct CLI are two transports for the same attempt. The
server-authoritative timer, scoring, and lifecycle own the result. At the
deadline, the browser becomes read-only and **Submit** is disabled.
The CLI remains the explicit fallback:

```sh
codesignal-sim submit --workspace-root "$workspace"
```

Full command contract, exits, and recovery:
[docs/cli-contract.md](docs/cli-contract.md).
During a timed attempt, follow [AGENTS.md](AGENTS.md) and
[docs/agent-safety.md](docs/agent-safety.md).

```text
workspace/
├── .cache/codesignal-fixtures/6aab304/  # ignored FETCH_ONLY cache (File Storage only)
└── attempts/
    ├── active.json                      # selected UUID
    ├── .restart-journal/                # in-flight restart transactions (normally empty)
    ├── .restart-completed/              # immutable restart receipts by operation ID
    └── <uuid>/
        ├── session.json                 # authoritative lifecycle state (session/v2)
        ├── events.jsonl
        ├── review.json                  # immutable submission review, once submitted
        ├── STATUS.md                    # generated view
        └── COACHING.md                  # your notes
```

`attempts/<uuid>/session.json` is the session record. Do not hand-edit it.

## Install

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --no-deps -e .
codesignal-sim --help
python3 -m codesignal_practice_simulator --help
```

For a previously built wheel, anywhere outside this checkout and with no
network:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --no-index --no-deps /path/to/codesignal_practice_simulator-*.whl
codesignal-sim --help
codesignal-sim catalog --workspace-root "$PWD" --json       # originals ready, File Storage fetch_required
codesignal-sim start --workspace-root "$PWD" --assessment account_ledger
```

The wheel bundles the browser assets and the two original exercises (their
`.py` files are byte-compiled by pip on install; the resulting `__pycache__`
is tolerated and never staged into an attempt). File Storage still needs an
explicit `fetch`.

## After you submit

[`study/`](study/), [`solution/`](solution/), and [`notes/`](notes/) are
opt-in learning material. Do not use them during a live attempt.

At Level 4, the fetched visible test treats `ROLLBACK` as log-only, while the
written task requires restoring state. Implement the written specification.
See [notes/level4-rollback-discrepancy.md](notes/level4-rollback-discrepancy.md).

## Troubleshooting

| Symptom | Safe action |
| --- | --- |
| `start` says the fixture cache is unavailable, or File Storage shows "Setup required" | Re-run `codesignal-sim fetch --workspace-root "$PWD"`. Do not edit cache files. The originals do not need this. |
| An original shows "Setup required" / `packaged_content_invalid` | The installed package is incomplete or altered. Reinstall the wheel; never edit files under `resources/assessments/`. |
| `start` exits 4 with `live_selection` | An attempt is already live. Resume it, or end/restart it first (browser controls, or `abandon`/`restart --expected-revision`). |
| `abandon`/`restart` exit 4 with `stale_revision` | Your view is behind. Read `status`, use the current `revision`, and retry. |
| `restart` exits 3 with `recovery_pending` | The restart is recorded but not published. Run the same `restart` again with the same `--operation-id`; do not start a new attempt. |
| `restart` exits 4 with `operation_conflict` | That operation ID was already used with different arguments. Mint a new UUID for a different request. |
| A review shows "submitted-source binding unavailable" | The attempt was submitted by an older release; the stored score is real, the shown file is the current one and is not proven to be the submitted bytes. |
| A review or listing row says the record is unavailable or corrupt | The stored record cannot be read safely. Nothing is repaired on read; keep the directory for inspection and start fresh attempts as needed. |
| The browser does not open, or the port is busy | `codesignal-sim web --workspace-root "$PWD" --port 0 --no-open`, then open the new URL. |
| The attempt expired in the browser | It is read-only. Finalize once with CLI `submit` if you want a stored result. |
| Editor assets fail to load | Reinstall the package or wheel. Do not point the UI at a CDN. |

## Contributors

```sh
just verify                 # legacy checks, unit suite, end-to-end suite, whitespace
python3 scripts/run_legacy_checks.py
just check content          # bundled originals: allowlist, manifest hashes, runner entry points
just check frontend         # webui metadata, lockfile, licenses
just build assets && just build assets-check
just check browser          # Playwright journeys with the locked privacy reporters
just check wheel            # build sdist+wheel, install outside the checkout, run the browser suite offline
```

`run_legacy_checks.py` verifies tracked mappings, cache hashes, and the Git
boundary, then runs first-party solution and study checks. It does not run the fetched
upstream compatibility test. Its `fixture-cache` scope needs a fetched cache.

`just check wheel` needs an interpreter with `setuptools` (>= 61), `wheel`,
`pip` and `venv`; with the `build` distribution it runs `python -m build
--no-isolation`, and without it the check calls the setuptools PEP 517 hooks
directly (reported as `build_mode: pep517-hooks`). Set `ASSET_BUILDER` to
choose the interpreter. Neither path downloads anything.

The simulator is a local practice tool, not an official CodeSignal evaluator.
No local result is equivalent to official hidden tests.
