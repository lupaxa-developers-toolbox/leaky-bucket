"""Public export surface."""

from __future__ import annotations

import lupaxa.leaky_bucket as leaky_bucket


def test_public_names_are_exported() -> None:
    for name in (
        "AdvanceableTimeProvider",
        "BucketOverflow",
        "InvalidBucketMode",
        "LeakyBucket",
        "LeakyBucketError",
        "SystemTimeProvider",
        "TimeProvider",
        "__version__",
        "get_version",
    ):
        assert hasattr(leaky_bucket, name)
        assert name in leaky_bucket.__all__
