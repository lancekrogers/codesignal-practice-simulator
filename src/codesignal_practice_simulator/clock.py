"""Injectable UTC time for session services."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    """Provides the current UTC time."""

    def now(self) -> datetime:
        """Return a timezone-aware timestamp in UTC."""


class UTCClock:
    """Production clock backed by the system's UTC time."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)
