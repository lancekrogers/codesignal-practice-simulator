"""Shared test-only controls for browser fixture servers."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path


class FileClock:
    """A clock advanced by the harness outside the HTTP API."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def now(self) -> datetime:
        value = self.path.read_text(encoding="utf-8").strip()
        return datetime.fromisoformat(value).astimezone(timezone.utc)


def clock_from_environment() -> FileClock | None:
    configured = os.environ.get("SIMULATOR_CLOCK_FILE")
    return FileClock(Path(configured)) if configured else None


def browser_opener_from_environment():
    configured = os.environ.get("SIMULATOR_BROWSER_OPENER_FILE")

    def record(url: str) -> None:
        if not configured:
            return
        origin = url.split("/#", 1)[0]
        with Path(configured).open("a", encoding="utf-8") as stream:
            stream.write(f"{origin}\n")

    return record


def install_score_call_recorder(application: object) -> None:
    configured = os.environ.get("SIMULATOR_SCORE_CALLS_FILE")
    if not configured:
        return
    original_factory = application.scorer_factory

    def recording_factory(definition):
        scorer = original_factory(definition)

        def recording_scorer(attempt):
            with Path(configured).open("a", encoding="utf-8") as stream:
                stream.write(f"{attempt}\n")
            return scorer(attempt)

        return recording_scorer

    application.scorer_factory = recording_factory
