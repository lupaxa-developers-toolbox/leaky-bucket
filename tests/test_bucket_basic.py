"""Admission, leak, and peek behaviour."""

from __future__ import annotations

import pytest

from lupaxa.leaky_bucket import InvalidBucketMode, LeakyBucket


def test_allow_in_drop_mode_with_capacity(fake_time) -> None:
    bucket = LeakyBucket(
        capacity=3,
        leak_rate=1,
        time_provider=fake_time,
        mode="drop",
    )

    assert bucket.allow() is True
    assert bucket.allow() is True
    assert bucket.allow() is True
    assert bucket.allow() is False

    fake_time.advance(1.0)
    assert bucket.allow() is True


def test_queue_mode_never_returns_false(fake_time) -> None:
    bucket = LeakyBucket(
        capacity=2,
        leak_rate=1,
        time_provider=fake_time,
        mode="queue",
    )

    assert bucket.allow() is True
    assert bucket.allow() is True
    assert bucket.allow() is True
    snap = bucket.peek()
    assert snap["pending"] == 1


def test_leak_and_flush_queue(fake_time) -> None:
    bucket = LeakyBucket(
        capacity=2,
        leak_rate=1,
        time_provider=fake_time,
        mode="queue",
    )

    assert bucket.allow() is True
    assert bucket.allow() is True
    assert bucket.allow() is True
    assert bucket.allow() is True
    snap = bucket.peek()
    assert snap["level"] == 2.0
    assert snap["pending"] == 2

    fake_time.advance(1.0)
    snap = bucket.peek()
    assert snap["level"] == 2.0
    assert snap["pending"] == 1

    fake_time.advance(1.0)
    snap = bucket.peek()
    assert snap["level"] == 2.0
    assert snap["pending"] == 0


def test_peek_contains_expected_fields(fake_time) -> None:
    bucket = LeakyBucket(
        capacity=5,
        leak_rate=1,
        time_provider=fake_time,
        mode="drop",
    )
    bucket.allow()
    snap = bucket.peek()
    assert "level" in snap
    assert "remaining" in snap
    assert "pending" in snap
    assert "fill_ratio" in snap
    assert "fill_percent" in snap
    assert snap["level"] == 1.0
    assert snap["remaining"] == 4.0
    assert snap["fill_ratio"] == 0.2
    assert snap["fill_percent"] == 20.0


def test_invalid_mode_raises(fake_time) -> None:
    with pytest.raises(InvalidBucketMode):
        LeakyBucket(
            capacity=1,
            leak_rate=1,
            time_provider=fake_time,
            mode="banana",
        )
