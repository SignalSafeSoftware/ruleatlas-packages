"""Claim clustering: deterministic signals + optional lexical/embedding similarity."""

from __future__ import annotations

import hashlib
import math
import re
from collections import defaultdict
from dataclasses import dataclass

from ruleatlas_contracts.enums import AuditEntityType, AuditEventType, ClaimClusterStatus
from ruleatlas_persistence.audit import record_audit_event
from ruleatlas_persistence.mixins import now_utc
from ruleatlas_persistence.models import ClaimCluster, ClaimClusterMembership, ClaimEmbedding, SourceClaim
from ruleatlas_persistence.repositories import RepositoryFactory
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

ALGORITHM_KEY = "deterministic_v1"
ALGORITHM_VERSION = "1"
MAX_CLUSTER_SIZE = 12
GENERIC_STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "for", "on", "is", "be", "if",
    "user", "system", "when", "then", "must", "should", "can", "with", "from",
}


@dataclass
class ClusterConfig:
    max_size: int = MAX_CLUSTER_SIZE
    lexical_threshold: float = 0.45
    embedding_threshold: float = 0.78
    use_embeddings: bool = False
    embedding_model_key: str = "hash_bag"
    embedding_model_version: str = "1"


def _require_cluster(session: Session, cluster_id: str) -> ClaimCluster:
    cluster = RepositoryFactory(session).claim_clusters().get_by_id(cluster_id)
    if cluster is None:
        raise LookupError(f"Claim cluster not found: {cluster_id}")
    return cluster


def _pair_key(left_id: str, right_id: str) -> tuple[str, str]:
    return (left_id, right_id) if left_id <= right_id else (right_id, left_id)


def _tokens(text: str) -> set[str]:
    return {
        t
        for t in re.findall(r"[a-z0-9_]{3,}", (text or "").lower())
        if t not in GENERIC_STOPWORDS
    }


def lexical_similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class EmbeddingProvider:
    """Optional embedding abstraction — default is deterministic hash bag (no external calls)."""

    def __init__(self, model_key: str = "hash_bag", model_version: str = "1", dim: int = 32) -> None:
        self.model_key = model_key
        self.model_version = model_version
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in _tokens(text):
            idx = int(hashlib.md5(token.encode()).hexdigest(), 16) % self.dim
            vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=False))


def _signals(a: SourceClaim, b: SourceClaim, *, lexical: float, embedding: float | None) -> dict:
    if (
        a.subject_text
        and b.subject_text
        and a.subject_text.strip().lower() != b.subject_text.strip().lower()
    ):
        return {
            "score": 0.0,
            "reasons": ["subject_mismatch"],
            "lexical": lexical,
            "embedding": embedding,
        }
    shared_subject = bool(
        a.subject_text and b.subject_text and a.subject_text.lower() == b.subject_text.lower()
    )
    shared_path = bool(a.source_path and b.source_path and a.source_path == b.source_path)
    shared_node = bool(a.graph_node_id and b.graph_node_id and a.graph_node_id == b.graph_node_id)
    role_diversity = a.claim_role != b.claim_role
    # Constants / thresholds crude signal
    nums_a = set(re.findall(r"\b\d+\b", a.claim_text or ""))
    nums_b = set(re.findall(r"\b\d+\b", b.claim_text or ""))
    shared_constants = bool(nums_a & nums_b)
    score = 0.0
    reasons = []
    if shared_node:
        score += 0.45
        reasons.append("shared_graph_node")
    if shared_subject:
        score += 0.4
        reasons.append("shared_subject")
    if shared_path and role_diversity:
        score += 0.2
        reasons.append("same_path_diverse_roles")
    elif shared_path:
        score += 0.08
        reasons.append("same_path")
    if shared_constants:
        score += 0.1
        reasons.append("shared_constants")
    action_overlap = bool(
        a.action_text
        and b.action_text
        and _tokens(a.action_text) & _tokens(b.action_text)
    )
    if action_overlap:
        score += 0.15
        reasons.append("shared_action_tokens")
    if lexical >= 0.45:
        score += min(lexical, 0.35)
        reasons.append(f"lexical:{lexical:.2f}")
    if embedding is not None and embedding >= 0.78:
        score += min(embedding * 0.25, 0.25)
        reasons.append(f"embedding:{embedding:.2f}")
    # Do not cluster solely on generic words — require at least one structured signal
    # or strong lexical with shared subject/path
    structured = shared_node or shared_subject or shared_path or shared_constants or action_overlap
    if not structured and lexical < 0.6:
        score = 0.0
        reasons = ["rejected_generic_only"]
    return {"score": score, "reasons": reasons, "lexical": lexical, "embedding": embedding}


