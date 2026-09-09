#!/usr/bin/env python3
"""Score a `simulation.py` the way the assessment does: level by level.

Each level is run as its own unittest invocation against the bundled
`test_simulation.py`, so a level-3 crash cannot take level 1 down with it —
that is what "partial credit" means in these assessments.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ATTEMPTS = ROOT / "attempts"
SOLUTION = ROOT / "solution"

LEVELS = (
    (1, "Initial design & basic functions", "10-15m"),
    (2, "Data structures & data processing", "20-30m"),
    (3, "Refactoring & encapsulation (TTLs)", "30-60m"),
    (4, "Extending design & functionality (rollback)", "30-60m"),
)

TEST_CLASS = "test_simulation.TestSimulateCodingFramework"
ERROR_LINE = re.compile(r"^(?:\w+\.)*\w*(?:Error|Exception)\b.*")


def latest_attempt() -> Path | None:
    candidates = [path for path in ATTEMPTS.glob("*") if (path / "simulation.py").is_file()]
    return max(candidates, key=lambda path: path.name) if candidates else None


def resolve_target(raw: str | None) -> Path:
    if raw:
        target = Path(raw).expanduser().resolve()
    else:
        found = latest_attempt()
        if found is None:
            raise SystemExit(
                "no attempt found — run `just practice` first, "
                "or pass --dir solution to score the reference solution"
            )
        target = found
    if not (target / "simulation.py").is_file():
        raise SystemExit(f"no simulation.py in {target}")
    if not (target / "test_simulation.py").is_file():
        raise SystemExit(f"no test_simulation.py in {target}")
    return target


def run_level(target: Path, level: int) -> tuple[bool, str]:
    """Run one level's test group. Returns (passed, first error line)."""
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", f"{TEST_CLASS}.test_group_{level}"],
        cwd=target,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        return True, ""
    combined = f"{completed.stderr}\n{completed.stdout}"
    for line in combined.splitlines():
        stripped = line.strip()
        if ERROR_LINE.match(stripped):
            return False, stripped[:160]
    return False, "failed"


def timing(target: Path) -> dict | None:
    meta_path = target / "attempt.json"
    if not meta_path.is_file():
        return None
    meta = json.loads(meta_path.read_text())
    now = datetime.now(timezone.utc)
    started = datetime.fromisoformat(meta["started_at"])
    deadline = datetime.fromisoformat(meta["deadline_at"])
    return {
        "started_at": meta["started_at"],
        "deadline_at": meta["deadline_at"],
        "limit_minutes": meta["limit_minutes"],
        "elapsed_seconds": int((now - started).total_seconds()),
        "remaining_seconds": int((deadline - now).total_seconds()),
    }


def clock(seconds: int) -> str:
    sign = "-" if seconds < 0 else ""
    seconds = abs(seconds)
    return f"{sign}{seconds // 3600:d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}"


def render_time(info: dict) -> None:
    remaining = info["remaining_seconds"]
    state = "OVER TIME" if remaining < 0 else "remaining"
    print(f"  elapsed   {clock(info['elapsed_seconds'])} of {info['limit_minutes']} min")
    print(f"  {state:<9} {clock(remaining)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", help="directory to score (default: newest attempt)")
    parser.add_argument("--level", type=int, choices=[1, 2, 3, 4], help="score one level")
    parser.add_argument("--time-only", action="store_true", help="print the clock only")
    parser.add_argument("--print-dir", action="store_true", help="print the resolved directory and exit")
    parser.add_argument("--submit", action="store_true", help="write RESULT.md")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    target = resolve_target(args.dir)
    if args.print_dir:
        print(target)
        return 0
    info = timing(target)

    if args.time_only:
        if info is None:
            raise SystemExit(f"{target} is not a timed attempt")
        render_time(info)
        return 0

    levels = [row for row in LEVELS if args.level in (None, row[0])]
    results = []
    for number, title, budget in levels:
        passed, detail = run_level(target, number)
        results.append(
            {"level": number, "title": title, "budget": budget, "passed": passed, "detail": detail}
        )

    passed_count = sum(1 for row in results if row["passed"])
    # Levels are sequential: your real score is how far you got without a gap.
    reached = 0
    for row in sorted(results, key=lambda row: row["level"]):
        if not row["passed"]:
            break
        reached = row["level"]

    if args.json:
        print(json.dumps(
            {
                "schema_version": "scorecard/v1",
                "target": str(target),
                "levels": results,
                "levels_passed": passed_count,
                "level_reached": reached,
                "timing": info,
            },
            indent=2,
        ))
        return 0 if passed_count == len(results) else 1

    label = target.name if target.parent == ATTEMPTS else str(target.relative_to(ROOT))
    print(f"  scorecard — {label}")
    print("  ┌───────┬──────────────────────────────────────────────┬────────┬────────┐")
    print("  │ level │ focus                                        │ budget │ result │")
    print("  ├───────┼──────────────────────────────────────────────┼────────┼────────┤")
    for row in results:
        mark = " PASS " if row["passed"] else " FAIL "
        print(f"  │   {row['level']}   │ {row['title']:<44} │ {row['budget']:<6} │ {mark} │")
    print("  └───────┴──────────────────────────────────────────────┴────────┴────────┘")
    for row in results:
        if not row["passed"] and row["detail"]:
            print(f"    L{row['level']}: {row['detail']}")
    if args.level is None:
        print(f"  levels passed  {passed_count}/{len(results)}   (sequential reach: {reached})")
    if info is not None:
        render_time(info)

    if args.submit:
        result_path = target / "RESULT.md"
        lines = [
            f"# Result — {target.name}",
            "",
            f"- Levels passed: {passed_count}/{len(results)}",
            f"- Sequential reach: level {reached}",
        ]
        if info is not None:
            lines.append(f"- Elapsed: {clock(info['elapsed_seconds'])} of {info['limit_minutes']} min")
        lines += ["", "| Level | Focus | Budget | Result |", "| --- | --- | --- | --- |"]
        lines += [
            f"| {row['level']} | {row['title']} | {row['budget']} | "
            f"{'PASS' if row['passed'] else 'FAIL'} |"
            for row in results
        ]
        lines += ["", "## What to fix next", "", "-", ""]
        result_path.write_text("\n".join(lines))
        print(f"  wrote {result_path.relative_to(ROOT)}")

    return 0 if passed_count == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
