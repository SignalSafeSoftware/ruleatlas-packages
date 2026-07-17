"""Behavioral tests for the kernel's public API (authorization + classification validation)."""

from __future__ import annotations

import pytest

from ruleatlas_contracts.authorization import permission_satisfied, role_satisfies
from ruleatlas_contracts.classification.override_validation import (
    ClassificationOverrideError,
    normalize_pattern,
    suggest_pattern_for_path,
    validate_classification,
    validate_file_kind,
)
from ruleatlas_contracts.enums import Permission, ProjectRole, SourceFileClassification


def test_role_satisfies_respects_rank() -> None:
    assert role_satisfies(ProjectRole.ADMIN, ProjectRole.VIEWER)
    assert role_satisfies(ProjectRole.EDITOR, ProjectRole.EDITOR)
    assert not role_satisfies(ProjectRole.VIEWER, ProjectRole.ADMIN)


def test_permission_satisfied() -> None:
    assert permission_satisfied(ProjectRole.ADMIN, Permission.ADMIN)
    assert permission_satisfied(ProjectRole.VIEWER, Permission.VIEW)
    assert permission_satisfied(ProjectRole.EDITOR, Permission.EDIT)
    assert not permission_satisfied(ProjectRole.VIEWER, Permission.ADMIN)
    assert not permission_satisfied(ProjectRole.VIEWER, Permission.EDIT)


def test_normalize_pattern_accepts_scoped_globs() -> None:
    assert normalize_pattern("docs/**") == "docs/**"
    assert normalize_pattern("  /docs/**  ") == "docs/**"
    assert normalize_pattern("src\\app\\**") == "src/app/**"


@pytest.mark.parametrize("bad", ["", "   ", "*", "**", "**/*", "../secrets", "a/../b"])
def test_normalize_pattern_rejects_empty_broad_or_traversal(bad: str) -> None:
    with pytest.raises(ClassificationOverrideError):
        normalize_pattern(bad)


def test_validate_classification_roundtrip_and_error() -> None:
    member = next(iter(SourceFileClassification))
    assert validate_classification(member.value) == member
    with pytest.raises(ClassificationOverrideError):
        validate_classification("definitely-not-a-classification")


def test_suggest_pattern_for_path() -> None:
    assert suggest_pattern_for_path("src/foo/bar.py") == "src/**"
    with pytest.raises(ClassificationOverrideError):
        suggest_pattern_for_path("   ")


def test_validate_file_kind_blank_is_none() -> None:
    assert validate_file_kind(None) is None
    assert validate_file_kind("   ") is None
