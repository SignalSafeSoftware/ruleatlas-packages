"""Source claim persistence and providers.

Heuristic/config extraction of claims from source files lives in the *extraction*
context (``ruleatlas.application.extraction.heuristic_claim_extraction``) so the
``claims`` context does not depend on extraction internals.
"""

from __future__ import annotations

import hashlib

from ruleatlas_contracts.claims import ClaimDraft as ClaimDraft
from ruleatlas_contracts.enums import SourceClaimRole, SourceClaimStatus
from ruleatlas_persistence.models import (
    SourceClaim,
    SourceClaimEvidence,
)
from ruleatlas_persistence.repositories import RepositoryFactory
from sqlalchemy import select
from sqlalchemy.orm import Session


def claim_canonical_key(provider_key: str, path: str, text: str, start_line: int | None = None) -> str:
    digest = hashlib.sha256(f"{path}|{start_line}|{text}".encode()).hexdigest()[:16]
    return f"claim:{provider_key}:{digest}"


def persist_claim(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
    scan_run_id: str | None,
    draft: ClaimDraft,
) -> SourceClaim:
    key = claim_canonical_key(
        draft.provider_key, draft.source_path or "", draft.claim_text, draft.start_line
    )
    existing = RepositoryFactory(session).source_claims_structured().get_by_canonical_key(
        analysis_version_id, key
    )
    if existing is not None:
        return existing
    row = SourceClaim(
        project_id=project_id,
        analysis_version_id=analysis_version_id,
        scan_run_id=scan_run_id,
        canonical_key=key,
        claim_text=draft.claim_text,
        actor=draft.actor,
        condition_text=draft.condition_text,
        action_text=draft.action_text,
        result_text=draft.result_text,
        exception_text=draft.exception_text,
        subject_text=draft.subject_text,
        state_transition=draft.state_transition,
        claim_role=draft.claim_role,
        status=SourceClaimStatus.CANDIDATE.value,
        confidence=draft.confidence,
        provider_key=draft.provider_key,
        provider_version=draft.provider_version,
        schema_version="1",
        source_path=draft.source_path,
        start_line=draft.start_line,
        end_line=draft.end_line,
        graph_node_id=draft.graph_node_id,
        attributes_json=dict(draft.attributes),
        is_canonical=False,
    )
    session.add(row)
    session.flush()
    for item in draft.evidence:
        session.add(
            SourceClaimEvidence(
                source_claim_id=row.id,
                evidence_kind=str(item.get("evidence_kind") or "source_span"),
                reference_path=str(item.get("reference_path") or draft.source_path or ""),
                start_line=item.get("start_line"),
                end_line=item.get("end_line"),
                excerpt=item.get("excerpt"),
                graph_node_id=item.get("graph_node_id"),
                graph_edge_id=item.get("graph_edge_id"),
                attributes_json=dict(item.get("attributes") or {}),
            )
        )
    session.commit()
    session.refresh(row)
    return row


def persist_claims(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
    scan_run_id: str | None,
    drafts: list[ClaimDraft],
) -> list[SourceClaim]:
    """Persist a worker batch without per-claim lookups or commits.

    The caller owns the transaction boundary.  Duplicate canonical keys retain
    ``persist_claim`` semantics: the first draft wins and later duplicates
    return that same row without adding duplicate evidence.
    """
    if not drafts:
        return []

    keys = [
        claim_canonical_key(draft.provider_key, draft.source_path or "", draft.claim_text, draft.start_line)
        for draft in drafts
    ]
    existing_by_key = {
        row.canonical_key: row
        for row in session.scalars(
            select(SourceClaim).where(
                SourceClaim.analysis_version_id == analysis_version_id,
                SourceClaim.canonical_key.in_(list(dict.fromkeys(keys))),
            )
        )
    }
    rows_by_key = dict(existing_by_key)
    created_by_key: dict[str, SourceClaim] = {}
    output: list[SourceClaim] = []
    for draft, key in zip(drafts, keys, strict=True):
        row = rows_by_key.get(key)
        if row is None:
            row = SourceClaim(
                project_id=project_id,
                analysis_version_id=analysis_version_id,
                scan_run_id=scan_run_id,
                canonical_key=key,
                claim_text=draft.claim_text,
                actor=draft.actor,
                condition_text=draft.condition_text,
                action_text=draft.action_text,
                result_text=draft.result_text,
                exception_text=draft.exception_text,
                subject_text=draft.subject_text,
                state_transition=draft.state_transition,
                claim_role=draft.claim_role,
                status=SourceClaimStatus.CANDIDATE.value,
                confidence=draft.confidence,
                provider_key=draft.provider_key,
                provider_version=draft.provider_version,
                schema_version="1",
                source_path=draft.source_path,
                start_line=draft.start_line,
                end_line=draft.end_line,
                graph_node_id=draft.graph_node_id,
                attributes_json=dict(draft.attributes),
                is_canonical=False,
            )
            rows_by_key[key] = row
            created_by_key[key] = row
        output.append(row)

    if not created_by_key:
        return output
    session.add_all(created_by_key.values())
    session.flush()
    evidence_rows: list[SourceClaimEvidence] = []
    for draft, key in zip(drafts, keys, strict=True):
        row = created_by_key.get(key)
        if row is None:
            continue
        # Later duplicate drafts are represented by the same new row; only the
        # first draft contributes evidence, as in repeated persist_claim calls.
        created_by_key.pop(key)
        for item in draft.evidence:
            evidence_rows.append(
                SourceClaimEvidence(
                    source_claim_id=row.id,
                    evidence_kind=str(item.get("evidence_kind") or "source_span"),
                    reference_path=str(item.get("reference_path") or draft.source_path or ""),
                    start_line=item.get("start_line"),
                    end_line=item.get("end_line"),
                    excerpt=item.get("excerpt"),
                    graph_node_id=item.get("graph_node_id"),
                    graph_edge_id=item.get("graph_edge_id"),
                    attributes_json=dict(item.get("attributes") or {}),
                )
            )
    if evidence_rows:
        session.add_all(evidence_rows)
    session.flush()
    return output