def form_clusters(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
    config: ClusterConfig | None = None,
) -> dict:
    cfg = config or ClusterConfig()
    claims = (
        RepositoryFactory(session)
        .source_claims_structured()
        .list_for_analysis_ordered(project_id, analysis_version_id)
    )
    # Preserve locked clusters; drop unlocked prior clusters for reproducibility.
    repositories = RepositoryFactory(session)
    locked = repositories.claim_clusters().list_by_lock_state(
        project_id, analysis_version_id, is_locked=True
    )
    locked_claim_ids = _collect_locked_claim_ids(repositories, locked)
    _reset_unlocked_clusters(session, repositories, project_id, analysis_version_id)

    embedder = EmbeddingProvider(cfg.embedding_model_key, cfg.embedding_model_version)
    vectors = _compute_claim_embeddings(
        session,
        repositories,
        claims,
        embedder,
        cfg,
        project_id=project_id,
        analysis_version_id=analysis_version_id,
    )

    active = [c for c in claims if c.id not in locked_claim_ids]
    pair_meta, groups = _union_find_groups(active, vectors)

    created = 0
    for members in groups.values():
        for chunk in _split_oversized(members, cfg):
            _persist_cluster_for_chunk(
                session,
                chunk=chunk,
                pair_meta=pair_meta,
                vectors=vectors,
                cfg=cfg,
                project_id=project_id,
                analysis_version_id=analysis_version_id,
            )
            created += 1
    session.commit()
    return {
        "clusters_created": created,
        "locked_preserved": len(locked),
        "claims_considered": len(active),
        "algorithm": f"{ALGORITHM_KEY}:{ALGORITHM_VERSION}",
    }


def _collect_locked_claim_ids(
    repositories: RepositoryFactory, locked: list[ClaimCluster]
) -> set[str]:
    locked_claim_ids: set[str] = set()
    for cluster in locked:
        for m in repositories.claim_cluster_memberships().list_for_cluster(cluster.id):
            locked_claim_ids.add(m.source_claim_id)
    return locked_claim_ids


def _reset_unlocked_clusters(
    session: Session,
    repositories: RepositoryFactory,
    project_id: str,
    analysis_version_id: str,
) -> None:
    unlocked = repositories.claim_clusters().list_by_lock_state(
        project_id, analysis_version_id, is_locked=False
    )
    for cluster in unlocked:
        memberships = repositories.claim_cluster_memberships().list_for_cluster(cluster.id)
        for membership in memberships:
            session.delete(membership)
        session.delete(cluster)
    session.flush()


def _compute_claim_embeddings(
    session: Session,
    repositories: RepositoryFactory,
    claims: list[SourceClaim],
    embedder: EmbeddingProvider,
    cfg: ClusterConfig,
    *,
    project_id: str,
    analysis_version_id: str,
) -> dict[str, list[float]]:
    vectors: dict[str, list[float]] = {}
    if not cfg.use_embeddings:
        return vectors
    try:
        for claim in claims:
            ch = content_hash(claim.claim_text)
            existing = repositories.claim_clusters().get_embedding(
                analysis_version_id,
                ch,
                embedder.model_key,
                embedder.model_version,
            )
            if existing is None:
                vec = embedder.embed(claim.claim_text)
                existing = ClaimEmbedding(
                    project_id=project_id,
                    analysis_version_id=analysis_version_id,
                    source_claim_id=claim.id,
                    content_hash=ch,
                    model_key=embedder.model_key,
                    model_version=embedder.model_version,
                    vector_json=vec,
                    dimensions=len(vec),
                    attributes_json={},
                )
                session.add(existing)
                session.flush()
            vectors[claim.id] = list(existing.vector_json)
    except (SQLAlchemyError, TypeError, ValueError):  # — embeddings optional
        vectors = {}
    return vectors


