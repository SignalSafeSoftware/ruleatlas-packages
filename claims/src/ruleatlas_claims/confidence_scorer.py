"""Model-free confidence scorer (ports/DTOs proof-of-pattern, breakup Phase 3).

The scoring *algorithm* + its data contracts live here and depend only on the kernel (enums + the
classification helper) — no SQLAlchemy models, no Session, no service factory. The app-side
``ConfidenceScoringServiceRepository`` is the adapter: it loads ORM rows, maps them to these DTOs, calls
``score_rule_confidence``, and persists the result. This is the shape every context would follow to become
physically extractable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ruleatlas_contracts.classification.scaffold_filter import is_scaffold_evidence_text
from ruleatlas_contracts.enums import EvidenceSourceType, RuleStatus

DEFAULT_SOURCE_WEIGHTS: dict[str, float] = {
    EvidenceSourceType.BACKEND_CODE.value: 1.0,
    EvidenceSourceType.FRONTEND_CODE.value: 0.95,
    EvidenceSourceType.BDD_SPEC.value: 0.9,
    EvidenceSourceType.UNIT_TEST.value: 0.85,
    EvidenceSourceType.INTEGRATION_TEST.value: 0.85,
    EvidenceSourceType.API_TEST.value: 0.8,
    EvidenceSourceType.API_CONTRACT.value: 0.75,
    EvidenceSourceType.README_DOC.value: 0.7,
    EvidenceSourceType.DESIGN_DOC.value: 0.7,
    # Static-analysis (Semgrep/tree-sitter) findings corroborate the implementation but are lower
    # fidelity than reading the code and must stay below code/test weights (trust model: observations
    # support, they do not confirm product intent). See STATIC_ANALYSIS_SOURCE_TYPES below.
    EvidenceSourceType.STATIC_ANALYSIS.value: 0.6,
    EvidenceSourceType.COVERAGE_REPORT.value: 0.5,
    EvidenceSourceType.RUNTIME_LOG.value: 0.45,
    EvidenceSourceType.CODE_COMMENT.value: 0.35,
    EvidenceSourceType.AI_EXTRACTION.value: 0.35,
}

AI_SOURCE_TYPES = {EvidenceSourceType.AI_EXTRACTION}
IMPLEMENTATION_SOURCE_TYPES = {
    EvidenceSourceType.BACKEND_CODE,
    EvidenceSourceType.FRONTEND_CODE,
    EvidenceSourceType.API_CONTRACT,
}
TEST_SOURCE_TYPES = {
    EvidenceSourceType.UNIT_TEST,
    EvidenceSourceType.INTEGRATION_TEST,
    EvidenceSourceType.BDD_SPEC,
    EvidenceSourceType.API_TEST,
}
DOC_SOURCE_TYPES = {
    EvidenceSourceType.README_DOC,
    EvidenceSourceType.DESIGN_DOC,
    EvidenceSourceType.TICKET,
}
COMMENT_SOURCE_TYPES = {EvidenceSourceType.CODE_COMMENT}
# Structural static-analysis findings (Semgrep/tree-sitter). Corroborating implementation evidence,
# scored below real code so it can raise a candidate's confidence without ever confirming it alone.
STATIC_ANALYSIS_SOURCE_TYPES = {EvidenceSourceType.STATIC_ANALYSIS}
# Extra dampening applied on top of the source weight so static analysis never rivals reading the code.
STATIC_ANALYSIS_CORROBORATION_FACTOR = 0.8
AI_CONFIDENCE_CAP = 0.45

__all__ = [
    "AI_CONFIDENCE_CAP",
    "AI_SOURCE_TYPES",
    "COMMENT_SOURCE_TYPES",
    "DEFAULT_SOURCE_WEIGHTS",
    "DOC_SOURCE_TYPES",
    "IMPLEMENTATION_SOURCE_TYPES",
    "STATIC_ANALYSIS_CORROBORATION_FACTOR",
    "STATIC_ANALYSIS_SOURCE_TYPES",
    "TEST_SOURCE_TYPES",
    "ConfidenceBreakdown",
    "EvidenceView",
    "RuleConfidenceInputs",
    "score_rule_confidence",
]


@dataclass(frozen=True)
class EvidenceView:
    """Provider-neutral view of one evidence row (what the scorer reads)."""

    source_type: EvidenceSourceType
    confidence_score: float
    reference_path: str
    claim_text: str = ""
    snippet: str | None = None


@dataclass(frozen=True)
class RuleConfidenceInputs:
    """Everything the scorer needs for one rule — assembled by the adapter from ORM rows."""

    status: RuleStatus
    has_conflicts: bool
    evidence: tuple[EvidenceView, ...] = ()
    coverage_scores: tuple[float, ...] = ()
    runtime_high_flags: tuple[bool, ...] = ()
    source_weight_overrides: dict[str, float] = field(default_factory=dict)


@dataclass
class ConfidenceBreakdown:
    implementation_confidence: float = 0.0
    test_confidence: float = 0.0
    documentation_confidence: float = 0.0
    runtime_confidence: float = 0.0
    coverage_confidence: float = 0.0
    product_intent_confidence: float = 0.0
    overall_confidence: float = 0.0
    explanations: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, float | list[str]]:
        return {
            "implementation_confidence": self.implementation_confidence,
            "test_confidence": self.test_confidence,
            "documentation_confidence": self.documentation_confidence,
            "runtime_confidence": self.runtime_confidence,
            "coverage_confidence": self.coverage_confidence,
            "product_intent_confidence": self.product_intent_confidence,
            "overall_confidence": self.overall_confidence,
            "explanations": self.explanations,
        }


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _avg(scores: list[float]) -> float:
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def _weight_for(source_type: EvidenceSourceType, overrides: dict[str, float]) -> float:
    if source_type.value in overrides:
        return float(overrides[source_type.value])
    return DEFAULT_SOURCE_WEIGHTS.get(source_type.value, 1.0)


def _score_evidence_row(
    ev: EvidenceView,
    breakdown: ConfidenceBreakdown,
    overrides: dict[str, float],
    *,
    impl_scores: list[float],
    test_scores: list[float],
    doc_scores: list[float],
    ai_scores: list[float],
    static_scores: list[float],
) -> None:
    weight = _weight_for(ev.source_type, overrides)
    score = _clamp(ev.confidence_score if ev.confidence_score <= 1 else ev.confidence_score / 100)
    score = _clamp(score * weight)
    source = ev.source_type
    if source in IMPLEMENTATION_SOURCE_TYPES:
        impl_scores.append(score)
        breakdown.explanations.append(f"Implementation evidence from {ev.reference_path}")
        return
    if source in STATIC_ANALYSIS_SOURCE_TYPES:
        # Kept separate from the implementation average so corroboration can only *raise* confidence
        # (added as a capped boost below), never dilute a well-evidenced rule.
        static_scores.append(score)
        breakdown.explanations.append(
            f"Static-analysis corroboration from {ev.reference_path} (supports, not confirmation)"
        )
        return
    if source in TEST_SOURCE_TYPES:
        if is_scaffold_evidence_text(ev.claim_text, ev.snippet):
            breakdown.explanations.append(f"Skipped scaffold test line from {ev.reference_path}")
            return
        weight = 1.0 if source == EvidenceSourceType.BDD_SPEC else 0.75
        test_scores.append(score * weight)
        breakdown.explanations.append(f"Test evidence ({source.value}) from {ev.reference_path}")
        return
    if source in COMMENT_SOURCE_TYPES:
        doc_scores.append(score * 0.4)
        breakdown.explanations.append(
            f"Weak code-comment intent hint from {ev.reference_path} (cannot confirm alone)"
        )
        return
    if source in DOC_SOURCE_TYPES:
        doc_scores.append(score * 0.85)
        breakdown.explanations.append(f"Documentation/product intent from {ev.reference_path}")
        return
    if source in AI_SOURCE_TYPES:
        ai_scores.append(min(score, AI_CONFIDENCE_CAP))
        breakdown.explanations.append("AI candidate evidence (capped; not confirmation)")


def _apply_static_analysis(impl_confidence: float, static_scores: list[float], *, has_impl: bool) -> float:
    """Fold static-analysis corroboration into implementation confidence.

    When real implementation evidence exists, static analysis is a **capped additive boost** (it can
    only raise, never dilute). When a candidate has *only* static-analysis evidence, it is counted but
    dampened so it can never confirm a rule on its own (trust model: observations support, not confirm).
    """
    if not static_scores:
        return impl_confidence
    static_avg = _avg(static_scores)
    if has_impl:
        return impl_confidence + min(static_avg * 0.25, 0.15)
    return static_avg * STATIC_ANALYSIS_CORROBORATION_FACTOR


def _apply_coverage_runtime(
    breakdown: ConfidenceBreakdown,
    coverage_scores: tuple[float, ...],
    runtime_high_flags: tuple[bool, ...],
) -> None:
    if coverage_scores:
        breakdown.coverage_confidence = _clamp(
            _avg([s if s <= 1 else s / 100 for s in coverage_scores])
        )
        breakdown.explanations.append("Coverage supports execution evidence only")
        breakdown.test_confidence = _clamp(max(breakdown.test_confidence, breakdown.coverage_confidence * 0.6))
    if runtime_high_flags:
        breakdown.runtime_confidence = _clamp(_avg([0.7 if high else 0.45 for high in runtime_high_flags]))
        breakdown.explanations.append("Runtime logs show observed behavior only")


def score_rule_confidence(inputs: RuleConfidenceInputs) -> ConfidenceBreakdown:
    """Pure scoring over provider-neutral inputs. No DB/session/ORM."""
    breakdown = ConfidenceBreakdown()
    impl_scores: list[float] = []
    test_scores: list[float] = []
    doc_scores: list[float] = []
    ai_scores: list[float] = []
    static_scores: list[float] = []

    for ev in inputs.evidence:
        _score_evidence_row(
            ev,
            breakdown,
            inputs.source_weight_overrides,
            impl_scores=impl_scores,
            test_scores=test_scores,
            doc_scores=doc_scores,
            ai_scores=ai_scores,
            static_scores=static_scores,
        )

    breakdown.implementation_confidence = _clamp(
        _apply_static_analysis(_avg(impl_scores), static_scores, has_impl=bool(impl_scores))
    )
    breakdown.test_confidence = _clamp(_avg(test_scores))
    breakdown.documentation_confidence = _clamp(_avg(doc_scores))
    breakdown.product_intent_confidence = _clamp(_avg(doc_scores + [s * 0.5 for s in ai_scores]))
    _apply_coverage_runtime(breakdown, inputs.coverage_scores, inputs.runtime_high_flags)

    components = [
        breakdown.implementation_confidence * 0.35,
        breakdown.test_confidence * 0.25,
        breakdown.documentation_confidence * 0.15,
        breakdown.runtime_confidence * 0.1,
        breakdown.coverage_confidence * 0.1,
    ]
    breakdown.overall_confidence = _clamp(sum(components))
    if inputs.has_conflicts:
        breakdown.overall_confidence = _clamp(breakdown.overall_confidence * 0.55)
        breakdown.explanations.append("Open conflicts reduce overall confidence")
    if inputs.status in {RuleStatus.REJECTED, RuleStatus.DEPRECATED}:
        breakdown.overall_confidence = _clamp(breakdown.overall_confidence * 0.25)
    elif inputs.status == RuleStatus.APPROVED:
        breakdown.overall_confidence = _clamp(max(breakdown.overall_confidence, 0.6))
    return breakdown
