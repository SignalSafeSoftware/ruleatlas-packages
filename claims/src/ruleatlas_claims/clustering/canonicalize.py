"""Canonicalize claim clusters: roles, semantic dedup, attachments, emission policy."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from ruleatlas_contracts.enums import (
    ClaimClusterRole,
    ClaimClusterStatus,
    ConflictKind,
    ConflictType,
    RuleConflictStatus,
)
from ruleatlas_persistence.models import ClaimCluster, RuleConflict, SourceClaim
from ruleatlas_persistence.repositories import RepositoryFactory
from sqlalchemy.orm import Session

from ruleatlas_claims.clustering.cluster_attachments import (
    attach_cluster,
    fold_exception_into_primary,
    fold_supporting_into_primary,
)
from ruleatlas_claims.clustering.cluster_roles import (
    ClusterRoleSignals,
    assign_role_from_claims,
    score_authority,
)
from ruleatlas_claims.conflicts.conflict_detection_v2 import classify_claim_pair
from ruleatlas_claims.structured_semantics import (
    StructuredSemantics,
    extract_claim_semantics,
)

EMITTABLE_ROLES = {
    ClaimClusterRole.CANONICAL_RULE.value,
    ClaimClusterRole.REVIEW_REQUIRED.value,
}

# Roles that can never be the domain primary (attached/suppressed relative to canonical).
_SECONDARY_ROLES = {
    ClaimClusterRole.IMPLEMENTATION_DETAIL.value,
    ClaimClusterRole.SUPERSEDED.value,
    ClaimClusterRole.EXCEPTION.value,
    ClaimClusterRole.SUPPORTING_EVIDENCE.value,
    ClaimClusterRole.CONTRADICTION.value,
}

_PreparedCluster = tuple[ClaimCluster, list[SourceClaim], ClusterRoleSignals]


@dataclass
class CanonicalizationResult:
    raw_clusters: int = 0
    canonical_clusters: int = 0
    emitted_cluster_ids: list[str] = field(default_factory=list)
    suppressed_duplicates: int = 0
    exception_attachments: int = 0
    contradiction_attachments: int = 0
    superseded_claims: int = 0
    metrics: dict = field(default_factory=dict)


def _cluster_claims(session: Session, cluster_id: str) -> list[SourceClaim]:
    repositories = RepositoryFactory(session)
    memberships = repositories.claim_cluster_memberships().list_for_cluster(cluster_id)
    if not memberships:
        return []
    ids = [m.source_claim_id for m in memberships]
    return repositories.source_claims_structured().list_by_ids(ids)


def _update_attrs(cluster: ClaimCluster, **updates: object) -> None:
    attrs = dict(cluster.attributes_json or {})
    attrs.update(updates)
    cluster.attributes_json = attrs


def _facts_conflict(a: StructuredSemantics, b: StructuredSemantics) -> bool:
    if a.timing and b.timing and a.timing != b.timing:
        return True
    if a.threshold and b.threshold and a.threshold != b.threshold:
        return True
    # timing "30_days" vs threshold "30" is compatible, not a conflict
    return False


def _semantics_from_attrs(attrs: dict | None) -> StructuredSemantics:
    raw = (attrs or {}).get("structured_semantics") or {}
    if not isinstance(raw, dict):
        return StructuredSemantics()
    allowed = set(StructuredSemantics.__dataclass_fields__)
    return StructuredSemantics(**{k: raw.get(k) for k in allowed})


def _domain_key(semantics: StructuredSemantics, *, label: str | None = None) -> str:
    family = semantics.action_family or semantics.action or ""
    if not family and label:
        family = _action_family_from_label(label)
    return (family or "unknown").strip().lower() or "unknown"


def _action_family_from_label(label: str) -> str:
    blob = (label or "").lower()
    if "delet" in blob:
        return "delete"
    if "expir" in blob:
        return "expire"
    if "approv" in blob or "threshold" in blob or "policy" in blob:
        # invoice_policy often encodes approval+expiry constants — prefer expire when both
        if "expir" in blob:
            return "expire"
        if "approv" in blob or "threshold" in blob:
            return "approve"
        return "expire"  # policy constants in invoice fixture lean expiry+approval; expire grouping is safer with 30-day
    return ""


def assign_and_canonicalize_clusters(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
) -> CanonicalizationResult:
    """Assign roles, attach exceptions/superseded, mark duplicates; return emission set."""
    clusters = (
        RepositoryFactory(session)
        .claim_clusters()
        .list_for_canonicalization(
            project_id,
            analysis_version_id,
            exclude_status=ClaimClusterStatus.MERGED.value,
        )
    )
    result = CanonicalizationResult(raw_clusters=len(clusters))
    if not clusters:
        result.metrics = _metrics(result)
        return result

    # Pass 1: assign roles + semantics. Pass 2: group by domain; pick canonical; attach the rest.
    prepared = _assign_roles_and_semantics(session, clusters)
    by_domain: dict[str, list[_PreparedCluster]] = {}
    for item in prepared:
        domain = _domain_key(item[2].semantics, label=item[0].label)
        by_domain.setdefault(domain, []).append(item)

    for _domain, items in by_domain.items():
        ranked = _rank_domain(items)
        primary, primary_claims, primary_sem, primary_signals = _select_primary(ranked)
        if primary is not None and primary_signals is not None:
            _finalize_primary(
                session,
                primary=primary,
                primary_claims=primary_claims,
                primary_signals=primary_signals,
                result=result,
                project_id=project_id,
                analysis_version_id=analysis_version_id,
            )
        for cluster, claims, signals in ranked:
            if primary is None or cluster.id == primary.id:
                continue
            _attach_secondary_cluster(
                session,
                cluster=cluster,
                claims=claims,
                signals=signals,
                primary=primary,
                primary_sem=primary_sem,
                primary_claims=primary_claims,
                result=result,
                project_id=project_id,
                analysis_version_id=analysis_version_id,
            )

    session.flush()
    _compute_emission_set(session, clusters, result)
    result.metrics = _metrics(result)
    session.commit()
    return result


def _assign_roles_and_semantics(
    session: Session, clusters: list[ClaimCluster]
) -> list[_PreparedCluster]:
    """Pass 1: assign a role + structured semantics to each cluster in place."""
    prepared: list[_PreparedCluster] = []
    for cluster in clusters:
        claims = _cluster_claims(session, cluster.id)
        signals = assign_role_from_claims(claims)
        # Backfill action_family from cluster label when claim text is weak (legacy stubs)
        sem = signals.semantics
        if not sem.action_family:
            family = _action_family_from_label(cluster.label)
            if family:
                sem = StructuredSemantics(**{**sem.to_dict(), "action_family": family})
                signals = replace(signals, semantics=sem)
        cluster.cluster_role = signals.cluster_role
        _update_attrs(
            cluster,
            structured_semantics=signals.semantics.to_dict(),
            canonical_selection_reason=signals.selection_reason,
        )
        if signals.selection_reason and not cluster.explanation:
            cluster.explanation = signals.selection_reason
        prepared.append((cluster, claims, signals))
    return prepared


def _rank_domain(items: list[_PreparedCluster]) -> list[_PreparedCluster]:
    """Rank a domain's clusters: canonical first, then by authority score."""
    return sorted(
        items,
        key=lambda it: (
            1 if it[0].cluster_role == ClaimClusterRole.CANONICAL_RULE.value else 0,
            score_authority(it[1], it[2].semantics),
        ),
        reverse=True,
    )