def _union_find_groups(
    active: list[SourceClaim], vectors: dict[str, list[float]]
) -> tuple[dict[tuple[str, str], dict], dict[str, list[SourceClaim]]]:
    """Union claims whose pairwise signal clears threshold; return pair metadata + groups."""
    parent: dict[str, str] = {c.id: c.id for c in active}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    pair_meta: dict[tuple[str, str], dict] = {}
    for i, a in enumerate(active):
        for b in active[i + 1 :]:
            lex = lexical_similarity(a.claim_text, b.claim_text)
            emb = None
            if a.id in vectors and b.id in vectors:
                emb = cosine(vectors[a.id], vectors[b.id])
            sig = _signals(a, b, lexical=lex, embedding=emb)
            if sig["score"] >= 0.35:
                union(a.id, b.id)
                key = _pair_key(a.id, b.id)
                pair_meta[key] = sig

    groups: dict[str, list[SourceClaim]] = defaultdict(list)
    for claim in active:
        groups[find(claim.id)].append(claim)
    return pair_meta, groups


def _split_oversized(members: list[SourceClaim], cfg: ClusterConfig) -> list[list[SourceClaim]]:
    """Split an oversized group into max-size chunks by greedy lexical proximity to a seed."""
    if len(members) <= cfg.max_size:
        return [members]
    chunks: list[list[SourceClaim]] = []
    remaining = list(members)
    while remaining:
        seed = remaining.pop(0)
        chunk = [seed]
        scored = sorted(
            remaining,
            key=lambda c: lexical_similarity(seed.claim_text, c.claim_text),
            reverse=True,
        )
        for c in scored:
            if len(chunk) >= cfg.max_size:
                break
            chunk.append(c)
            remaining.remove(c)
        chunks.append(chunk)
    return chunks


def _persist_cluster_for_chunk(
    session: Session,
    *,
    chunk: list[SourceClaim],
    pair_meta: dict[tuple[str, str], dict],
    vectors: dict[str, list[float]],
    cfg: ClusterConfig,
    project_id: str,
    analysis_version_id: str,
) -> None:
    chunk = sorted(chunk, key=lambda c: c.id)
    label = chunk[0].subject_text or chunk[0].claim_text[:80]
    roles = sorted({c.claim_role for c in chunk})
    ckey = "cluster:" + hashlib.sha256(
        "|".join(c.id for c in chunk).encode()
    ).hexdigest()[:16]
    explanation = (
        f"Grouped {len(chunk)} claims via {ALGORITHM_KEY} "
        f"(roles={','.join(roles)}; max_size={cfg.max_size})"
    )
    cluster = ClaimCluster(
        project_id=project_id,
        analysis_version_id=analysis_version_id,
        canonical_key=ckey,
        label=label,
        status=ClaimClusterStatus.CANDIDATE.value,
        algorithm_key=ALGORITHM_KEY,
        algorithm_version=ALGORITHM_VERSION,
        explanation=explanation,
        score=max(
            (
                pair_meta.get(_pair_key(chunk[0].id, m.id), {}).get("score", 0.0)
                for m in chunk[1:]
            ),
            default=0.5,
        ),
        attributes_json={
            "member_count": len(chunk),
            "roles": roles,
            "embedding_used": bool(vectors),
        },
    )
    session.add(cluster)
    session.flush()
    for member in chunk:
        reasons: list[str] = []
        score = 0.5
        for other in chunk:
            if other.id == member.id:
                continue
            meta = pair_meta.get(_pair_key(member.id, other.id))
            if meta:
                reasons.extend(meta["reasons"])
                score = max(score, meta["score"])
        reason = ", ".join(dict.fromkeys(reasons)) or "singleton_seed"
        session.add(
            ClaimClusterMembership(
                project_id=project_id,
                analysis_version_id=analysis_version_id,
                claim_cluster_id=cluster.id,
                source_claim_id=member.id,
                join_reason=reason,
                join_signals_json={"reasons": list(dict.fromkeys(reasons))},
                join_score=score,
                attributes_json={},
            )
        )


def lock_cluster(session: Session, cluster_id: str, *, actor: str) -> ClaimCluster:
    cluster = _require_cluster(session, cluster_id)
    cluster.is_locked = True
    cluster.locked_at = now_utc()
    cluster.locked_by = actor
    cluster.status = ClaimClusterStatus.LOCKED.value
    session.add(cluster)
    session.commit()
    record_audit_event(
        session,
        event_type=AuditEventType.CLAIM_CLUSTER_LOCKED,
        summary=f"Locked claim cluster {cluster.label}",
        project_id=cluster.project_id,
        entity_type=AuditEntityType.PROJECT,
        entity_id=cluster.id,
        actor=actor,
        metadata={"cluster_id": cluster.id},
    )
    session.refresh(cluster)
    return cluster


