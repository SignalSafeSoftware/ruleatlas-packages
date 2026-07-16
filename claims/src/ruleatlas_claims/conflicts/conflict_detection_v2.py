"""Conflict detection v2: contradiction / exception / scope / supersession from claims."""

from __future__ import annotations

from dataclasses import dataclass

from ruleatlas_contracts.enums import ConflictKind, ConflictType, RuleConflictStatus, SourceClaimRole
from ruleatlas_persistence.models import RuleConflict, SourceClaim
from ruleatlas_persistence.repositories import RepositoryFactory
from sqlalchemy.orm import Session


@dataclass
class DetectedConflict:
    conflict_kind: str
    area: str
    source_a_type: str
    source_a_claim: str
    source_b_type: str
    source_b_claim: str
    claim_a_id: str
    claim_b_id: str
    explanation: str
    confidence: float


def _norm(text: str | None) -> str:
    return (text or "").strip().lower()


def _same_action(a: SourceClaim, b: SourceClaim) -> bool:
    aa, bb = _norm(a.action_text), _norm(b.action_text)
    if aa and bb and aa == bb:
        return True
    # Fall back to shared subject
    return bool(a.subject_text and b.subject_text and _norm(a.subject_text) == _norm(b.subject_text))


def _is_exception_pair(a: SourceClaim, b: SourceClaim) -> bool:
    """Exception: same action with explicit exception/deny path vs allow path."""
    if not _same_action(a, b):
        return False
    has_exc = bool(a.exception_text or b.exception_text)
    deny_tokens = ("deny", "denied", "forbidden", "permissionerror", "not allowed")
    a_deny = any(t in _norm(a.claim_text) + _norm(a.result_text) for t in deny_tokens)
    b_deny = any(t in _norm(b.claim_text) + _norm(b.result_text) for t in deny_tokens)
    a_allow = any(t in _norm(a.claim_text) + _norm(a.result_text) for t in ("allow", "permitted", "can "))
    b_allow = any(t in _norm(b.claim_text) + _norm(b.result_text) for t in ("allow", "permitted", "can "))
    if has_exc and (a_deny != b_deny or a_allow != b_allow):
        # Different actors/conditions → exception rather than flat contradiction
        if _norm(a.actor) != _norm(b.actor) or _norm(a.condition_text) != _norm(b.condition_text):
            return True
    return False


def _is_contradiction(a: SourceClaim, b: SourceClaim) -> bool:
    if not _same_action(a, b):
        return False
    if _is_exception_pair(a, b):
        return False
    # Same actor + opposing outcomes
    if _norm(a.actor) and _norm(a.actor) == _norm(b.actor):
        ra, rb = _norm(a.result_text), _norm(b.result_text)
        if ra and rb and ra != rb:
            return True
        ca, cb = _norm(a.claim_text), _norm(b.claim_text)
        deny = ("deny", "denied", "cannot", "must not")
        allow = ("allow", "can ", "may ")
        a_d = any(t in ca for t in deny)
        b_d = any(t in cb for t in deny)
        a_a = any(t in ca for t in allow)
        b_a = any(t in cb for t in allow)
        if (a_d and b_a) or (a_a and b_d):
            return True
    return False


def _is_scope_difference(a: SourceClaim, b: SourceClaim) -> bool:
    if not _same_action(a, b):
        return False
    if _norm(a.condition_text) and _norm(b.condition_text) and _norm(a.condition_text) != _norm(b.condition_text):
        if not _is_contradiction(a, b) and not _is_exception_pair(a, b):
            return True
    return False


def _is_supersession(a: SourceClaim, b: SourceClaim) -> bool:
    """Outdated markers + conflicting numeric timing/threshold vs current evidence."""
    from ruleatlas_claims.structured_semantics import extract_claim_semantics

    if not _same_action(a, b):
        # Also allow same action family via subject/expire/approve language
        sa, sb = extract_claim_semantics(a), extract_claim_semantics(b)
        if not sa.action_family or sa.action_family != sb.action_family:
            return False
    else:
        sa, sb = extract_claim_semantics(a), extract_claim_semantics(b)

    outdated = {sa.authority_status, sb.authority_status}
    if "superseded" not in outdated or "current" not in outdated:
        # Path/text markers alone on one side still count
        if "superseded" not in outdated:
            return False
    # Conflicting timing or threshold
    if sa.timing and sb.timing and sa.timing != sb.timing:
        return True
    return bool(sa.threshold and sb.threshold and sa.threshold != sb.threshold)