def _select_primary(
    ranked: list[_PreparedCluster],
) -> tuple[ClaimCluster | None, list[SourceClaim], StructuredSemantics | None, ClusterRoleSignals | None]:
    """Pick the domain primary: first canonical/review, else promote the strongest non-secondary."""
    for cluster, claims, signals in ranked:
        if cluster.cluster_role in _SECONDARY_ROLES:
            continue
        if cluster.cluster_role in {
            ClaimClusterRole.CANONICAL_RULE.value,
            ClaimClusterRole.REVIEW_REQUIRED.value,
        }:
            return cluster, claims, signals.semantics, signals
    # Promote strongest non-detail cluster for review emission
    for cluster, claims, signals in ranked:
        if cluster.cluster_role in _SECONDARY_ROLES:
            continue
        cluster.cluster_role = ClaimClusterRole.REVIEW_REQUIRED.value
        return cluster, claims, signals.semantics, signals
    return None, [], None, None


def _finalize_primary(
    session: Session,
    *,
    primary: ClaimCluster,
    primary_claims: list[SourceClaim],
    primary_signals: ClusterRoleSignals,
    result: CanonicalizationResult,
    project_id: str,
    analysis_version_id: str,
) -> None:
    """Promote the primary to canonical and record any intra-cluster superseded members."""
    if primary.cluster_role == ClaimClusterRole.REVIEW_REQUIRED.value:
        # Keep review_required when no strong multi-source canonical
        pass
    else:
        primary.cluster_role = ClaimClusterRole.CANONICAL_RULE.value
    reason = (
        primary_signals.selection_reason
        or "Selected as canonical for this action domain."
    )
    # Intra-cluster superseded members (60-day mixed into 30-day cluster)
    current_members = [
        c for c in primary_claims if extract_claim_semantics(c).authority_status == "current"
    ]
    superseded_members = [
        c for c in primary_claims if extract_claim_semantics(c).authority_status == "superseded"
    ]
    if superseded_members and current_members:
        attrs = dict(primary.attributes_json or {})
        sid = list(attrs.get("attached_superseded_claim_ids") or [])
        for sc in superseded_members:
            if sc.id not in sid:
                sid.append(sc.id)
        attrs["attached_superseded_claim_ids"] = sid
        attrs["provenance_explanation"] = (
            reason
            + " A legacy/outdated claim with conflicting timing or threshold was retained "
            "as superseded evidence."
        )
        primary.attributes_json = attrs
        result.superseded_claims += len(superseded_members)
        result.contradiction_attachments += 1
        _persist_supersession_conflicts(
            session,
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            primary_claims=current_members,
            other_claims=superseded_members,
        )
        reason = attrs["provenance_explanation"]
    _update_attrs(
        primary,
        canonical_selection_reason=reason,
        attached_to_cluster_id=None,
        suppression_reason=None,
    )
    if primary.explanation is None:
        primary.explanation = reason


