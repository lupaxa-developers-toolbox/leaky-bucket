<p align="center">
  <a href="https://github.com/lupaxa-developers-toolbox">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/organisations/developers-toolbox/readme-logo.png" alt="Developers Toolbox" />
  </a>
</p>

<h1 align="center">Leaky Bucket</h1>

Rate-limit events with a leaky bucket. Arrivals that fit are admitted.
In drop mode the rest are rejected. In queue mode they wait until
leaked capacity can take them.

The PyPI name is `lupaxa-leaky-bucket`. The import path is
`lupaxa.leaky_bucket`. `lupaxa` is a namespace package — there is no
`lupaxa/__init__.py`.

## Install

```bash
pip install lupaxa-leaky-bucket
```

Requires Python 3.10+. There are no runtime dependencies.

From a clone of this repository (editable install):

```bash
make init
make python-install-dev
```

## Usage

`lupaxa-leaky-bucket` is a library only. There is no console script
and no `python -m` entry point.

```python
from lupaxa.leaky_bucket import LeakyBucket

bucket = LeakyBucket(capacity=5, leak_rate=5, mode="drop")

if bucket.allow():
    handle_request()
```

Units are whatever you count: requests, jobs, or bytes. `capacity` is
the burst limit. `leak_rate` is how many units leak per second. Set
both when you construct the bucket. Each must be finite and greater
than zero.

| Parameter            | Default              | Meaning                                                     |
| -------------------- | -------------------- | ----------------------------------------------------------- |
| `capacity`           | required             | Burst limit, in your units                                  |
| `leak_rate`          | required             | Units leaked per second                                     |
| `time_provider`      | `SystemTimeProvider` | Clock with `now() -> float`                                 |
| `mode`               | `"drop"`             | `"drop"` or `"queue"`                                       |
| `raise_on_overflow`  | `False`              | In drop mode, raise `BucketOverflow` instead of `False`     |
| `drain_on_shutdown`  | `False`              | `shutdown()` waits until the bucket and queue are empty     |

`mode` must be `"drop"` or `"queue"`. Anything else raises
`InvalidBucketMode`. `raise_on_overflow=True` is valid only in drop
mode. Queue mode with that flag raises `LeakyBucketError`.

### Admitting work

`allow(amount=1.0)` leaks for the time since the last check, then
tries to add `amount` as a whole. It does not take part of an amount.
`amount` must be finite and greater than zero. A bad amount raises
`LeakyBucketError`.

| Situation                         | Drop mode                                      | Queue mode                          |
| --------------------------------- | ---------------------------------------------- | ----------------------------------- |
| Amount fits now                   | Add it and return `True`                       | Add it and return `True`            |
| Amount fits later, not now        | Return `False`, or raise `BucketOverflow`      | Append it and return `True`         |
| Amount is larger than `capacity`  | Return `False`, or raise `BucketOverflow`      | Raise `BucketOverflow`              |

An amount larger than `capacity` can never be admitted. Queue mode
raises rather than parking it, because that arrival would block
everything behind it. Drop mode raises only when `raise_on_overflow`
is set.

Queue mode returns `True` for an amount that is waiting. The caller
has handed the bucket the work. `pending_count()` and `has_pending()`
report what is still waiting. Both leak before they answer, so a
queued amount that now fits is admitted by the read.

### Inspecting the bucket

Every read leaks first, using the same clock as `allow()`.

| Method                  | Returns                                                         |
| ----------------------- | --------------------------------------------------------------- |
| `current_level()`       | Water currently in the bucket                                   |
| `remaining_capacity()`  | `capacity - level`, never below zero                            |
| `pending_count()`       | How many queued amounts are still waiting                       |
| `has_pending()`         | Whether the queue is non-empty                                  |
| `fill_ratio()`          | Fullness from `0.0` to `1.0`                                    |
| `fill_percent()`        | Fullness from `0` to `100`                                      |
| `peek()`                | One snapshot of level, remaining, pending, and fill             |

`peek()` leaks once and builds every field from that moment:

```python
bucket.peek()
# {
#     "level": 1.0,
#     "remaining": 4.0,
#     "pending": 0,
#     "fill_ratio": 0.2,
#     "fill_percent": 20.0,
# }
```

`level`, `remaining`, and `fill_ratio` are rounded for display.
`fill_percent` is rounded to one decimal place. The bucket keeps full
precision for later leaks.

### Shutdown

```python
bucket = LeakyBucket(capacity=5, leak_rate=1, mode="queue", drain_on_shutdown=True)
bucket.allow()
bucket.shutdown()
```

`shutdown()` with `drain_on_shutdown=False` sets the level to zero and
clears the queue. With `drain_on_shutdown=True` the clock advances by
the time needed to admit each queued amount, then by the time needed
to empty the bucket. An advanceable clock is stepped directly. The
system clock sleeps.

### Clock

`SystemTimeProvider` uses `time.monotonic()`. A wall-clock step does
not refill the bucket. A custom provider only needs `now() -> float`.
If that clock moves backwards, elapsed time is ignored until it
catches up, so the level does not grow.

`AdvanceableTimeProvider` is the protocol for a test or demo clock
that also implements `advance(seconds)`. `shutdown()` calls `advance`
when the provider matches that protocol.

### Threads

Public methods share one lock. Several threads may call `allow()` and
the read methods on the same bucket. `shutdown()` keeps that lock
while it drains, so other callers wait until the drain finishes.

### Errors and version

| Name                   | When                                                              |
| ---------------------- | ----------------------------------------------------------------- |
| `LeakyBucketError`     | Base error: bad capacity, leak rate, amount, or conflicting flags |
| `BucketOverflow`       | An arrival does not fit and the call is configured to raise       |
| `InvalidBucketMode`    | `mode` is not `"drop"` or `"queue"`                               |
| `__version__`          | Package version string                                            |
| `get_version()`        | Same string as `__version__`                                      |

`BucketOverflow` and `InvalidBucketMode` are subclasses of
`LeakyBucketError`.

## Demos

Scripts under `demo/` are examples. They are not part of the wheel.
Install the package first (`make python-install-dev`), then run them
from the repository root.

```bash
python demo/demo_live.py --queue --capacity 5 --rate 1 --events 10
python demo/demo_timeline.py
python demo/demo_worker.py --jobs 20 --rate 1 --capacity 5
python demo/demo_copy.py input.txt output.txt --rate 100000
```

| Script             | What it shows                                                                  |
| ------------------ | ------------------------------------------------------------------------------ |
| `demo_live.py`     | Flags on the real clock: mode, capacity, rate, interval, and drain             |
| `demo_timeline.py` | Drop, queue, and drain on a fake clock, printed back to back with no sleeping  |
| `demo_worker.py`   | A fast producer and a worker that waits in drop mode until each job fits       |
| `demo_copy.py`     | A file copy charged in bytes per chunk                                         |

`demo_copy.py` refuses a chunk larger than the rate. One read has to
fit in the bucket. `demo_worker.py` keeps jobs on a normal queue. The
bucket only decides when the worker may take the next job. The main
thread waits until that worker, including `shutdown()`, has finished.

## Check

```bash
make init
make python-check
```

<a href="https://github.com/the-lupaxa-project">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/components/footer-for-child-orgs.svg" alt="The Lupaxa Project Footer" width="100%" />
</a>
