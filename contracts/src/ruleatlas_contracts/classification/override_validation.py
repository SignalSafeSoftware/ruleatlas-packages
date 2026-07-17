"""Pure validation/normalization for user-supplied classification overrides.

Kernel-grade classification vocabulary (no ORM, no I/O): glob-pattern normalization
and enum validation shared by the scanning service and its persistence adapter.
"""

from __future__ import annotations

from ruleatlas_contracts.enums import FileKind, SourceFileClassification

__all__ = [
    "ClassificationOverrideError",
    "normalize_pattern",
    "suggest_pattern_for_path",
    "validate_classification",
    "validate_file_kind",
]


class ClassificationOverrideError(Exception):
    """Raised when an override pattern/classification/file-kind is invalid."""


def normalize_pattern(pattern: str) -> str:
    normalized = pattern.strip().replace("\\", "/").lstrip("/")
    if not normalized:
        raise ClassificationOverrideError("Pattern cannot be empty")
    if normalized.startswith("..") or "/../" in normalized:
        raise ClassificationOverrideError("Pattern cannot contain parent directory segments")
    if normalized in {"**", "**/*", "*"}:
        raise ClassificationOverrideError("Pattern is too broad; use a directory prefix like docs/**")
    return normalized


def validate_classification(value: str) -> SourceFileClassification:
    try:
        return SourceFileClassification(value)
    except ValueError as exc:
        raise ClassificationOverrideError(f"Invalid classification: {value}") from exc


def validate_file_kind(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    try:
        return FileKind(normalized).value
    except ValueError as exc:
        raise ClassificationOverrideError(f"Invalid file kind: {value}") from exc


def suggest_pattern_for_path(path: str) -> str:
    normalized = path.strip().replace("\\", "/").lstrip("/")
    if not normalized:
        raise ClassificationOverrideError("Path cannot be empty")
    root = normalized.split("/", maxsplit=1)[0]
    return f"{root}/**"
