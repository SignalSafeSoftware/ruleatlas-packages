"""Attachment and provenance helpers for canonical claim clusters."""

from __future__ import annotations

from ruleatlas_persistence.models import ClaimCluster, SourceClaim


def attach_cluster(
    cluster: ClaimCluster,
    primary: ClaimCluster,
    *,
    reason: str,
    kind: str,
) -> None:
    """Link a non-emitted cluster to its canonical cluster without losing evidence."""
    attributes = dict(cluster.attributes_json or {})
    attributes.update(
        attached_to_cluster_id=primary.id,
        suppression_reason=reason,
        attachment_kind=kind,
    )
    cluster.attributes_json = attributes

    primary_attributes = dict(primary.attributes_json or {})
    key = {
        "exception": "attached_exception_cluster_ids",
        "supporting": "attached_supporting_cluster_ids",
        "superseded": "attached_superseded_cluster_ids",
        "contradiction": "attached_contradiction_cluster_ids",
    }.get(kind, "attached_cluster_ids")
    linked = list(primary_attributes.get(key) or [])
    if cluster.id not in linked:
        linked.append(cluster.id)
    primary_attributes[key] = linked
    if kind == "superseded":
        primary_attributes["provenance_explanation"] = (
            primary_attributes.get("canonical_selection_reason")
            or primary.explanation
            or "Selected as canonical."
        ) + (
            " A legacy/outdated claim with conflicting timing or threshold was retained "
            "as superseded evidence."
        )
    primary.attributes_json = primary_attributes
    session_note = primary.explanation or primary_attributes.get("canonical_selection_reason")
    if kind == "superseded" and session_note and "superseded evidence" not in session_note:
        primary.explanation = (
            f"{session_note} A legacy document with conflicting timing was retained as superseded evidence."
        )


def fold_exception_into_primary(primary: ClaimCluster, claims: list[SourceClaim]) -> None:
    """Expose attached exception text on the primary cluster's proposal payload."""
    attributes = dict(primary.attributes_json or {})
    exception_ids = list(attributes.get("attached_exception_claim_ids") or [])
    texts = list(attributes.get("attached_exception_texts") or [])
    for claim in claims:
        if claim.id not in exception_ids:
            exception_ids.append(claim.id)
        snippet = claim.exception_text or claim.claim_text
        if snippet and snippet not in texts:
            texts.append(snippet)
    attributes["attached_exception_claim_ids"] = exception_ids
    attributes["attached_exception_texts"] = texts
    primary.attributes_json = attributes


def fold_supporting_into_primary(primary: ClaimCluster, claims: list[SourceClaim]) -> None:
    """Retain supporting evidence IDs on the canonical cluster."""
    attributes = dict(primary.attributes_json or {})
    ids = list(attributes.get("attached_supporting_claim_ids") or [])
    for claim in claims:
        if claim.id not in ids:
            ids.append(claim.id)
    attributes["attached_supporting_claim_ids"] = ids
    primary.attributes_json = attributes
