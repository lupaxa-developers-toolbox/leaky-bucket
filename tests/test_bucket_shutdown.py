"""Shutdown drops or drains according to ``drain_on_shutdown``."""

from __future__ import annotations

import time

from lupaxa.leaky_bucket import LeakyBucket
from lupaxa.leaky_bucket.timeutils import SystemTimeProvider


def test_shutdown_drops_when_flag_false(fake_time) -> None:
    bucket = LeakyBucket(
        capacity=3,
        leak_rate=1,
        time_provider=fake_time,
        mode="queue",
        drain_on_shutdown=False,
    )

    assert bucket.allow() is True
    assert bucket.allow() is True
    assert bucket.allow() is True
    assert bucket.allow() is True
    snap = bucket.peek()
    assert snap["pending"] == 1

    bucket.shutdown()

    snap = bucket.peek()
    assert snap["level"] == 0.0
    assert snap["pending"] == 0
    assert snap["fill_ratio"] == 0.0


def test_shutdown_drains_when_flag_true(fake_time) -> None:
    bucket = LeakyBucket(
        capacity=3,
        leak_rate=1,
        time_provider=fake_time,
        mode="queue",
        drain_on_shutdown=True,
    )

    assert bucket.allow() is True
    assert bucket.allow() is True
    assert bucket.allow() is True
    assert bucket.allow() is True
    assert bucket.allow() is True

    snap = bucket.peek()
    assert snap["level"] == 3.0
    assert snap["pending"] == 2

    bucket.shutdown()

    snap = bucket.peek()
    assert snap["level"] == 0.0
    assert snap["pending"] == 0


def test_shutdown_with_real_time_provider_does_not_crash() -> None:
    bucket = LeakyBucket(
        capacity=1,
        leak_rate=10,
        time_provider=SystemTimeProvider(),
        mode="queue",
        drain_on_shutdown=True,
    )

    assert bucket.allow() is True
    assert bucket.allow() is True

    started = time.time()
    bucket.shutdown()
    elapsed = time.time() - started
    assert elapsed < 1.0

    snap = bucket.peek()
    assert snap["level"] == 0.0
    assert snap["pending"] == 0
