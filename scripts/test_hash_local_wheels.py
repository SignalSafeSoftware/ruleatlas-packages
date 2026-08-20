#!/usr/bin/env python3
"""Tests for hashed local-wheel requirements."""

from __future__ import annotations

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "hash_local_wheels",
    Path(__file__).with_name("hash_local_wheels.py"),
)
assert _spec is not None
assert _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
_write = _mod.write_hashed_requirements


class HashLocalWheelsTests(unittest.TestCase):
    def test_writes_sha256_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wheel = root / "example-1.0-py3-none-any.whl"
            payload = b"wheel-bytes"
            wheel.write_bytes(payload)
            output = root / "wheels.txt"
            _write(root, output)
            digest = hashlib.sha256(payload).hexdigest()
            text = output.read_text(encoding="utf-8")
            self.assertIn(wheel.resolve().as_uri(), text)
            self.assertIn(f"--hash=sha256:{digest}", text)


if __name__ == "__main__":
    unittest.main()
