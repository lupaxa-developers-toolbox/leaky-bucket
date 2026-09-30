#!/usr/bin/env python3
"""Copy a file without exceeding a byte rate.

Each ``allow()`` charges the size of the chunk, not a single event.
The chunk must fit in the bucket, so it cannot be larger than the rate.

    python demo/demo_copy.py input.txt output.txt --rate 100000
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from lupaxa.leaky_bucket import LeakyBucket


def copy_with_rate_limit(
    src: Path,
    dst: Path,
    rate_bytes_per_sec: int,
    chunk_size: int,
) -> None:
    """Copy ``src`` to ``dst``, waiting whenever the bucket is full."""
    if rate_bytes_per_sec <= 0:
        raise SystemExit("rate must be greater than 0")
    if chunk_size <= 0:
        raise SystemExit("chunk must be greater than 0")
    if chunk_size > rate_bytes_per_sec:
        message = "chunk must be <= rate, so each read fits in the bucket"
        raise SystemExit(message)

    bucket = LeakyBucket(
        capacity=float(rate_bytes_per_sec),
        leak_rate=float(rate_bytes_per_sec),
        mode="drop",
        drain_on_shutdown=False,
    )

    total = 0
    start = time.time()

    with src.open("rb") as source, dst.open("wb") as destination:
        while True:
            chunk = source.read(chunk_size)
            if not chunk:
                break

            needed = len(chunk)
            while not bucket.allow(needed):
                time.sleep(0.01)

            destination.write(chunk)
            total += needed

            snap = bucket.peek()
            elapsed = time.time() - start
            speed = total / elapsed if elapsed > 0 else 0
            print(
                f"\rCopied {total} bytes in {elapsed:.1f}s "
                f"({speed:,.0f} B/s) | bucket: {snap['fill_ratio']:.2f} "
                f"({snap['fill_percent']:.1f}%)",
                end="",
                flush=True,
            )

    print("\nDone.")


def main() -> None:
    """Parse paths and a byte rate, then copy."""
    parser = argparse.ArgumentParser(description="Copy a file at a limited byte rate")
    parser.add_argument("src", help="Source file")
    parser.add_argument("dst", help="Destination file")
    parser.add_argument(
        "--rate",
        type=int,
        default=100_000,
        help="Maximum copy rate in bytes per second",
    )
    parser.add_argument(
        "--chunk",
        type=int,
        default=32_768,
        help="Read and write size in bytes",
    )
    args = parser.parse_args()

    src = Path(args.src)
    dst = Path(args.dst)
    if not src.exists():
        message = f"Source file does not exist: {src}"
        raise SystemExit(message)

    copy_with_rate_limit(src, dst, args.rate, args.chunk)


if __name__ == "__main__":
    main()
