#!/usr/bin/env python3
"""Compare drop, queue, and drain-on-shutdown on a fake clock.

Nothing sleeps. Each run advances time by a fixed step so the three
shutdown policies can be read side by side.

    python demo/demo_timeline.py
"""

from __future__ import annotations

from lupaxa.leaky_bucket import LeakyBucket, TimeProvider


class FakeTime(TimeProvider):
    """Advanceable clock for a predictable trace."""

    def __init__(self, start: float = 0.0) -> None:
        self._t = start

    def now(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


def run_simulation(mode: str, *, drain_on_shutdown: bool) -> None:
    """Print one timeline for ``mode``."""
    print(f"\n=== Simulation in mode={mode}, drain_on_shutdown={drain_on_shutdown} ===")

    clock = FakeTime()
    bucket = LeakyBucket(
        capacity=5.0,
        leak_rate=1.0,
        time_provider=clock,
        mode=mode,
        raise_on_overflow=False,
        drain_on_shutdown=drain_on_shutdown,
    )

    print("step | time  | allowed | level | remaining | pending | fill | fill (%)")
    print("------------------------------------------------------------------------")

    for step in range(12):
        allowed = bucket.allow(1.0)
        snap = bucket.peek()
        print(
            f"{step:4d} | {clock.now():4.1f}s | "
            f"{allowed!s:7s} | "
            f"{snap['level']:5.2f} | "
            f"{snap['remaining']:9.2f} | "
            f"{snap['pending']:7d} | "
            f"{snap['fill_ratio']:.2f} | "
            f"{snap['fill_percent']:6.1f}%"
        )
        clock.advance(0.3)

    print("\n-- shutdown called --")
    bucket.shutdown()
    final = bucket.peek()
    print(
        f"after shutdown: t={clock.now():.1f}s "
        f"level={final['level']:.2f} "
        f"remaining={final['remaining']:.2f} "
        f"pending={final['pending']} "
        f"fill={final['fill_ratio']:.2f} "
        f"fill%={final['fill_percent']:.1f}%"
    )


def main() -> None:
    """Run drop, queue-and-drop, and queue-and-drain traces."""
    run_simulation("drop", drain_on_shutdown=False)
    run_simulation("queue", drain_on_shutdown=False)
    run_simulation("queue", drain_on_shutdown=True)


if __name__ == "__main__":
    main()
