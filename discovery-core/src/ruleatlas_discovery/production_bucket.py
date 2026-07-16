"""Production vs tests/docs bucket for discovery codebase metrics."""

from __future__ import annotations

from pathlib import Path

from ruleatlas_contracts.enums import SourceFileClassification, SourceType

PRODUCTION_BUCKET_PRODUCTION = "production"
PRODUCTION_BUCKET_TESTS = "tests"
PRODUCTION_BUCKET_DOCS = "docs"
PRODUCTION_BUCKET_CONFIG = "config"
PRODUCTION_BUCKET_GENERATED = "generated_or_vendor"
PRODUCTION_BUCKET_ARTIFACTS = "artifacts"
PRODUCTION_BUCKET_UNKNOWN = "unknown"

_TEST_PATH_MARKERS = ("/tests/", "/test/", "/__tests__/", "/spec/", "/specs/", "/e2e/", "/cypress/")
_DOC_PATH_MARKERS = ("/docs/", "/doc/", "/documentation/")
_CONFIG_PATH_MARKERS = ("/config/", "/configs/", "/settings/")
# Path-segment markers only — avoid bare "coverage" (matches coverage_report.md, docs/coverage.md).
_ARTIFACT_MARKERS = ("/coverage/", "coverage/", "htmlcov", ".log", "artifacts/")

_TEST_CLASSIFICATIONS = {
    SourceFileClassification.TEST_EVIDENCE.value,
    SourceFileClassification.UI_RULE_MIRROR.value,
}
_TEST_SOURCE_TYPES = {SourceType.TESTS.value, SourceType.BDD_SPECS.value}
_DOC_CLASSIFICATIONS = {
    SourceFileClassification.DOCUMENTATION_EVIDENCE.value,
    SourceFileClassification.DESIGN_DOC_EVIDENCE.value,
    SourceFileClassification.TICKET_EVIDENCE.value,
    SourceFileClassification.PRESENTATION_ONLY.value,
}
_DOC_SOURCE_TYPES = {SourceType.DOCS.value, SourceType.DESIGN_DOCS.value, SourceType.TICKETS.value}
_CONFIG_BASENAME_SUFFIXES = (".yaml", ".yml", ".json", ".toml", ".ini", ".env.example")


def _enum_str(value: object | None) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def infer_production_bucket(
    path: str,
    *,
    classification: SourceFileClassification | str,
    source_type: SourceType | str | None = None,
) -> str:
    cls = _enum_str(classification)
    st = _enum_str(source_type)

    if cls == SourceFileClassification.GENERATED_VENDOR.value:
        return PRODUCTION_BUCKET_GENERATED

    normalized = path.replace("\\", "/").lower()
    basename = Path(normalized).name

    if any(marker in normalized for marker in _ARTIFACT_MARKERS):
        return PRODUCTION_BUCKET_ARTIFACTS
    if cls in _TEST_CLASSIFICATIONS or st in _TEST_SOURCE_TYPES:
        return PRODUCTION_BUCKET_TESTS
    if cls in _DOC_CLASSIFICATIONS or st in _DOC_SOURCE_TYPES:
        return PRODUCTION_BUCKET_DOCS
    if any(marker in normalized for marker in _DOC_PATH_MARKERS) or basename.endswith((".md", ".rst")):
        return PRODUCTION_BUCKET_DOCS
    if any(marker in normalized for marker in _TEST_PATH_MARKERS) or basename.startswith(("test_", "spec.")):
        return PRODUCTION_BUCKET_TESTS
    if (
        cls == SourceFileClassification.OPS_ONLY.value
        or any(marker in normalized for marker in _CONFIG_PATH_MARKERS)
        or basename.endswith(_CONFIG_BASENAME_SUFFIXES)
    ):
        return PRODUCTION_BUCKET_CONFIG
    if cls == SourceFileClassification.RULE_BEARING.value:
        return PRODUCTION_BUCKET_PRODUCTION
    if cls == SourceFileClassification.UNKNOWN_NEEDS_REVIEW.value:
        return PRODUCTION_BUCKET_UNKNOWN
    return PRODUCTION_BUCKET_PRODUCTION
