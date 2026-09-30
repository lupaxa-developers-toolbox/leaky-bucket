"""Leaky-bucket rate limiter."""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from .exceptions import BucketOverflow, InvalidBucketMode, LeakyBucketError
from .timeutils import AdvanceableTimeProvider, SystemTimeProvider, TimeProvider


@dataclass
class LeakyBucket:
    """Rate limiter that leaks at a steady rate.

    ``mode="drop"`` rejects arrivals that do not fit. ``mode="queue"``
    holds them until leaked capacity can admit them. ``drain_on_shutdown``
    chooses whether :meth:`shutdown` waits for the bucket to empty.

    ``capacity`` and ``leak_rate`` must be finite and greater than zero.
    ``raise_on_overflow`` applies only in drop mode. Public methods share
    one lock, so one bucket can be used from several threads.
    """

    capacity: float
    leak_rate: float
    time_provider: TimeProvider = field(default_factory=SystemTimeProvider)
    mode: str = "drop"
    raise_on_overflow: bool = False
    drain_on_shutdown: bool = False

    _level: float = field(default=0.0, init=False)
    _last_check: float | None = field(default=None, init=False)
    _pending: deque[float] = field(default_factory=deque, init=False)
    _lock: threading.RLock = field(
        default_factory=threading.RLock, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self.mode not in ("drop", "queue"):
            message = f"Unsupported mode '{self.mode}', expected 'drop' or 'queue'"
            raise InvalidBucketMode(message)
        if self.mode == "queue" and self.raise_on_overflow:
            message = "raise_on_overflow applies to drop mode; queue mode holds arrivals"
            raise LeakyBucketError(message)
        if not math.isfinite(self.capacity) or self.capacity <= 0:
            message = "capacity must be a finite number greater than 0"
            raise LeakyBucketError(message)
        if not math.isfinite(self.leak_rate) or self.leak_rate <= 0:
            message = "leak_rate must be a finite number greater than 0"
            raise LeakyBucketError(message)

    def _leak(self) -> None:
        """Leak for the elapsed time, then admit queued amounts that fit."""
        now = self.time_provider.now()
        if self._last_check is None:
            self._last_check = now
            return

        elapsed = now - self._last_check
        if elapsed > 0:
            self._level = max(0.0, self._level - elapsed * self.leak_rate)
            self._last_check = now
        elif elapsed == 0:
            self._last_check = now
        self._flush_queue()

    def _flush_queue(self) -> None:
        """Move queued amounts into the bucket while they fit."""
        while self._pending and self._level + self._pending[0] <= self.capacity:
            self._level += self._pending.popleft()

    def _advance(self, seconds: float) -> None:
        """Move the clock forward by ``seconds``."""
        if seconds <= 0:
            return
        provider = self.time_provider
        if isinstance(provider, AdvanceableTimeProvider):
            provider.advance(seconds)
        else:
            time.sleep(seconds)

    def _fill_ratio_unlocked(self) -> float:
        return self._level / self.capacity

    def allow(self, amount: float = 1.0) -> bool:
        """Try to add ``amount`` units.

        ``amount`` must be finite, greater than zero, and no larger than
        ``capacity``. Returns ``True`` when the amount is accepted or
        queued. In drop mode a full bucket returns ``False``, or raises
        :class:`BucketOverflow` when ``raise_on_overflow`` is set.
        Queue mode accepts every amount that can eventually fit.
        """
        with self._lock:
            if not math.isfinite(amount) or amount <= 0:
                message = "amount must be a finite number greater than 0"
                raise LeakyBucketError(message)

            self._leak()

            if amount > self.capacity:
                if self.mode == "queue" or self.raise_on_overflow:
                    message = (
                        f"Bucket overflow: current={self._level}, "
                        f"amount={amount}, capacity={self.capacity}"
                    )
                    raise BucketOverflow(message)
                return False

            if self._level + amount <= self.capacity:
                self._level += amount
                return True

            if self.mode == "drop":
                if self.raise_on_overflow:
                    message = (
                        f"Bucket overflow: current={self._level}, "
                        f"amount={amount}, capacity={self.capacity}"
                    )
                    raise BucketOverflow(message)
                return False

            self._pending.append(amount)
            return True

    def current_level(self) -> float:
        """Return the current fill level after leaking."""
        with self._lock:
            self._leak()
            return self._level

    def remaining_capacity(self) -> float:
        """Return unused capacity after leaking."""
        with self._lock:
            self._leak()
            return max(0.0, self.capacity - self._level)

    def pending_count(self) -> int:
        """Return how many amounts are waiting in the queue."""
        with self._lock:
            self._leak()
            return len(self._pending)

    def has_pending(self) -> bool:
        """Return whether the queue holds any amounts."""
        with self._lock:
            self._leak()
            return bool(self._pending)

    def fill_ratio(self) -> float:
        """Return how full the bucket is, from 0.0 to 1.0."""
        with self._lock:
            self._leak()
            return self._fill_ratio_unlocked()

    def fill_percent(self) -> float:
        """Return how full the bucket is, from 0 to 100."""
        return self.fill_ratio() * 100.0

    def peek(self) -> dict[str, Any]:
        """Return a snapshot of level, remaining capacity, and fill.

        Every field is taken after a single leak, so the ratio matches
        the reported level.
        """
        with self._lock:
            self._leak()
            ratio = self._fill_ratio_unlocked()
            return {
                "level": round(self._level, 3),
                "remaining": round(max(0.0, self.capacity - self._level), 3),
                "pending": len(self._pending),
                "fill_ratio": round(ratio, 3),
                "fill_percent": round(ratio * 100.0, 1),
            }

    def shutdown(self) -> None:
        """Drop remaining work, or leak until the bucket and queue are empty.

        Draining advances the clock by the exact wait for the next queued
        amount, then by the time needed to empty the bucket.
        """
        with self._lock:
            if not self.drain_on_shutdown:
                self._level = 0.0
                self._pending.clear()
                return

            self._leak()
            while self._pending:
                head = self._pending[0]
                if self._level + head <= self.capacity:
                    self._level += self._pending.popleft()
                    continue
                target = self.capacity - head
                self._advance((self._level - target) / self.leak_rate)
                self._last_check = self.time_provider.now()
                self._level = self.capacity
                self._pending.popleft()

            if self._level > 0:
                self._advance(self._level / self.leak_rate)
                self._last_check = self.time_provider.now()
                self._level = 0.0
