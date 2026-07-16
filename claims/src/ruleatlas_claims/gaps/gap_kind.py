from __future__ import annotations

from enum import StrEnum

from ruleatlas_contracts.enum_utils import enum_value


class GapKind(StrEnum):
    IMPLEMENTATION = "implementation"
    COVERAGE = "coverage"
    EVIDENCE = "evidence"


COVERAGE_GAP_TITLE_PREFIX = "Coverage gap (test execution):"
IMPLEMENTATION_GAP_TITLE_PREFIX = "Implementation gap:"


def classify_gap_kind(title: str) -> str:
    lowered = title.lower()
    if lowered.startswith("coverage gap") or "test execution" in lowered:
        return enum_value(GapKind.COVERAGE)
    if lowered.startswith("evidence gap"):
        return enum_value(GapKind.EVIDENCE)
    return enum_value(GapKind.IMPLEMENTATION)


def implementation_gap_title(claim_text: str, *, max_len: int = 200) -> str:
    claim = " ".join(claim_text.split())
    if len(claim) > max_len:
        claim = claim[: max_len - 1].rstrip(" ,;:-") + "…"
    return f"{IMPLEMENTATION_GAP_TITLE_PREFIX} {claim}"


def coverage_gap_title(path: str, line_number: int) -> str:
    return f"{COVERAGE_GAP_TITLE_PREFIX} {path}:{line_number}"
