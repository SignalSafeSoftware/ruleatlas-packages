"""Canonical keys and graph persistence/query helpers."""

from __future__ import annotations

import hashlib

from ruleatlas_contracts.enums import GraphObservationKind, GraphProviderStatus, GraphResolutionType
from ruleatlas_contracts.graph_contract import StructuralAnalysisResult
from ruleatlas_persistence.models import (
    GraphEdge,
    GraphNode,
    GraphObservation,
    GraphProviderRun,
)
from ruleatlas_persistence.repositories import RepositoryFactory
from sqlalchemy.orm import Session


def file_canonical_key(path: str) -> str:
    return f"file:{path.replace(chr(92), '/')}"


def symbol_canonical_key(path: str, name: str, *, start_line: int | None = None) -> str:
    suffix = f":{start_line}" if start_line is not None else ""
    return f"symbol:{path.replace(chr(92), '/')}:{name}{suffix}"


def edge_canonical_key(edge_type: str, from_key: str, to_key: str) -> str:
    return f"edge:{edge_type}:{from_key}->{to_key}"


def upsert_provider_result(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
    scan_run_id: str | None,
    result: StructuralAnalysisResult,
) -> GraphProviderRun:
    repositories = RepositoryFactory(session)
    raw_payload_hash = result.raw_payload_hash
    if raw_payload_hash is None:
        raw_payload_hash = hashlib.sha256(
            f"{result.provider_key}:{result.provider_version}:{result.status}".encode()
        ).hexdigest()
    run = repositories.graph_provider_runs().get_by_payload(
        project_id, analysis_version_id, result.provider_key, raw_payload_hash
    )
    if run is None:
        run = GraphProviderRun(
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            scan_run_id=scan_run_id,
            provider_key=result.provider_key,
            provider_version=result.provider_version,
            status=result.status,
            files_attempted=result.files_attempted,
            files_succeeded=result.files_succeeded,
            files_failed=result.files_failed,
            files_unsupported=result.files_unsupported,
            duration_ms=result.duration_ms,
            error_message=result.error_message,
            summary_json=dict(result.summary),
            raw_payload_hash=raw_payload_hash,
        )
        session.add(run)
        session.flush()
    else:
        # Idempotent re-import of identical payload.
        return run

    key_to_node: dict[str, GraphNode] = {}
    for item in result.nodes:
        existing = repositories.graph_nodes().get_by_canonical_key(
            analysis_version_id, item.canonical_key
        )
        if existing is None:
            existing = GraphNode(
                project_id=project_id,
                analysis_version_id=analysis_version_id,
                canonical_key=item.canonical_key,
                node_type=item.node_type,
                display_name=item.display_name,
                language_key=item.language_key,
                source_path=item.source_path,
                start_line=item.start_line,
                end_line=item.end_line,
                content_hash=item.content_hash,
                symbol_kind=item.symbol_kind,
                attributes_json=dict(item.attributes),
            )
            session.add(existing)
            session.flush()
        key_to_node[item.canonical_key] = existing
        _upsert_observation(
            session,
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            provider_run_id=run.id,
            kind=GraphObservationKind.NODE.value,
            provider_object_id=item.provider_object_id,
            node_id=existing.id,
            confidence=item.confidence,
            payload={"canonical_key": item.canonical_key, **item.attributes},
        )

    extracted = inferred = ambiguous = 0
    for edge in result.edges:
        from_node = key_to_node.get(edge.from_canonical_key)
        to_node = key_to_node.get(edge.to_canonical_key)
        if from_node is None or to_node is None:
            ambiguous += 1
            continue
        if edge.resolution_type == GraphResolutionType.INFERRED.value:
            inferred += 1
        elif edge.resolution_type == GraphResolutionType.AMBIGUOUS.value:
            ambiguous += 1
        else:
            extracted += 1
        existing_edge = repositories.graph_edges().get_by_analysis_and_canonical_key(
            analysis_version_id, edge.canonical_key
        )
        if existing_edge is None:
            existing_edge = GraphEdge(
                project_id=project_id,
                analysis_version_id=analysis_version_id,
                canonical_key=edge.canonical_key,
                edge_type=edge.edge_type,
                from_node_id=from_node.id,
                to_node_id=to_node.id,
                confidence=edge.confidence,
                resolution_type=edge.resolution_type,
                attributes_json=dict(edge.attributes),
            )
            session.add(existing_edge)
            session.flush()
        _upsert_observation(
            session,
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            provider_run_id=run.id,
            kind=GraphObservationKind.EDGE.value,
            provider_object_id=edge.provider_object_id,
            edge_id=existing_edge.id,
            confidence=edge.confidence,
            resolution_type=edge.resolution_type,
            payload={"canonical_key": edge.canonical_key, **edge.attributes},
        )

    run.nodes_count = len(result.nodes)
    run.edges_count = len(result.edges)
    run.extracted_edges = extracted
    run.inferred_edges = inferred
    run.ambiguous_edges = ambiguous
    if result.status == GraphProviderStatus.FAILED.value:
        run.status = GraphProviderStatus.FAILED.value
    elif ambiguous or result.files_failed:
        run.status = GraphProviderStatus.DEGRADED.value if result.nodes else GraphProviderStatus.PARTIAL.value
    else:
        run.status = result.status or GraphProviderStatus.SUCCEEDED.value
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def _upsert_observation(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
    provider_run_id: str,
    kind: str,
    provider_object_id: str,
    confidence: float,
    payload: dict,
    node_id: str | None = None,
    edge_id: str | None = None,
    resolution_type: str = GraphResolutionType.EXTRACTED.value,
) -> GraphObservation:
    existing = RepositoryFactory(session).graph_observations().get_for_provider_object(
        provider_run_id, provider_object_id, kind
    )
    if existing is not None:
        return existing
    row = GraphObservation(
        project_id=project_id,
        analysis_version_id=analysis_version_id,
        provider_run_id=provider_run_id,
        observation_kind=kind,
        provider_object_id=provider_object_id,
        node_id=node_id,
        edge_id=edge_id,
        confidence=confidence,
        resolution_type=resolution_type,
        raw_payload_json=payload,
    )
    session.add(row)
    session.flush()
    return row