def classify_claim_pair(a: SourceClaim, b: SourceClaim) -> DetectedConflict | None:
    if a.id is not None and b.id is not None and a.id == b.id:
        return None
    # Prefer roles that can conflict across evidence kinds
    roles = {a.claim_role, b.claim_role}
    interesting = roles & {
        SourceClaimRole.IMPLEMENTATION.value,
        SourceClaimRole.VERIFICATION.value,
        SourceClaimRole.PRODUCT_INTENT.value,
        SourceClaimRole.CONFIGURATION.value,
    }
    if len(interesting) < 1:
        return None

    if _is_supersession(a, b):
        kind = ConflictKind.SUPERSESSION.value
        explanation = (
            "Outdated/legacy claim conflicts with current timing or threshold; "
            "retained as supersession evidence"
        )
        conf = 0.78
    elif _is_exception_pair(a, b):
        kind = ConflictKind.EXCEPTION.value
        explanation = (
            f"Exception/deny path vs allow path for same action "
            f"(actors={a.actor!r}/{b.actor!r}; conditions differ)"
        )
        conf = 0.75
    elif _is_contradiction(a, b):
        kind = ConflictKind.CONTRADICTION.value
        explanation = "Opposing outcomes for same actor/action without exception framing"
        conf = 0.8
    elif _is_scope_difference(a, b):
        kind = ConflictKind.SCOPE_DIFFERENCE.value
        explanation = "Same action under different conditions/scopes"
        conf = 0.65
    else:
        return None

    return DetectedConflict(
        conflict_kind=kind,
        area=(a.subject_text or b.subject_text or "claims")[:255],
        source_a_type=a.claim_role,
        source_a_claim=a.claim_text,
        source_b_type=b.claim_role,
        source_b_claim=b.claim_text,
        claim_a_id=a.id,
        claim_b_id=b.id,
        explanation=explanation,
        confidence=conf,
    )


def detect_conflicts_v2(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
    persist: bool = True,
) -> list[DetectedConflict]:
    """Semantic conflict detection over structured claims.

    NOT WIRED (RA-04-001): no route or production pipeline calls this; ``persist=True`` is exercised
    only by tests and performs NO dedup / clear-existing. Add an idempotency guard (clear-existing,
    or upsert by semantic key) before wiring to any route, or repeated runs will duplicate rows.

    Performance (RA-17-005): this compares **all claim pairs** (O(n^2)). Add blocking/indexing (e.g.
    bucket by subject or normalized claim text and only compare within a bucket) before productionizing
    on large analyses.
    """
    claims = (
        RepositoryFactory(session)
        .source_claims_structured()
        .list_for_analysis_ordered_by_id(project_id, analysis_version_id)
    )
    found: list[DetectedConflict] = []
    for i, a in enumerate(claims):
        for b in claims[i + 1 :]:
            hit = classify_claim_pair(a, b)
            if hit:
                found.append(hit)

    if persist:
        for item in found:
            row = RuleConflict(
                project_id=project_id,
                analysis_version_id=analysis_version_id,
                conflict_type=ConflictType.TEST_CODE,  # legacy column; semantic kind is authoritative
                area=item.area,
                source_a_type=item.source_a_type,
                source_a_claim=item.source_a_claim,
                source_b_type=item.source_b_type,
                source_b_claim=item.source_b_claim,
                risk="medium",
                recommended_fix=item.explanation,
                confidence_score=item.confidence,
                status=RuleConflictStatus.OPEN,
                conflict_kind=item.conflict_kind,
                attributes_json={
                    "claim_a_id": item.claim_a_id,
                    "claim_b_id": item.claim_b_id,
                    "explanation": item.explanation,
                    "ai_explanation": None,  # AI only after deterministic detection
                },
            )
            session.add(row)
        session.commit()
    return found