def _is_superseded_secondary(
    role: str, cluster_sem: StructuredSemantics, primary_sem: StructuredSemantics | None
) -> bool:
    return bool(
        role == ClaimClusterRole.SUPERSEDED.value
        or cluster_sem.authority_status == "superseded"
        or (
            primary_sem is not None
            and cluster_sem.timing
            and primary_sem.timing
            and cluster_sem.timing != primary_sem.timing
            and cluster_sem.action_family == primary_sem.action_family
        )
    )


def _is_exception_secondary(
    role: str, cluster_sem: StructuredSemantics, primary_sem: StructuredSemantics | None
) -> bool:
    return bool(
        role == ClaimClusterRole.EXCEPTION.value
        or (
            bool(cluster_sem.exception)
            and primary_sem is not None
            and cluster_sem.action_family == primary_sem.action_family
            and role != ClaimClusterRole.CANONICAL_RULE.value
        )
    )


def _same_action_family(
    cluster: ClaimCluster,
    primary: ClaimCluster,
    cluster_sem: StructuredSemantics,
    primary_sem: StructuredSemantics | None,
) -> bool:
    if primary_sem is None:
        return False
    return (cluster_sem.action_family or _action_family_from_label(cluster.label)) == (
        primary_sem.action_family or _action_family_from_label(primary.label)
    )


