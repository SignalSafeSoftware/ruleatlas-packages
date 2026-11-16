"""Scaffold smoke test: the package imports and exposes a version."""

from __future__ import annotations

from importlib.metadata import version

import ruleatlas_contracts


def test_package_imports_and_has_version() -> None:
    assert ruleatlas_contracts.__version__ == version("ruleatlas-contracts")
