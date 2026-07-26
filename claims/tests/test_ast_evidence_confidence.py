"""Confidence tests for AST evidence and the human approval boundary."""

from __future__ import annotations

import pytest
from ruleatlas_contracts.enums import EvidenceSourceType, RuleStatus

from ruleatlas_claims.ast_evidence import (
    AST_ONLY_IMPLEMENTATION_CAP,
    AstEvidenceView,
    AstObservationKind,
    AstObservationResolution,
    score_ast_evidence,
)
from ruleatlas_claims.confidence_scorer import (
    EvidenceView,
    RuleConfidenceInputs,
    score_rule_confidence,
)


def _ast(
    *,
    resolution: AstObservationResolution = AstObservationResolution.EXTRACTED,
    confidence: float = 1.0,
    parse_quality: float = 1.0,
    has_parser_error: bool = False,
) -> AstEvidenceView:
    return AstEvidenceView(
        citation_id="ast:one",
        source_path="src/approval.py",
        observation_kind=AstObservationKind.CONDITION,
        resolution=resolution,
        confidence_score=confidence,
        parse_quality=parse_quality,
        has_parser_error=has_parser_error,
    )


def _inputs(
    *,
    ast_evidence: tuple[AstEvidenceView, ...] = (),
    evidence: tuple[EvidenceView, ...] = (),
    status: RuleStatus = RuleStatus.NEEDS_REVIEW,
    human_approval_recorded: bool = False,
) -> RuleConfidenceInputs:
    return RuleConfidenceInputs(
        status=status,
        has_conflicts=False,
        evidence=evidence,
        ast_evidence=ast_evidence,
        human_approval_recorded=human_approval_recorded,
    )


def test_ast_only_evidence_is_capped_as_implementation_observation() -> None:
    result = score_rule_confidence(_inputs(ast_evidence=(_ast(),)))

    assert result.ast_confidence == AST_ONLY_IMPLEMENTATION_CAP
    assert result.implementation_confidence == AST_ONLY_IMPLEMENTATION_CAP
    assert result.overall_confidence < 0.6
    assert result.product_intent_confidence == 0.0
    assert result.approval_authority == "human_review_required"
    assert any("cannot establish product intent or approval" in explanation for explanation in result.explanations)


def test_resolved_inferred_and_ambiguous_observations_are_dampened() -> None:
    extracted = score_ast_evidence((_ast(),)).implementation_confidence
    resolved = score_ast_evidence((_ast(resolution=AstObservationResolution.RESOLVED),)).implementation_confidence
    inferred = score_ast_evidence((_ast(resolution=AstObservationResolution.INFERRED),)).implementation_confidence
    ambiguous = score_ast_evidence((_ast(resolution=AstObservationResolution.AMBIGUOUS),)).implementation_confidence

    assert extracted > resolved > inferred > ambiguous


def test_parse_quality_and_parser_errors_reduce_ast_confidence() -> None:
    clean = score_ast_evidence((_ast(),)).implementation_confidence
    partial = score_ast_evidence((_ast(parse_quality=0.5),)).implementation_confidence
    error = score_ast_evidence((_ast(has_parser_error=True),)).implementation_confidence

    assert partial < clean
    assert error < clean


def test_ast_corroborates_code_without_replacing_it() -> None:
    code = EvidenceView(
        source_type=EvidenceSourceType.BACKEND_CODE,
        confidence_score=0.6,
        reference_path="src/approval.py",
    )
    base = score_rule_confidence(_inputs(evidence=(code,)))
    corroborated = score_rule_confidence(_inputs(evidence=(code,), ast_evidence=(_ast(),)))

    assert corroborated.implementation_confidence > base.implementation_confidence
    assert corroborated.implementation_confidence <= base.implementation_confidence + 0.15


def test_ast_evidence_never_raises_product_intent_confidence() -> None:
    without_ast = score_rule_confidence(_inputs())
    with_ast = score_rule_confidence(_inputs(ast_evidence=(_ast(),)))

    assert with_ast.product_intent_confidence == without_ast.product_intent_confidence == 0.0


def test_approved_status_does_not_substitute_for_recorded_human_approval() -> None:
    unverified_status = score_rule_confidence(_inputs(status=RuleStatus.APPROVED))
    human_approved = score_rule_confidence(
        _inputs(
            status=RuleStatus.APPROVED,
            human_approval_recorded=True,
        )
    )

    assert unverified_status.overall_confidence == 0.0
    assert unverified_status.approval_authority == "human_review_required"
    assert human_approved.overall_confidence >= 0.6
    assert human_approved.approval_authority == "human_approved"


def test_human_approval_record_cannot_conflict_with_status() -> None:
    with pytest.raises(ValueError, match="requires status=approved"):
        _inputs(
            status=RuleStatus.NEEDS_REVIEW,
            human_approval_recorded=True,
        )


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("confidence_score", -0.1),
        ("confidence_score", 1.1),
        ("parse_quality", -0.1),
        ("parse_quality", 1.1),
    ],
)
def test_ast_evidence_scores_are_normalized(
    field_name: str,
    value: float,
) -> None:
    values = {
        "citation_id": "ast:one",
        "source_path": "src/approval.py",
        "observation_kind": AstObservationKind.CONDITION,
        "resolution": AstObservationResolution.EXTRACTED,
        "confidence_score": 1.0,
        "parse_quality": 1.0,
    }
    values[field_name] = value

    with pytest.raises(ValueError, match="must be between"):
        AstEvidenceView(**values)  # type: ignore[arg-type]