def unlock_cluster(session: Session, cluster_id: str, *, actor: str) -> ClaimCluster:
    cluster = _require_cluster(session, cluster_id)
    cluster.is_locked = False
    cluster.locked_at = None
    cluster.locked_by = None
    cluster.status = ClaimClusterStatus.NEEDS_REVIEW.value
    session.add(cluster)
    session.commit()
    record_audit_event(
        session,
        event_type=AuditEventType.CLAIM_CLUSTER_UNLOCKED,
        summary=f"Unlocked claim cluster {cluster.label}",
        project_id=cluster.project_id,
        entity_type=AuditEntityType.PROJECT,
        entity_id=cluster.id,
        actor=actor,
        metadata={"cluster_id": cluster.id},
    )
    session.refresh(cluster)
    return cluster


def merge_clusters(
    session: Session,
    *,
    target_cluster_id: str,
    source_cluster_id: str,
    actor: str,
) -> ClaimCluster:
    repositories = RepositoryFactory(session)
    target = _require_cluster(session, target_cluster_id)
    source = _require_cluster(session, source_cluster_id)
    if target.is_locked or source.is_locked:
        raise ValueError("Cannot merge locked clusters")
    if target.analysis_version_id != source.analysis_version_id:
        raise ValueError("Clusters must share analysis version")
    for membership in repositories.claim_cluster_memberships().list_for_cluster(source.id):
        exists = repositories.claim_cluster_memberships().get_for_cluster_and_claim(
            target.id, membership.source_claim_id
        )
        if exists is None:
            membership.claim_cluster_id = target.id
            membership.join_reason = f"merged_from:{source.id}; {membership.join_reason}"
            session.add(membership)
        else:
            session.delete(membership)
    source.status = ClaimClusterStatus.MERGED.value
    source.parent_cluster_id = target.id
    session.add(source)
    session.commit()
    record_audit_event(
        session,
        event_type=AuditEventType.CLAIM_CLUSTER_MERGED,
        summary=f"Merged cluster {source.id} into {target.id}",
        project_id=target.project_id,
        entity_type=AuditEntityType.PROJECT,
        entity_id=target.id,
        actor=actor,
        metadata={"source_cluster_id": source.id, "target_cluster_id": target.id},
    )
    session.refresh(target)
    return target


def split_cluster(
    session: Session,
    *,
    cluster_id: str,
    claim_ids: list[str],
    actor: str,
) -> ClaimCluster:
    repositories = RepositoryFactory(session)
    source = _require_cluster(session, cluster_id)
    if source.is_locked:
        raise ValueError("Cannot split locked cluster")
    members = repositories.claim_cluster_memberships().list_for_cluster_claim_ids(
        source.id, claim_ids
    )
    if not members:
        raise ValueError("No matching memberships to split")
    ckey = "cluster:" + hashlib.sha256(
        f"split|{source.id}|{','.join(sorted(claim_ids))}".encode()
    ).hexdigest()[:16]
    new_cluster = ClaimCluster(
        project_id=source.project_id,
        analysis_version_id=source.analysis_version_id,
        canonical_key=ckey,
        label=f"Split from {source.label}"[:512],
        status=ClaimClusterStatus.SPLIT.value,
        algorithm_key=ALGORITHM_KEY,
        algorithm_version=ALGORITHM_VERSION,
        explanation=f"Manual split from {source.id}",
        parent_cluster_id=source.id,
        score=source.score,
        attributes_json={"split_from": source.id},
    )
    session.add(new_cluster)
    session.flush()
    for membership in members:
        membership.claim_cluster_id = new_cluster.id
        membership.join_reason = f"split_from:{source.id}; {membership.join_reason}"
        session.add(membership)
    session.commit()
    record_audit_event(
        session,
        event_type=AuditEventType.CLAIM_CLUSTER_SPLIT,
        summary=f"Split {len(members)} claims from cluster {source.id}",
        project_id=source.project_id,
        entity_type=AuditEntityType.PROJECT,
        entity_id=new_cluster.id,
        actor=actor,
        metadata={"source_cluster_id": source.id, "new_cluster_id": new_cluster.id},
    )
    session.refresh(new_cluster)
    return new_cluster
