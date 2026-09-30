"""Limits, snapshot consistency, and concurrent admission."""

from __future__ import annotations

import threading
import time

import pytest

from lupaxa.leaky_bucket import BucketOverflow, LeakyBucket, LeakyBucketError
from lupaxa.leaky_bucket.timeutils import SystemTimeProvider, TimeProvider


class MovingClock(TimeProvider):
    """Clock that jumps forward on every read."""

    def __init__(self) -> None:
        self._t = 0.0

    def now(self) -> float:
        current = self._t
        self._t += 0.5
        return current


class RecordingClock(TimeProvider):
    """Advanceable clock that records each step."""

    def __init__(self) -> None:
        self._t = 0.0
        self.advances: list[float] = []

    def now(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self.advances.append(seconds)
        self._t += seconds


def test_peek_fields_share_one_leak() -> None:
    clock = MovingClock()
    bucket = LeakyBucket(capacity=5, leak_rate=1, time_provider=clock, mode="drop")
    bucket.allow()
    snap = bucket.peek()
    assert snap["fill_ratio"] == pytest.approx(snap["level"] / 5)
    assert snap["fill_percent"] == pytest.approx(snap["fill_ratio"] * 100)


def test_non_positive_capacity_and_rate_are_rejected(fake_time) -> None:
    with pytest.raises(LeakyBucketError):
        LeakyBucket(capacity=0, leak_rate=1, time_provider=fake_time)
    with pytest.raises(LeakyBucketError):
        LeakyBucket(capacity=-1, leak_rate=1, time_provider=fake_time)
    with pytest.raises(LeakyBucketError):
        LeakyBucket(capacity=1, leak_rate=0, time_provider=fake_time)
    with pytest.raises(LeakyBucketError):
        LeakyBucket(capacity=1, leak_rate=-2, time_provider=fake_time)
    with pytest.raises(LeakyBucketError):
        LeakyBucket(capacity=float("nan"), leak_rate=1, time_provider=fake_time)
    with pytest.raises(LeakyBucketError):
        LeakyBucket(capacity=1, leak_rate=float("inf"), time_provider=fake_time)


def test_queue_mode_rejects_raise_on_overflow(fake_time) -> None:
    with pytest.raises(LeakyBucketError):
        LeakyBucket(
            capacity=1,
            leak_rate=1,
            time_provider=fake_time,
            mode="queue",
            raise_on_overflow=True,
        )


def test_non_positive_amount_is_rejected(fake_time) -> None:
    bucket = LeakyBucket(capacity=2, leak_rate=1, time_provider=fake_time)
    with pytest.raises(LeakyBucketError):
        bucket.allow(0)
    with pytest.raises(LeakyBucketError):
        bucket.allow(-1)
    with pytest.raises(LeakyBucketError):
        bucket.allow(float("nan"))
    assert bucket.current_level() == 0


def test_drop_mode_rejects_amount_larger_than_capacity(fake_time) -> None:
    bucket = LeakyBucket(capacity=2, leak_rate=1, time_provider=fake_time, mode="drop")
    assert bucket.allow(3) is False
    assert bucket.current_level() == 0

    raising = LeakyBucket(
        capacity=2,
        leak_rate=1,
        time_provider=fake_time,
        mode="drop",
        raise_on_overflow=True,
    )
    with pytest.raises(BucketOverflow):
        raising.allow(3)


def test_queue_mode_rejects_amount_larger_than_capacity(fake_time) -> None:
    bucket = LeakyBucket(capacity=2, leak_rate=1, time_provider=fake_time, mode="queue")
    with pytest.raises(BucketOverflow):
        bucket.allow(3)
    assert bucket.pending_count() == 0
    assert bucket.current_level() == 0


def test_drop_mode_raises_when_full(fake_time) -> None:
    bucket = LeakyBucket(
        capacity=1,
        leak_rate=1,
        time_provider=fake_time,
        mode="drop",
        raise_on_overflow=True,
    )
    assert bucket.allow() is True
    with pytest.raises(BucketOverflow):
        bucket.allow()


def test_shutdown_drain_advances_once_per_wait() -> None:
    clock = RecordingClock()
    bucket = LeakyBucket(
        capacity=2,
        leak_rate=1,
        time_provider=clock,
        mode="queue",
        drain_on_shutdown=True,
    )
    assert bucket.allow() is True
    assert bucket.allow() is True
    assert bucket.allow() is True
    bucket.shutdown()
    assert clock.advances == pytest.approx([1.0, 2.0])
    assert bucket.peek()["level"] == 0.0
    assert bucket.peek()["pending"] == 0


def test_system_clock_matches_monotonic() -> None:
    now = SystemTimeProvider().now()
    assert abs(now - time.monotonic()) < 1


def test_concurrent_drop_does_not_exceed_capacity(fake_time) -> None:
    bucket = LeakyBucket(capacity=50, leak_rate=1, time_provider=fake_time, mode="drop")
    accepted: list[int] = []
    guard = threading.Lock()

    def worker() -> None:
        local = 0
        for _ in range(20):
            if bucket.allow():
                local += 1
        with guard:
            accepted.append(local)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sum(accepted) == 50
    assert bucket.current_level() == 50
