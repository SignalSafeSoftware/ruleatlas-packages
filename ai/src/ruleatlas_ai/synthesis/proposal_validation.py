"""Deterministic rule proposal validation against scoped evidence."""

from __future__ import annotations

from dataclasses import dataclass, field

from ruleatlas_persistence.models import SourceClaim
from ruleatlas_persistence.repositories import RepositoryFactory
from sqlalchemy.orm import Session

from ruleatlas_ai.synthesis.schema import AiRuleProposal, validate_proposal_payload


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    proposal: AiRuleProposal | None = None


def validate_rule_proposal(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
    payload: dict,
) -> ValidationResult:
    proposal, schema_errors = validate_proposal_payload(payload)
    if proposal is None:
        return ValidationResult(valid=False, errors=schema_errors)

    errors: list[str] = []
    warnings: list[str] = []
    repositories = RepositoryFactory(session)

    def _claim_in_scope(claim_id: str) -> SourceClaim | None:
        return repositories.source_claims_structured().get_for_analysis(
            claim_id,
            project_id,
            analysis_version_id,
        )

    for claim_id in proposal.supporting_claim_ids + proposal.contradicting_claim_ids:
        row = _claim_in_scope(claim_id)
        if row is None:
            errors.append(f"Invented or cross-analysis claim citation: {claim_id}")

    for evidence_id in proposal.supporting_evidence_ids:
        ev = repositories.source_claim_evidence().get_by_id(evidence_id)
        if ev is None:
            errors.append(f"Invented evidence citation: {evidence_id}")
            continue
        parent = _claim_in_scope(ev.source_claim_id)
        if parent is None:
            errors.append(f"Evidence {evidence_id} outside analysis scope")
        if ev.start_line is not None and ev.end_line is not None and ev.end_line < ev.start_line:
            errors.append(f"Invalid line range on evidence {evidence_id}")

    roles = set()
    for claim_id in proposal.supporting_claim_ids:
        row = _claim_in_scope(claim_id)
        if row:
            roles.add(row.claim_role)
    if "implementation" not in roles:
        warnings.append("Missing implementation-role supporting claim")
    if "verification" not in roles and "product_intent" not in roles:
        warnings.append("Missing verification or product-intent supporting claim")

    # Never approve/persist here
    return ValidationResult(
        valid=not errors,
        errors=errors,
        warnings=warnings,
        proposal=proposal if not errors else None,
    )
