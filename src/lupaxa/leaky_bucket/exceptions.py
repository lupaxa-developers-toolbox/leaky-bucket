"""Errors raised by ``lupaxa.leaky_bucket``."""

from __future__ import annotations


class LeakyBucketError(Exception):
    """Base exception for leaky bucket errors."""


class BucketOverflow(LeakyBucketError):
    """Raised when an arrival does not fit.

    Drop mode raises only when ``raise_on_overflow`` is set. Queue mode
    raises when the amount is larger than ``capacity``, because that
    arrival can never be admitted.
    """


class InvalidBucketMode(LeakyBucketError):
    """Raised when ``mode`` is not ``drop`` or ``queue``."""