def _attach_secondary_cluster(
    session: Session,
    *,
    cluster: ClaimCluster,
    claims: list[SourceClaim],
    signals: ClusterRoleSignals,
    primary: ClaimCluster,
    primary_sem: StructuredSemantics | None,
    primary_claims: list[SourceClaim],
    result: CanonicalizationResult,
    project_id: str,
    analysis_version_id: str,
) -> None:
    """Classify one non-primary cluster relative to the domain primary and attach/suppress it."""
    cluster_sem = signals.semantics
    role = cluster.cluster_role

    if role == ClaimClusterRole.IMPLEMENTATION_DETAIL.value:
        return

    if _is_superseded_secondary(role, cluster_sem, primary_sem):
        cluster.cluster_role = ClaimClusterRole.SUPERSEDED.value
        attach_cluster(
            cluster,
            primary,
            reason=(
                f"Superseded relative to canonical cluster {primary.id}: "
                f"conflicting timing/threshold retained as evidence."
            ),
            kind="superseded",
        )
        result.superseded_claims += len(claims)
        _persist_supersession_conflicts(
            session,
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            primary_claims=primary_claims,
            other_claims=claims,
        )
        result.contradiction_attachments += 1
        return

    if _is_exception_secondary(role, cluster_sem, primary_sem):
        cluster.cluster_role = ClaimClusterRole.EXCEPTION.value
        attach_cluster(
            cluster,
            primary,
            reason=f"Exception attached to canonical cluster {primary.id}.",
            kind="exception",
        )
        result.exception_attachments += 1
        fold_exception_into_primary(primary, claims)
        return

    # Same identity → supporting duplicate
    if (
        primary_sem is not None
        and cluster_sem.identity_key() == primary_sem.identity_key()
        and cluster.id != primary.id
    ):
        cluster.cluster_role = ClaimClusterRole.SUPPORTING_EVIDENCE.value
        attach_cluster(
            cluster,
            primary,
            reason=(
                f"Near-duplicate of canonical cluster {primary.id}; "
                "suppressed as supporting evidence (not discarded)."
            ),
            kind="supporting",
        )
        result.suppressed_duplicates += 1
        fold_supporting_into_primary(primary, claims)
        return

    # Same family without conflicting timing/threshold → supporting (e.g. config constants)
    if (
        primary_sem is not None
        and _same_action_family(cluster, primary, cluster_sem, primary_sem)
        and not _facts_conflict(primary_sem, cluster_sem)
    ):
        cluster.cluster_role = ClaimClusterRole.SUPPORTING_EVIDENCE.value
        attach_cluster(
            cluster,
            primary,
            reason=(
                f"Supporting evidence for canonical cluster {primary.id} "
                "(same action family; no conflicting timing/threshold)."
            ),
            kind="supporting",
        )
        result.suppressed_duplicates += 1
        fold_supporting_into_primary(primary, claims)
        return

    # Different threshold/actor same family → contradiction / attach
    if (
        primary_sem is not None
        and _same_action_family(cluster, primary, cluster_sem, primary_sem)
        and cluster_sem.identity_key() != primary_sem.identity_key()
    ):
        cluster.cluster_role = ClaimClusterRole.CONTRADICTION.value
        attach_cluster(
            cluster,
            primary,
            reason=f"Contradiction attached to canonical cluster {primary.id}.",
            kind="contradiction",
        )
        result.contradiction_attachments += 1
        return


def _is_emittable(cluster: ClaimCluster, attrs: dict) -> bool:
    return bool(
        cluster.cluster_role in EMITTABLE_ROLES
        and not attrs.get("attached_to_cluster_id")
        and not attrs.get("suppression_reason")
        and not cluster.is_locked
    )


def _review_suppressed_by_canonical(
    cluster: ClaimCluster, clusters: list[ClaimCluster], attrs: dict
) -> bool:
    """A review_required cluster is suppressed when a canonical cluster covers its domain."""
    domain = _domain_key(_semantics_from_attrs(attrs), label=cluster.label)
    return any(
        c.cluster_role == ClaimClusterRole.CANONICAL_RULE.value
        and _domain_key(_semantics_from_attrs(c.attributes_json), label=c.label) == domain
        for c in clusters
    )


