from __future__ import annotations

from pydantic import BaseModel, Field
from ruleatlas_contracts.enums import CandidateStatus, EvidenceSourceType


class ExtractionEvidence(BaseModel):
    source_type: EvidenceSourceType
    reference_path: str
    start_line: int | None = None
    end_line: int | None = None
    snippet: str
    claim_text: str
    confidence_score: float = Field(ge=0.0, le=100.0)
    extraction_explanation: str


class ExtractionCandidate(BaseModel):
    domain: str | None = None
    name: str
    business_rule: str
    why_this_rule_exists: str | None = None
    conditions_if: str | None = None
    actions_then: str | None = None
    exceptions_constraints: str | None = None
    ui_surface: str | None = None
    confidence_score: float = Field(ge=0.0, le=100.0)
    candidate_status: CandidateStatus = CandidateStatus.NEEDS_REVIEW
    evidence: list[ExtractionEvidence] = Field(default_factory=list)
    rejection_reason: str | None = None
    is_likely_implementation_detail: bool = False
