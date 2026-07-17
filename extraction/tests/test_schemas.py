"""Validation behavior of the extraction candidate/evidence schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from ruleatlas_contracts.enums import CandidateStatus, EvidenceSourceType

from ruleatlas_extraction.schemas import ExtractionCandidate, ExtractionEvidence


def test_candidate_defaults_to_needs_review() -> None:
    candidate = ExtractionCandidate(
        name="Invoice approval",
        business_rule="Invoices over $10,000 require manager approval",
        confidence_score=80.0,
    )
    assert candidate.candidate_status == CandidateStatus.NEEDS_REVIEW
    assert candidate.evidence == []
    assert candidate.is_likely_implementation_detail is False


def test_confidence_score_is_bounded() -> None:
    with pytest.raises(ValidationError):
        ExtractionCandidate(name="x", business_rule="y", confidence_score=150.0)
    with pytest.raises(ValidationError):
        ExtractionCandidate(name="x", business_rule="y", confidence_score=-1.0)


def test_evidence_carries_provenance() -> None:
    evidence = ExtractionEvidence(
        source_type=next(iter(EvidenceSourceType)),
        reference_path="billing/approvals.py",
        snippet="if amount > 10000: require_manager_approval()",
        claim_text="Invoices over $10,000 require manager approval",
        confidence_score=90.0,
        extraction_explanation="threshold comparison on invoice amount",
    )
    assert evidence.reference_path.endswith(".py")
    assert evidence.start_line is None
