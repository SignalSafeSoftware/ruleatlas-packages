#!/usr/bin/env python3
"""Tests for release-tag path validation."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "verify_release_tag",
    Path(__file__).with_name("verify-release-tag.py"),
)
assert _spec is not None
assert _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
_validated = _mod.validated_github_output_path


class ValidatedGithubOutputPathTests(unittest.TestCase):
    def test_accepts_path_under_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            target = root / "github-output"
            target.write_text("", encoding="utf-8")
            self.assertEqual(_validated(target, cwd=root, github_output=""), target)

    def test_rejects_path_outside_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            outside = root.parent / "escape"
            with self.assertRaises(SystemExit):
                _validated(outside, cwd=root, github_output="")

    def test_rejects_relative_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            with self.assertRaises(SystemExit):
                _validated(Path("../etc/passwd"), cwd=root, github_output="")

    def test_env_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            allowed = root / "allowed"
            other = root / "other"
            allowed.write_text("", encoding="utf-8")
            other.write_text("", encoding="utf-8")
            with self.assertRaises(SystemExit):
                _validated(other, cwd=root, github_output=str(allowed))

    def test_env_match_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            allowed = root / "allowed"
            allowed.write_text("", encoding="utf-8")
            self.assertEqual(_validated(allowed, cwd=root, github_output=str(allowed)), allowed)


if __name__ == "__main__":
    unittest.main()
