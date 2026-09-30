#!/usr/bin/env python3
"""Slow a worker that drains a faster producer.

Jobs wait on a normal queue. The bucket is in drop mode, so the worker
sleeps until ``allow()`` admits the next job. That is separate from the
bucket's own queue mode.

    python demo/demo_worker.py --jobs 20 --rate 1.0 --capacity 5
"""

from __future__ import annotations

import argparse
import queue
import threading
import time
from typing import Any

from lupaxa.leaky_bucket import LeakyBucket


def producer(jobs: queue.Queue[Any], count: int, delay: float) -> None:
    """Put ``count`` jobs on the queue, then a sentinel."""
    for index in range(count):
        jobs.put({"id": index, "payload": f"item-{index}"})
        time.sleep(delay)
    jobs.put(None)


def consumer(jobs: queue.Queue[Any], bucket: LeakyBucket) -> None:
    """Process one job each time drop mode admits a unit."""
    while True:
        item = jobs.get()
        if item is None:
            jobs.task_done()
            break

        while not bucket.allow(1.0):
            time.sleep(0.01)

        snap = bucket.peek()
        print(
            f"[worker] processed {item['payload']} | "
            f"bucket level={snap['level']:.2f} "
            f"fill={snap['fill_ratio']:.2f} ({snap['fill_percent']:.1f}%)"
        )
        jobs.task_done()

    bucket.shutdown()
    print("[worker] shutdown complete")


def main() -> None:
    """Start a consumer thread and produce jobs from the main thread."""
    parser = argparse.ArgumentParser(description="Queue plus a rate-limited worker")
    parser.add_argument("--jobs", type=int, default=20, help="How many jobs to produce")
    parser.add_argument(
        "--produce-delay",
        type=float,
        default=0.05,
        help="Delay between produced jobs, in seconds",
    )
    parser.add_argument("--capacity", type=float, default=5.0, help="Bucket capacity")
    parser.add_argument("--rate", type=float, default=1.0, help="Leak rate in units per second")
    parser.add_argument(
        "--drain-on-shutdown",
        action="store_true",
        help="Drain the bucket on shutdown",
    )
    args = parser.parse_args()

    jobs: queue.Queue[Any] = queue.Queue()
    bucket = LeakyBucket(
        capacity=args.capacity,
        leak_rate=args.rate,
        mode="drop",
        drain_on_shutdown=args.drain_on_shutdown,
    )

    worker = threading.Thread(target=consumer, args=(jobs, bucket))
    worker.start()
    producer(jobs, args.jobs, args.produce_delay)
    jobs.join()
    worker.join()
    print("[main] all jobs processed")


if __name__ == "__main__":
    main()
