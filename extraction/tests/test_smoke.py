"""Scaffold smoke test: the package imports and exposes a version."""

from __future__ import annotations

import ruleatlas_extraction


def test_package_imports_and_has_version() -> None:
    assert ruleatlas_extraction.__version__ == "0.1.0"
