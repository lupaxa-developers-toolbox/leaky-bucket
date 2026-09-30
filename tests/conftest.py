"""Shared fixtures."""

from __future__ import annotations

import pytest

from lupaxa.leaky_bucket.timeutils import TimeProvider


class FakeTime(TimeProvider):
    """Advanceable clock for tests."""

    def __init__(self, start: float = 0.0) -> None:
        self._t = start

    def now(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


@pytest.fixture
def fake_time() -> FakeTime:
    return FakeTime()