_STRUCTURAL_PATTERN_KINDS = {
    "authorization_gate": (
        "Authorization gate detected",
        "caller lacks required role/permission",
        "deny or raise authorization error",
        0.55,
    ),
    "validation_failure": (
        "Validation failure path detected",
        "input fails validation",
        "reject request or raise validation error",
        0.5,
    ),
    "threshold": (
        "Threshold or limit check detected",
        "value crosses configured threshold",
        "enforce limit",
        0.48,
    ),
    "state_transition": (
        "State transition detected",
        "entity is in a prior state",
        "transition entity to a new state",
        0.5,
    ),
    "expiration": (
        "Expiration or retention check detected",
        "resource is expired or past retention",
        "deny access or purge resource",
        0.52,
    ),
    "role_restriction": (
        "Role restriction detected",
        "caller role is not allowed",
        "deny operation",
        0.53,
    ),
    "tenancy_check": (
        "Tenancy boundary check detected",
        "caller tenant does not match resource tenant",
        "deny cross-tenant access",
        0.54,
    ),
    "feature_flag": (
        "Feature flag gate detected",
        "feature flag is disabled for caller",
        "hide or deny feature",
        0.45,
    ),
}
_STRUCTURAL_NAME_HINTS = (
    ("can_", "authorization_gate"),
    ("require", "authorization_gate"),
    ("authorize", "authorization_gate"),
    ("permission", "role_restriction"),
    ("validate", "validation_failure"),
    ("threshold", "threshold"),
    ("limit", "threshold"),
    ("expire", "expiration"),
    ("retention", "expiration"),
    ("ttl", "expiration"),
    ("org_id", "tenancy_check"),
    ("tenant", "tenancy_check"),
    ("feature_flag", "feature_flag"),
    ("status =", "state_transition"),
    ("transition", "state_transition"),
)


def _structural_kind_for_node(node) -> str | None:
    kind = node.symbol_kind or ""
    attrs = node.attributes_json or {}
    if attrs.get("pattern"):
        kind = str(attrs["pattern"])
    if kind in _STRUCTURAL_PATTERN_KINDS:
        return kind
    lowered = (node.display_name or "").lower()
    for hint, mapped in _STRUCTURAL_NAME_HINTS:
        if hint in lowered:
            return mapped
    return None


def _structural_claim_draft(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
    node,
    kind: str,
) -> ClaimDraft:
    title, condition, action, confidence = _STRUCTURAL_PATTERN_KINDS[kind]
    edge_ids = [
        edge.id
        for edge in RepositoryFactory(session)
        .graph_edges()
        .list_for_node_limited(project_id, analysis_version_id, node.id, limit=20)
    ]
    return ClaimDraft(
        claim_text=f"{title} at {node.display_name}",
        provider_key="structural_graph",
        provider_version="1.0.0",
        claim_role=SourceClaimRole.IMPLEMENTATION.value,
        confidence=confidence,
        actor="system",
        condition_text=condition,
        action_text=action,
        subject_text=node.display_name,
        source_path=node.source_path,
        start_line=node.start_line,
        end_line=node.end_line,
        graph_node_id=node.id,
        evidence=[
            {
                "evidence_kind": "graph_node",
                "reference_path": node.source_path or "",
                "start_line": node.start_line,
                "end_line": node.end_line,
                "graph_node_id": node.id,
                "excerpt": node.display_name,
                "attributes": {"supporting_edge_ids": edge_ids},
            }
        ],
        attributes={
            "pattern": kind,
            "supporting_nodes": [node.id],
            "supporting_edges": edge_ids,
        },
    )


def extract_structural_claims_from_graph(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
) -> list[ClaimDraft]:
    """Generate structured claims from graph neighborhoods (deterministic)."""
    nodes = RepositoryFactory(session).graph_nodes().list_for_analysis(
        project_id, analysis_version_id
    )
    drafts: list[ClaimDraft] = []
    for node in nodes:
        kind = _structural_kind_for_node(node)
        if kind is None:
            continue
        drafts.append(
            _structural_claim_draft(
                session,
                project_id=project_id,
                analysis_version_id=analysis_version_id,
                node=node,
                kind=kind,
            )
        )
    return drafts


def migrate_heuristic_rules_to_claims(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
) -> int:
    """Read-through compatibility: map existing Rule candidates into claims without duplicating."""
    rules = (
        RepositoryFactory(session)
        .rules()
        .list_for_project_version_limited(project_id, analysis_version_id, limit=500)
    )
    created = 0
    for rule in rules:
        draft = ClaimDraft(
            claim_text=rule.name or "Heuristic candidate",
            provider_key="heuristic",
            provider_version="1.0.0",
            confidence=min(float(rule.confidence_score or 25.0) / 100.0, 0.45),
            source_path=None,
            evidence=[{"evidence_kind": "legacy_rule", "reference_path": "legacy", "excerpt": rule.id}],
            attributes={"legacy_rule_id": rule.id, "never_auto_canonical": True},
        )
        before = RepositoryFactory(session).source_claims_structured().count_for_analysis_version(
            analysis_version_id
        )
        persist_claim(
            session,
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            scan_run_id=None,
            draft=draft,
        )
        after = RepositoryFactory(session).source_claims_structured().count_for_analysis_version(
            analysis_version_id
        )
        created += max(0, after - before)
    return created
