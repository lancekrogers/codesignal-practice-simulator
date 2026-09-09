#!/usr/bin/env python3
"""Start a fresh timed attempt at the file_storage assessment.

Copies the untouched assessment (task markdown, starter `simulation.py`, the
bundled tests) into `attempts/<timestamp>/` and starts the clock.  Nothing is
scored here; `scorecard.py` does that.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fixture_contract import FIXTURE_CACHE_ROOT

ROOT = Path(__file__).resolve().parent.parent
ASSESSMENT = ROOT / FIXTURE_CACHE_ROOT / "assessment" / "file_storage"
ATTEMPTS = ROOT / "attempts"
DEFAULT_MINUTES = 90

COPIED_FILES = (
    "level1.md",
    "level2.md",
    "level3.md",
    "level4.md",
    "simulation.py",
    "test_simulation.py",
)

ATTEMPT_NOTES = """# Attempt {slug}

- Started: {started_local}
- Limit: {minutes} minutes (deadline {deadline_local})

## Rules

1. Levels in order. Do not start level N+1 until level N passes.
2. Do not change the existing method signatures.
3. Refactoring earlier levels is expected, not a mistake.

## Log

Jot the time you finished each level; the split is the useful signal.

| Level | Budget | Finished | Notes |
| ----- | ------ | -------- | ----- |
| 1     | 10-15m |          |       |
| 2     | 20-30m |          |       |
| 3     | 30-60m |          |       |
| 4     | 30-60m |          |       |
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--minutes",
        type=int,
        default=DEFAULT_MINUTES,
        help=f"time limit in minutes (default: {DEFAULT_MINUTES})",
    )
    parser.add_argument("--name", help="suffix for the attempt directory")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    started = datetime.now(timezone.utc)
    slug = started.astimezone().strftime("%Y-%m-%dT%H-%M-%S")
    if args.name:
        slug = f"{slug}_{args.name}"
    attempt = ATTEMPTS / slug
    if attempt.exists():
        raise SystemExit(f"attempt already exists: {attempt}")

    missing = [name for name in COPIED_FILES if not (ASSESSMENT / name).is_file()]
    if missing:
        raise SystemExit(
            "fixture cache is incomplete; run "
            "`python3 scripts/fetch_fixture.py --manifest docs/migration-manifest.json` "
            f"before starting an attempt (missing: {', '.join(missing)})"
        )

    attempt.mkdir(parents=True)
    for name in COPIED_FILES:
        shutil.copy2(ASSESSMENT / name, attempt / name)

    deadline = started + timedelta(minutes=args.minutes)
    meta = {
        "schema_version": "attempt/v1",
        "assessment": "file_storage",
        "started_at": started.isoformat(),
        "deadline_at": deadline.isoformat(),
        "limit_minutes": args.minutes,
    }
    (attempt / "attempt.json").write_text(json.dumps(meta, indent=2) + "\n")
    (attempt / "ATTEMPT.md").write_text(
        ATTEMPT_NOTES.format(
            slug=slug,
            started_local=started.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
            deadline_local=deadline.astimezone().strftime("%H:%M:%S %Z"),
            minutes=args.minutes,
        )
    )

    if args.json:
        print(json.dumps({**meta, "path": str(attempt)}, indent=2))
        return 0

    rel = attempt.relative_to(ROOT)
    print("┌───────────────────────────────────────────────────────────────┐")
    print("│  Industry Coding Framework — file_storage                     │")
    print("└───────────────────────────────────────────────────────────────┘")
    print(f"  attempt   {rel}")
    print(f"  started   {started.astimezone():%H:%M:%S}")
    print(f"  deadline  {deadline.astimezone():%H:%M:%S}  ({args.minutes} min)")
    print()
    print(f"  edit      {rel}/simulation.py")
    print(f"  read      {rel}/level1.md   (one level at a time)")
    print()
    print("  just level 1     score a single level")
    print("  just score       score every level")
    print("  just time        time remaining")
    print("  just submit      stop, score, write RESULT.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
