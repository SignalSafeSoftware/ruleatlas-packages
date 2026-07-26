"""Pure confidence inputs and scoring for cited AST observations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

AST_ONLY_IMPLEMENTATION_CAP = 0.7
AST_CORROBORATION_BOOST_CAP = 0.15


class AstObservationKind(StrEnum):
    CONDITION = "condition"
    ASSIGNMENT = "assignment"
    CALL = "call"
    CONTROL_FLOW = "control_flow"
    DEFINITION = "definition"
    EXCEPTION = "exception"


class AstObservationResolution(StrEnum):
    EXTRACTED = "extracted"
    RESOLVED = "resolved"
    INFERRED = "inferred"
    AMBIGUOUS = "ambiguous"


_RESOLUTION_FACTORS = {
    AstObservationResolution.EXTRACTED: 1.0,
    AstObservationResolution.RESOLVED: 0.9,
    AstObservationResolution.INFERRED: 0.65,
    AstObservationResolution.AMBIGUOUS: 0.4,
}


@dataclass(frozen=True)
class AstEvidenceView:
    citation_id: str
    source_path: str
    observation_kind: AstObservationKind
    resolution: AstObservationResolution
    confidence_score: float
    parse_quality: float = 1.0
    has_parser_error: bool = False

    def __post_init__(self) -> None:
        if not self.citation_id.strip():
            raise ValueError("citation_id must not be blank")
        if not self.source_path.strip():
            raise ValueError("source_path must not be blank")
        for field_name, value in {
            "confidence_score": self.confidence_score,
            "parse_quality": self.parse_quality,
        }.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0.0 and 1.0")


@dataclass(frozen=True)
class AstEvidenceScore:
    implementation_confidence: float
    explanations: tuple[str, ...]


def score_ast_evidence(evidence: tuple[AstEvidenceView, ...]) -> AstEvidenceScore:
    """Score structural observations as implementation evidence only."""

    if not evidence:
        return AstEvidenceScore(0.0, ())
    scores: list[float] = []
    explanations: list[str] = []
    for item in evidence:
        score = item.confidence_score * item.parse_quality * _RESOLUTION_FACTORS[item.resolution]
        if item.has_parser_error:
            score *= 0.5
        scores.append(score)
        qualifications = [item.resolution.value]
        if item.has_parser_error:
            qualifications.append("parser-error-dampened")
        explanations.append(
            "AST "
            f"{item.observation_kind.value} observation from {item.source_path} "
            f"({', '.join(qualifications)}; implementation only)"
        )
    average = sum(scores) / len(scores)
    return AstEvidenceScore(
        implementation_confidence=min(
            average * AST_ONLY_IMPLEMENTATION_CAP,
            AST_ONLY_IMPLEMENTATION_CAP,
        ),
        explanations=tuple(explanations),
    )


__all__ = [
    "AST_CORROBORATION_BOOST_CAP",
    "AST_ONLY_IMPLEMENTATION_CAP",
    "AstEvidenceScore",
    "AstEvidenceView",
    "AstObservationKind",
    "AstObservationResolution",
    "score_ast_evidence",
]
