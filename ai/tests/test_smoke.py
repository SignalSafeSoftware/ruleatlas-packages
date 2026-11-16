"""Scaffold smoke test: the package imports and exposes a version."""

from __future__ import annotations

from importlib.metadata import version

import ruleatlas_ai


def test_package_imports_and_has_version() -> None:
    assert ruleatlas_ai.__version__ == version("ruleatlas-ai")