def _compute_emission_set(
    session: Session, clusters: list[ClaimCluster], result: CanonicalizationResult
) -> None:
    for cluster in clusters:
        session.add(cluster)
        if cluster.cluster_role == ClaimClusterRole.CANONICAL_RULE.value:
            result.canonical_clusters += 1
        attrs = cluster.attributes_json or {}
        if not _is_emittable(cluster, attrs):
            continue
        # review_required only when no canonical for same domain
        if (
            cluster.cluster_role == ClaimClusterRole.REVIEW_REQUIRED.value
            and _review_suppressed_by_canonical(cluster, clusters, attrs)
        ):
            continue
        # Never emit superseded/exception/etc. even if role drifted
        if cluster.cluster_role not in EMITTABLE_ROLES:
            continue
        if (attrs.get("structured_semantics") or {}).get("authority_status") == "superseded":
            continue
        result.emitted_cluster_ids.append(cluster.id)


def _persist_supersession_conflicts(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
    primary_claims: list[SourceClaim],
    other_claims: list[SourceClaim],
) -> None:
    for a in primary_claims:
        for b in other_claims:
            hit = classify_claim_pair(a, b)
            kind = ConflictKind.SUPERSESSION.value
            explanation = (
                "Outdated/legacy claim conflicts with current timing or threshold; "
                "retained as supersession evidence."
            )
            if hit and hit.conflict_kind == ConflictKind.CONTRADICTION.value:
                kind = ConflictKind.CONTRADICTION.value
                explanation = hit.explanation
            elif hit is None:
                # Still record supersession when outdated markers + same action family
                from ruleatlas_claims.structured_semantics import (
                    extract_claim_semantics,
                )

                sa, sb = extract_claim_semantics(a), extract_claim_semantics(b)
                if sa.action_family != sb.action_family:
                    continue
            session.add(
                RuleConflict(
                    project_id=project_id,
                    analysis_version_id=analysis_version_id,
                    conflict_type=ConflictType.TEST_CODE,
                    area=(a.subject_text or b.subject_text or "claims")[:255],
                    source_a_type=a.claim_role,
                    source_a_claim=a.claim_text,
                    source_b_type=b.claim_role,
                    source_b_claim=b.claim_text,
                    risk="medium",
                    recommended_fix=explanation,
                    confidence_score=0.7,
                    status=RuleConflictStatus.OPEN,
                    conflict_kind=kind,
                    attributes_json={
                        "claim_a_id": a.id,
                        "claim_b_id": b.id,
                        "explanation": explanation,
                        "ai_explanation": None,
                    },
                )
            )


def _metrics(result: CanonicalizationResult) -> dict:
    return {
        "raw_clusters": result.raw_clusters,
        "canonical_clusters": result.canonical_clusters,
        "emitted_candidates": len(result.emitted_cluster_ids),
        "suppressed_duplicates": result.suppressed_duplicates,
        "exception_attachments": result.exception_attachments,
        "contradiction_attachments": result.contradiction_attachments,
        "superseded_claims": result.superseded_claims,
    }


def enrichment_for_proposal(cluster: ClaimCluster) -> dict:
    """Fields to fold into AiRuleProposal before/after synthesis."""
    attrs = cluster.attributes_json or {}
    exceptions = attrs.get("attached_exception_texts") or []
    return {
        "exceptions_extra": "; ".join(exceptions) if exceptions else None,
        "attached_exception_ids": attrs.get("attached_exception_claim_ids") or [],
        "superseded_claim_ids": attrs.get("attached_superseded_claim_ids") or [],
        "supporting_extra_ids": attrs.get("attached_supporting_claim_ids") or [],
        "provenance_explanation": attrs.get("provenance_explanation")
        or attrs.get("canonical_selection_reason"),
        "structured_semantics": attrs.get("structured_semantics") or {},
        "cluster_role": cluster.cluster_role,
    }