def get_node(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
    node_id: str,
) -> GraphNode | None:
    return RepositoryFactory(session).graph_nodes().get_for_analysis(
        project_id, analysis_version_id, node_id
    )


def neighbors(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
    node_id: str,
    depth: int = 1,
    max_nodes: int = 50,
    edge_types: list[str] | None = None,
) -> dict:
    depth = max(1, min(depth, 3))
    max_nodes = max(1, min(max_nodes, 200))
    visited: set[str] = {node_id}
    frontier = [node_id]
    edges_out: list[GraphEdge] = []
    for _ in range(depth):
        if not frontier or len(visited) >= max_nodes:
            break
        batch = (
            RepositoryFactory(session)
            .graph_edges()
            .list_incident_limited(
                project_id,
                analysis_version_id,
                frontier,
                edge_types=edge_types,
                limit=max_nodes * 4,
            )
        )
        next_frontier: list[str] = []
        for edge in batch:
            edges_out.append(edge)
            for candidate in (edge.from_node_id, edge.to_node_id):
                if candidate not in visited and len(visited) < max_nodes:
                    visited.add(candidate)
                    next_frontier.append(candidate)
        frontier = next_frontier
    nodes = RepositoryFactory(session).graph_nodes().list_by_ids(
        project_id, analysis_version_id, list(visited)
    )
    return {
        "nodes": [_node_dict(n) for n in nodes],
        "edges": [_edge_dict(e) for e in edges_out],
        "limits": {"depth": depth, "max_nodes": max_nodes},
    }


def _node_dict(node: GraphNode) -> dict:
    return {
        "id": node.id,
        "canonical_key": node.canonical_key,
        "node_type": node.node_type,
        "display_name": node.display_name,
        "language_key": node.language_key,
        "source_path": node.source_path,
        "start_line": node.start_line,
        "end_line": node.end_line,
        "content_hash": node.content_hash,
        "symbol_kind": node.symbol_kind,
        "attributes": node.attributes_json,
    }


def _edge_dict(edge: GraphEdge) -> dict:
    return {
        "id": edge.id,
        "canonical_key": edge.canonical_key,
        "edge_type": edge.edge_type,
        "from_node_id": edge.from_node_id,
        "to_node_id": edge.to_node_id,
        "confidence": edge.confidence,
        "resolution_type": edge.resolution_type,
        "attributes": edge.attributes_json,
    }


def payload_hash(raw: bytes | str) -> str:
    data = raw.encode("utf-8") if isinstance(raw, str) else raw
    return hashlib.sha256(data).hexdigest()


def list_provider_runs(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
) -> list[dict]:
    rows = (
        RepositoryFactory(session)
        .graph_provider_runs()
        .list_for_analysis_ordered(project_id, analysis_version_id)
    )
    return [_run_dict(row) for row in rows]


