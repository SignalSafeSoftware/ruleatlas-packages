"""Deterministic cluster role assignment for canonical synthesis."""

from __future__ import annotations

from dataclasses import dataclass

from ruleatlas_contracts.enums import ClaimClusterRole, SourceClaimRole
from ruleatlas_persistence.models import SourceClaim

from ruleatlas_claims.structured_semantics import (
    StructuredSemantics,
    extract_claim_semantics,
    looks_exception_claim,
    looks_implementation_detail,
    merge_semantics,
)


@dataclass
class ClusterRoleSignals:
    cluster_role: str
    selection_reason: str
    semantics: StructuredSemantics
    is_outdated: bool = False
    is_exception: bool = False
    is_impl_detail: bool = False


_STRONG_ROLES = {
    SourceClaimRole.IMPLEMENTATION.value,
    SourceClaimRole.VERIFICATION.value,
    SourceClaimRole.PRODUCT_INTENT.value,
    SourceClaimRole.CONFIGURATION.value,
}


def score_authority(claims: list[SourceClaim], semantics: StructuredSemantics) -> float:
    """Higher = better canonical candidate."""
    score = 0.0
    roles = {c.claim_role for c in claims}
    if SourceClaimRole.IMPLEMENTATION.value in roles:
        score += 3.0
    if SourceClaimRole.VERIFICATION.value in roles:
        score += 2.0
    if SourceClaimRole.PRODUCT_INTENT.value in roles:
        score += 2.0
    if SourceClaimRole.CONFIGURATION.value in roles:
        score += 1.5
    if semantics.authority_status == "current":
        score += 2.0
    if semantics.authority_status == "superseded":
        score -= 5.0
    score += sum(float(c.confidence or 0) for c in claims) / max(len(claims), 1)
    return score


def _is_outdated_cluster(claims: list[SourceClaim], member_semantics: list[StructuredSemantics]) -> bool:
    superseded_count = sum(1 for semantics in member_semantics if semantics.authority_status == "superseded")
    current_impl = any(
        claim.claim_role == SourceClaimRole.IMPLEMENTATION.value
        and extract_claim_semantics(claim).authority_status == "current"
        for claim in claims
    )
    return bool(superseded_count and not current_impl and superseded_count >= max(1, len(claims) // 2))


def _is_only_exception_cluster(claims: list[SourceClaim], exceptionish: list[SourceClaim]) -> bool:
    has_base_prohibition = any(
        "cannot" in (claim.claim_text or "").lower() or "must not" in (claim.claim_text or "").lower()
        for claim in claims
        if claim not in exceptionish
    )
    if has_base_prohibition:
        return False
    describes_exception = any(
        "except" in (claim.claim_text or "").lower()
        or "correction" in (claim.claim_text or "").lower()
        or claim.exception_text
        for claim in exceptionish
    )
    if not describes_exception:
        return False
    return all(
        looks_exception_claim(claim) or "admin" in (claim.claim_text or "").lower()
        for claim in claims
    )


def _canonical_signals(claims: list[SourceClaim], semantics: StructuredSemantics) -> ClusterRoleSignals | None:
    roles = {claim.claim_role for claim in claims}
    strong = roles & _STRONG_ROLES
    if len(strong) >= 2 and semantics.authority_status != "superseded":
        return ClusterRoleSignals(
            cluster_role=ClaimClusterRole.CANONICAL_RULE.value,
            selection_reason=(
                "Selected as canonical because current implementation, verification, and/or "
                "product intent agree on this domain."
            ),
            semantics=semantics,
        )
    if SourceClaimRole.IMPLEMENTATION.value in roles and semantics.authority_status == "current":
        return ClusterRoleSignals(
            cluster_role=ClaimClusterRole.CANONICAL_RULE.value,
            selection_reason="Selected as canonical from current implementation evidence.",
            semantics=semantics,
        )
    return None


def assign_role_from_claims(claims: list[SourceClaim]) -> ClusterRoleSignals:
    if not claims:
        return ClusterRoleSignals(
            cluster_role=ClaimClusterRole.REVIEW_REQUIRED.value,
            selection_reason="Empty cluster",
            semantics=StructuredSemantics(),
        )

    member_semantics = [extract_claim_semantics(claim) for claim in claims]
    semantics = merge_semantics(member_semantics)
    if _is_outdated_cluster(claims, member_semantics):
        return ClusterRoleSignals(
            cluster_role=ClaimClusterRole.SUPERSEDED.value,
            selection_reason=(
                "Marked outdated/legacy; retained as superseded evidence rather than an active rule."
            ),
            semantics=semantics,
            is_outdated=True,
        )

    exceptionish = [claim for claim in claims if looks_exception_claim(claim)]
    if exceptionish and len(exceptionish) >= len(claims) / 2 and _is_only_exception_cluster(claims, exceptionish):
        return ClusterRoleSignals(
            cluster_role=ClaimClusterRole.EXCEPTION.value,
            selection_reason="Exception / admin-correction language attached to a primary action.",
            semantics=semantics,
            is_exception=True,
        )

    if all(looks_implementation_detail(claim) for claim in claims):
        return ClusterRoleSignals(
            cluster_role=ClaimClusterRole.IMPLEMENTATION_DETAIL.value,
            selection_reason="Config/ops/enablement wording — implementation detail, not a primary business rule.",
            semantics=semantics,
            is_impl_detail=True,
        )

    canonical = _canonical_signals(claims, semantics)
    if canonical is not None:
        return canonical
    return ClusterRoleSignals(
        cluster_role=ClaimClusterRole.REVIEW_REQUIRED.value,
        selection_reason="Ambiguous or weak multi-source agreement; requires human review.",
        semantics=semantics,
    )
