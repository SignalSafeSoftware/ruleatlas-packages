"""GP-5: static-analysis is a first-class, weighted, corroborating evidence source (never confirming)."""

from __future__ import annotations

import math

from ruleatlas_contracts.enums import EvidenceSourceType, RuleStatus

from ruleatlas_claims.confidence_scorer import (
    DEFAULT_SOURCE_WEIGHTS,
    STATIC_ANALYSIS_SOURCE_TYPES,
    EvidenceView,
    RuleConfidenceInputs,
    score_rule_confidence,
)


def _inputs(*evidence: EvidenceView) -> RuleConfidenceInputs:
    return RuleConfidenceInputs(status=RuleStatus.NEEDS_REVIEW, has_conflicts=False, evidence=evidence)


def _ev(source_type: EvidenceSourceType, score: float = 0.9) -> EvidenceView:
    return EvidenceView(source_type=source_type, confidence_score=score, reference_path="src/a.py")


def test_static_analysis_is_weighted_below_code_and_tests() -> None:
    w = DEFAULT_SOURCE_WEIGHTS
    assert math.isclose(w[EvidenceSourceType.STATIC_ANALYSIS.value], 0.6)
    assert w[EvidenceSourceType.STATIC_ANALYSIS.value] < w[EvidenceSourceType.BACKEND_CODE.value]
    assert w[EvidenceSourceType.STATIC_ANALYSIS.value] < w[EvidenceSourceType.UNIT_TEST.value]
    assert EvidenceSourceType.STATIC_ANALYSIS in STATIC_ANALYSIS_SOURCE_TYPES


def test_static_analysis_contributes_to_implementation_confidence() -> None:
    # A static-analysis-only rule gains *some* implementation confidence (it is counted, not ignored)...
    only_static = score_rule_confidence(_inputs(_ev(EvidenceSourceType.STATIC_ANALYSIS)))
    assert only_static.implementation_confidence > 0.0
    # ...but strictly less than the same rule backed by real backend code.
    only_code = score_rule_confidence(_inputs(_ev(EvidenceSourceType.BACKEND_CODE)))
    assert only_static.implementation_confidence < only_code.implementation_confidence


def test_static_analysis_raises_overall_confidence_as_corroboration() -> None:
    base = score_rule_confidence(_inputs(_ev(EvidenceSourceType.BACKEND_CODE, 0.5)))
    corroborated = score_rule_confidence(
        _inputs(_ev(EvidenceSourceType.BACKEND_CODE, 0.5), _ev(EvidenceSourceType.STATIC_ANALYSIS, 0.5))
    )
    assert corroborated.overall_confidence >= base.overall_confidence


def test_static_analysis_never_alone_confirms() -> None:
    # Corroboration must not, by itself, push a candidate to a "confirmed"-level score.
    only_static = score_rule_confidence(_inputs(_ev(EvidenceSourceType.STATIC_ANALYSIS, 1.0)))
    assert only_static.overall_confidence < 0.6