def _run_dict(run: GraphProviderRun) -> dict:
    return {
        "id": run.id,
        "provider_key": run.provider_key,
        "provider_version": run.provider_version,
        "status": run.status,
        "files_attempted": run.files_attempted,
        "files_succeeded": run.files_succeeded,
        "files_failed": run.files_failed,
        "files_unsupported": run.files_unsupported,
        "nodes_count": run.nodes_count,
        "edges_count": run.edges_count,
        "extracted_edges": run.extracted_edges,
        "inferred_edges": run.inferred_edges,
        "ambiguous_edges": run.ambiguous_edges,
        "duration_ms": run.duration_ms,
        "error_message": run.error_message,
        "summary": run.summary_json,
        "raw_payload_hash": run.raw_payload_hash,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


def find_path(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
    from_node_id: str,
    to_node_id: str,
    max_depth: int = 3,
    max_nodes: int = 100,
) -> dict:
    """BFS path search with hard caps (depth ≤3, nodes ≤200)."""
    max_depth = max(1, min(max_depth, 3))
    max_nodes = max(1, min(max_nodes, 200))
    if from_node_id == to_node_id:
        node = get_node(
            session,
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            node_id=from_node_id,
        )
        return {
            "found": node is not None,
            "node_ids": [from_node_id] if node else [],
            "edge_ids": [],
            "limits": {"max_depth": max_depth, "max_nodes": max_nodes},
        }
    parent: dict[str, tuple[str, str]] = {}
    visited = {from_node_id}
    frontier = [from_node_id]
    found = False
    for _ in range(max_depth):
        if not frontier or len(visited) >= max_nodes:
            break
        next_frontier: list[str] = []
        edges = (
            RepositoryFactory(session)
            .graph_edges()
            .list_incident_limited(
                project_id,
                analysis_version_id,
                frontier,
                limit=max_nodes * 4,
            )
        )
        for edge in edges:
            for a, b in ((edge.from_node_id, edge.to_node_id), (edge.to_node_id, edge.from_node_id)):
                if a not in visited and b in visited:
                    continue
                if a in visited and b not in visited:
                    visited.add(b)
                    parent[b] = (a, edge.id)
                    next_frontier.append(b)
                    if b == to_node_id:
                        found = True
                        break
            if found:
                break
        if found:
            break
        frontier = next_frontier
    if not found:
        return {
            "found": False,
            "node_ids": [],
            "edge_ids": [],
            "limits": {"max_depth": max_depth, "max_nodes": max_nodes},
        }
    node_ids = [to_node_id]
    edge_ids: list[str] = []
    cur = to_node_id
    while cur != from_node_id:
        prev, edge_id = parent[cur]
        edge_ids.append(edge_id)
        node_ids.append(prev)
        cur = prev
    node_ids.reverse()
    edge_ids.reverse()
    return {
        "found": True,
        "node_ids": node_ids,
        "edge_ids": edge_ids,
        "limits": {"max_depth": max_depth, "max_nodes": max_nodes},
    }


def related_tests(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
    node_id: str,
    max_nodes: int = 50,
) -> dict:
    from ruleatlas_contracts.enums import GraphEdgeType, GraphNodeType

    hop = neighbors(
        session,
        project_id=project_id,
        analysis_version_id=analysis_version_id,
        node_id=node_id,
        depth=2,
        max_nodes=max_nodes,
        edge_types=[GraphEdgeType.TESTS.value, GraphEdgeType.ASSERTS.value, GraphEdgeType.REFERENCES.value],
    )
    test_nodes = [
        n
        for n in hop["nodes"]
        if n["node_type"] in {GraphNodeType.TEST.value, GraphNodeType.BDD_SCENARIO.value}
        or (n.get("symbol_kind") or "").startswith("test")
    ]
    return {"nodes": test_nodes, "limits": hop["limits"]}


def related_evidence(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
    node_id: str,
) -> dict:
    observations = (
        RepositoryFactory(session)
        .graph_observations()
        .list_for_node_in_analysis(project_id, analysis_version_id, node_id, limit=100)
    )
    return {
        "observations": [
            {
                "id": row.id,
                "provider_run_id": row.provider_run_id,
                "observation_kind": row.observation_kind,
                "provider_object_id": row.provider_object_id,
                "confidence": row.confidence,
                "resolution_type": row.resolution_type,
                "payload": row.raw_payload_json,
            }
            for row in observations
        ]
    }


def compare_analysis_graphs(
    session: Session,
    *,
    project_id: str,
    left_analysis_version_id: str,
    right_analysis_version_id: str,
) -> dict:
    """Historical comparison by canonical keys (counts only; immutable snapshots)."""
    repositories = RepositoryFactory(session)
    left_keys = set(
        repositories.graph_nodes().list_canonical_keys(project_id, left_analysis_version_id)
    )
    right_keys = set(
        repositories.graph_nodes().list_canonical_keys(project_id, right_analysis_version_id)
    )
    return {
        "left_only": len(left_keys - right_keys),
        "right_only": len(right_keys - left_keys),
        "shared": len(left_keys & right_keys),
        "left_total": len(left_keys),
        "right_total": len(right_keys),
    }
