"""Library-only package boundary."""

from __future__ import annotations

import pathlib
import runpy

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = REPO_ROOT / "src" / "lupaxa" / "leaky_bucket"


def test_namespace_package_has_no_init() -> None:
    assert not (REPO_ROOT / "src" / "lupaxa" / "__init__.py").is_file()


def test_no_package_cli_or_main_module() -> None:
    assert not (PKG / "cli.py").is_file()
    assert not (PKG / "__main__.py").is_file()


def test_package_is_not_runnable_as_module() -> None:
    with pytest.raises(ImportError):
        runpy.run_module("lupaxa.leaky_bucket", run_name="__main__")


def test_public_all_lists_documented_names() -> None:
    import lupaxa.leaky_bucket as leaky_bucket

    assert set(leaky_bucket.__all__) >= {
        "AdvanceableTimeProvider",
        "BucketOverflow",
        "InvalidBucketMode",
        "LeakyBucket",
        "LeakyBucketError",
        "SystemTimeProvider",
        "TimeProvider",
        "__version__",
        "get_version",
    }


def test_no_repo_root_cli() -> None:
    assert not (REPO_ROOT / "cli.py").is_file()
    assert not (REPO_ROOT / "setup.cfg").is_file()


def test_demos_live_outside_the_package() -> None:
    demo = REPO_ROOT / "demo"
    assert (demo / "demo_live.py").is_file()
    assert (demo / "demo_timeline.py").is_file()
    assert (demo / "demo_worker.py").is_file()
    assert (demo / "demo_copy.py").is_file()
    assert not (demo / "cli.py").is_file()
    assert not (PKG / "demo").exists()
