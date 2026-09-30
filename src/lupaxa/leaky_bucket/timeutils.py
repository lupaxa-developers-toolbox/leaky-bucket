"""Clock sources used by :class:`lupaxa.leaky_bucket.LeakyBucket`."""

from __future__ import annotations

import time
from typing import Protocol, runtime_checkable


class TimeProvider(Protocol):
    """Minimal clock. Anything with ``now() -> float`` can be used."""

    def now(self) -> float:
        """Return the current time in seconds."""


@runtime_checkable
class AdvanceableTimeProvider(TimeProvider, Protocol):
    """Clock that tests and demos can move forward without sleeping."""

    def advance(self, seconds: float) -> None:
        """Move the clock forward by ``seconds``."""


class SystemTimeProvider:
    """Clock backed by :func:`time.monotonic`.

    Monotonic time ignores wall-clock steps, so a backwards adjustment
    cannot refill the bucket.
    """

    def now(self) -> float:
        """Return seconds from a monotonic clock."""
        return time.monotonic()
