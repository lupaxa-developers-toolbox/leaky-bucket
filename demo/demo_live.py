#!/usr/bin/env python3
"""Watch drop or queue mode on the real clock.

Pass flags to change capacity, leak rate, and how often an event
arrives. The other demos use fixed scenarios.

    python demo/demo_live.py --queue --capacity 5 --rate 1 --events 10
"""

from __future__ import annotations

import argparse
import time

from lupaxa.leaky_bucket import LeakyBucket


def main() -> None:
    """Print a short admission trace for drop or queue mode."""
    parser = argparse.ArgumentParser(description="Leaky bucket demo with drop/queue modes")
    parser.add_argument("--capacity", type=float, default=10.0, help="Bucket capacity")
    parser.add_argument("--rate", type=float, default=2.0, help="Leak rate (units/sec)")
    parser.add_argument("--interval", type=float, default=0.5, help="Pause between events (sec)")
    parser.add_argument("--events", type=int, default=20, help="How many events to try")
    parser.add_argument(
        "--drain-on-shutdown",
        action="store_true",
        help="Drain the bucket and queue on shutdown",
    )
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--drop",
        action="store_true",
        help="Drop events when the bucket is full",
    )
    mode_group.add_argument(
        "--queue",
        action="store_true",
        help="Queue events when the bucket is full",
    )
    args = parser.parse_args()

    mode = "drop" if args.drop else "queue"
    bucket = LeakyBucket(
        capacity=args.capacity,
        leak_rate=args.rate,
        mode=mode,
        raise_on_overflow=False,
        drain_on_shutdown=args.drain_on_shutdown,
    )

    print(
        f"Running in mode={mode}, capacity={args.capacity}, leak_rate={args.rate}/s, "
        f"drain_on_shutdown={args.drain_on_shutdown}"
    )
    print("Idx | result          | level | remaining | pending | fill | fill (%)")
    print("-----------------------------------------------------------------------")

    for index in range(args.events):
        ok = bucket.allow()
        snapshot = bucket.peek()
        if mode == "drop":
            status = "allowed" if ok else "REJECTED"
        else:
            status = "accepted/queued" if snapshot["pending"] else "accepted"
        print(
            f"{index:3d} | {status:15s} | "
            f"{snapshot['level']:5.2f} | "
            f"{snapshot['remaining']:9.2f} | "
            f"{snapshot['pending']:7d} | "
            f"{snapshot['fill_ratio']:.2f} | "
            f"{snapshot['fill_percent']:6.1f}%"
        )
        time.sleep(args.interval)

    bucket.shutdown()


if __name__ == "__main__":
    main()
