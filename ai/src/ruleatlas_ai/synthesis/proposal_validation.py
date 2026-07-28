"""Deterministic rule proposal validation against scoped evidence."""

from __future__ import annotations

import re
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


_GROUNDING_STOP_WORDS = {
    "about",
    "after",
    "against",
    "also",
    "before",
    "being",
    "cannot",
    "could",
    "documented",
    "does",
    "except",
    "from",
    "have",
    "into",
    "must",
    "only",
    "other",
    "should",
    "system",
    "that",
    "their",
    "then",
    "there",
    "these",
    "this",
    "through",
    "under",
    "when",
    "where",
    "which",
    "with",
    "without",
    "would",
}
_GROUNDING_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _term_variants(term: str) -> set[str]:
    """Return deliberately small morphology variants for grounding comparisons."""
    variants = {term}
    if len(term) > 4 and term.endswith("ies"):
        variants.add(f"{term[:-3]}y")
    if len(term) > 4 and term.endswith("es"):
        variants.update({term[:-2], term[:-1]})
    elif len(term) > 3 and term.endswith("s"):
        variants.add(term[:-1])
    if len(term) > 5 and term.endswith("ied"):
        variants.add(f"{term[:-3]}y")
    elif len(term) > 4 and term.endswith("ed"):
        variants.update({term[:-2], term[:-1]})
    if len(term) > 5 and term.endswith("ing"):
        variants.update({term[:-3], f"{term[:-3]}e"})
    return {variant for variant in variants if len(variant) >= 3}


def _grounding_tokens(text: str | None) -> set[str]:
    if not text:
        return set()
    return {
        token
        for token in _GROUNDING_TOKEN_RE.findall(text.lower())
        if (len(token) >= 4 or token.isdigit()) and token not in _GROUNDING_STOP_WORDS
    }


def unsupported_grounding_terms(canonical_wording: str, source_texts: list[str]) -> list[str]:
    """Return material proposal terms that do not occur in cited source content.

    This is intentionally conservative: it tolerates common connective language and
    simple morphology, while preventing a model from introducing a new business
    object or policy vocabulary that none of its citations contain.
    """
    proposal_terms = _grounding_tokens(canonical_wording)
    source_terms = set().union(*(_grounding_tokens(text) for text in source_texts))
    source_variants = set().union(*(_term_variants(term) for term in source_terms))
    return sorted(
        term
        for term in proposal_terms
        if not (_term_variants(term) & source_variants)
    )


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

    supporting_claims: list[SourceClaim] = []
    for claim_id in proposal.supporting_claim_ids + proposal.contradicting_claim_ids:
        row = _claim_in_scope(claim_id)
        if row is None:
            errors.append(f"Invented or cross-analysis claim citation: {claim_id}")
        elif claim_id in proposal.supporting_claim_ids:
            supporting_claims.append(row)

    supporting_evidence = []
    for evidence_id in proposal.supporting_evidence_ids:
        ev = repositories.source_claim_evidence().get_by_id(evidence_id)
        if ev is None:
            errors.append(f"Invented evidence citation: {evidence_id}")
            continue
        parent = _claim_in_scope(ev.source_claim_id)
        if parent is None:
            errors.append(f"Evidence {evidence_id} outside analysis scope")
        else:
            supporting_evidence.append(ev)
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

    source_texts = [
        value
        for claim in supporting_claims
        for value in (
            claim.claim_text,
            claim.actor,
            claim.condition_text,
            claim.action_text,
            claim.result_text,
            claim.exception_text,
            claim.subject_text,
            claim.state_transition,
        )
        if value
    ]
    source_texts.extend(ev.excerpt for ev in supporting_evidence if ev.excerpt)
    unsupported = unsupported_grounding_terms(proposal.canonical_wording, source_texts)
    proposal_terms = _grounding_tokens(proposal.canonical_wording)
    if (
        len(unsupported) >= 2
        and proposal_terms
        and len(unsupported) / len(proposal_terms) > 0.35
    ):
        errors.append(
            "Canonical wording introduces unsupported material terms: "
            + ", ".join(unsupported[:12])
        )

    # Never approve/persist here
    return ValidationResult(
        valid=not errors,
        errors=errors,
        warnings=warnings,
        proposal=proposal if not errors else None,
    )
