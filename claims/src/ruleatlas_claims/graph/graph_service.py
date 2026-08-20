"""Canonical keys and graph persistence/query helpers."""

from __future__ import annotations

import hashlib

from ruleatlas_contracts.enums import GraphObservationKind, GraphProviderStatus, GraphResolutionType
from ruleatlas_contracts.graph_contract import NormalizedGraphEdge, StructuralAnalysisResult
from ruleatlas_persistence.models import (
    GraphEdge,
    GraphNode,
    GraphObservation,
    GraphProviderRun,
)
from ruleatlas_persistence.repositories import RepositoryFactory
from sqlalchemy import select
from sqlalchemy.orm import Session


def file_canonical_key(path: str) -> str:
    return f"file:{path.replace(chr(92), '/')}"


def symbol_canonical_key(path: str, name: str, *, start_line: int | None = None) -> str:
    suffix = f":{start_line}" if start_line is not None else ""
    return f"symbol:{path.replace(chr(92), '/')}:{name}{suffix}"


def edge_canonical_key(edge_type: str, from_key: str, to_key: str) -> str:
    return f"edge:{edge_type}:{from_key}->{to_key}"


def _provider_payload_hash(result: StructuralAnalysisResult) -> str:
    if result.raw_payload_hash is not None:
        return result.raw_payload_hash
    return hashlib.sha256(
        f"{result.provider_key}:{result.provider_version}:{result.status}".encode()
    ).hexdigest()


def _load_nodes_by_key(session: Session, analysis_version_id: str, keys: list[str]) -> dict[str, GraphNode]:
    if not keys:
        return {}
    return {
        node.canonical_key: node
        for node in session.scalars(
            select(GraphNode).where(
                GraphNode.analysis_version_id == analysis_version_id,
                GraphNode.canonical_key.in_(keys),
            )
        ).all()
    }


def _load_edges_by_key(session: Session, analysis_version_id: str, keys: list[str]) -> dict[str, GraphEdge]:
    if not keys:
        return {}
    return {
        edge.canonical_key: edge
        for edge in session.scalars(
            select(GraphEdge).where(
                GraphEdge.analysis_version_id == analysis_version_id,
                GraphEdge.canonical_key.in_(keys),
            )
        ).all()
    }


def _ensure_graph_nodes(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
    result: StructuralAnalysisResult,
) -> dict[str, GraphNode]:
    node_keys = list(dict.fromkeys(item.canonical_key for item in result.nodes))
    nodes_by_key = _load_nodes_by_key(session, analysis_version_id, node_keys)
    new_nodes: list[GraphNode] = []
    for item in result.nodes:
        if item.canonical_key in nodes_by_key:
            continue
        node = GraphNode(
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
        nodes_by_key[item.canonical_key] = node
        new_nodes.append(node)
    if new_nodes:
        session.add_all(new_nodes)
        session.flush()
    return nodes_by_key


def _count_resolution(edge: NormalizedGraphEdge) -> str:
    if edge.resolution_type == GraphResolutionType.INFERRED.value:
        return "inferred"
    if edge.resolution_type == GraphResolutionType.AMBIGUOUS.value:
        return "ambiguous"
    return "extracted"


def _ensure_graph_edges(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
    result: StructuralAnalysisResult,
    nodes_by_key: dict[str, GraphNode],
) -> tuple[int, int, int, list[tuple[NormalizedGraphEdge, GraphEdge]]]:
    extracted = inferred = ambiguous = 0
    edge_keys = list(dict.fromkeys(edge.canonical_key for edge in result.edges))
    edges_by_key = _load_edges_by_key(session, analysis_version_id, edge_keys)
    new_edges: list[GraphEdge] = []
    resolved_edges: list[tuple[NormalizedGraphEdge, GraphEdge]] = []
    for edge in result.edges:
        from_node = nodes_by_key.get(edge.from_canonical_key)
        to_node = nodes_by_key.get(edge.to_canonical_key)
        if from_node is None or to_node is None:
            ambiguous += 1
            continue
        bucket = _count_resolution(edge)
        extracted += int(bucket == "extracted")
        inferred += int(bucket == "inferred")
        ambiguous += int(bucket == "ambiguous")
        graph_edge = edges_by_key.get(edge.canonical_key)
        if graph_edge is None:
            graph_edge = GraphEdge(
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
            edges_by_key[edge.canonical_key] = graph_edge
            new_edges.append(graph_edge)
        resolved_edges.append((edge, graph_edge))
    if new_edges:
        session.add_all(new_edges)
        session.flush()
    return extracted, inferred, ambiguous, resolved_edges


def _queue_observation(
    observation_rows: list[GraphObservation],
    observation_keys: set[tuple[str, str]],
    *,
    project_id: str,
    analysis_version_id: str,
    run_id: str,
    kind: str,
    provider_object_id: str,
    confidence: float,
    payload: dict,
    node_id: str | None = None,
    edge_id: str | None = None,
    resolution_type: str = GraphResolutionType.EXTRACTED.value,
) -> None:
    observation_key = (kind, provider_object_id)
    if observation_key in observation_keys:
        return
    observation_keys.add(observation_key)
    observation_rows.append(
        GraphObservation(
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            provider_run_id=run_id,
            observation_kind=kind,
            provider_object_id=provider_object_id,
            node_id=node_id,
            edge_id=edge_id,
            confidence=confidence,
            resolution_type=resolution_type,
            raw_payload_json=payload,
        )
    )


def _finalize_provider_run(
    run: GraphProviderRun,
    result: StructuralAnalysisResult,
    *,
    extracted: int,
    inferred: int,
    ambiguous: int,
) -> None:
    run.nodes_count = len(result.nodes)
    run.edges_count = len(result.edges)
    run.extracted_edges = extracted
    run.inferred_edges = inferred
    run.ambiguous_edges = ambiguous
    if result.status == GraphProviderStatus.FAILED.value:
        run.status = GraphProviderStatus.FAILED.value
        return
    if ambiguous or result.files_failed:
        run.status = GraphProviderStatus.DEGRADED.value if result.nodes else GraphProviderStatus.PARTIAL.value
        return
    run.status = result.status or GraphProviderStatus.SUCCEEDED.value


def upsert_provider_result(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
    scan_run_id: str | None,
    result: StructuralAnalysisResult,
) -> GraphProviderRun:
    repositories = RepositoryFactory(session)
    raw_payload_hash = _provider_payload_hash(result)
    run = repositories.graph_provider_runs().get_by_payload(
        project_id, analysis_version_id, result.provider_key, raw_payload_hash
    )
    if run is not None:
        return run
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

    nodes_by_key = _ensure_graph_nodes(
        session,
        project_id=project_id,
        analysis_version_id=analysis_version_id,
        result=result,
    )
    extracted, inferred, ambiguous, resolved_edges = _ensure_graph_edges(
        session,
        project_id=project_id,
        analysis_version_id=analysis_version_id,
        result=result,
        nodes_by_key=nodes_by_key,
    )
    observation_rows: list[GraphObservation] = []
    observation_keys: set[tuple[str, str]] = set()
    for item in result.nodes:
        node = nodes_by_key[item.canonical_key]
        _queue_observation(
            observation_rows,
            observation_keys,
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            run_id=run.id,
            kind=GraphObservationKind.NODE.value,
            provider_object_id=item.provider_object_id,
            node_id=node.id,
            confidence=item.confidence,
            payload={"canonical_key": item.canonical_key, **item.attributes},
        )
    for edge, graph_edge in resolved_edges:
        _queue_observation(
            observation_rows,
            observation_keys,
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            run_id=run.id,
            kind=GraphObservationKind.EDGE.value,
            provider_object_id=edge.provider_object_id,
            edge_id=graph_edge.id,
            confidence=edge.confidence,
            resolution_type=edge.resolution_type,
            payload={"canonical_key": edge.canonical_key, **edge.attributes},
        )
    if observation_rows:
        session.add_all(observation_rows)
    _finalize_provider_run(run, result, extracted=extracted, inferred=inferred, ambiguous=ambiguous)
    session.add(run)
    session.commit()
    session.refresh(run)
    return run

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


def _path_payload(
    *,
    found: bool,
    node_ids: list[str],
    edge_ids: list[str],
    max_depth: int,
    max_nodes: int,
) -> dict:
    return {
        "found": found,
        "node_ids": node_ids,
        "edge_ids": edge_ids,
        "limits": {"max_depth": max_depth, "max_nodes": max_nodes},
    }


def _expand_path_frontier(
    edges,
    *,
    visited: set[str],
    parent: dict[str, tuple[str, str]],
    to_node_id: str,
) -> tuple[list[str], bool]:
    next_frontier: list[str] = []
    for edge in edges:
        for origin, destination in (
            (edge.from_node_id, edge.to_node_id),
            (edge.to_node_id, edge.from_node_id),
        ):
            if origin not in visited and destination in visited:
                continue
            if origin in visited and destination not in visited:
                visited.add(destination)
                parent[destination] = (origin, edge.id)
                next_frontier.append(destination)
                if destination == to_node_id:
                    return next_frontier, True
    return next_frontier, False


def _reconstruct_path(
    parent: dict[str, tuple[str, str]],
    from_node_id: str,
    to_node_id: str,
) -> tuple[list[str], list[str]]:
    node_ids = [to_node_id]
    edge_ids: list[str] = []
    current = to_node_id
    while current != from_node_id:
        previous, edge_id = parent[current]
        edge_ids.append(edge_id)
        node_ids.append(previous)
        current = previous
    node_ids.reverse()
    edge_ids.reverse()
    return node_ids, edge_ids


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
        return _path_payload(
            found=node is not None,
            node_ids=[from_node_id] if node else [],
            edge_ids=[],
            max_depth=max_depth,
            max_nodes=max_nodes,
        )
    parent: dict[str, tuple[str, str]] = {}
    visited = {from_node_id}
    frontier = [from_node_id]
    found = False
    for _ in range(max_depth):
        if not frontier or len(visited) >= max_nodes:
            break
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
        frontier, found = _expand_path_frontier(
            edges,
            visited=visited,
            parent=parent,
            to_node_id=to_node_id,
        )
        if found:
            break
    if not found:
        return _path_payload(
            found=False,
            node_ids=[],
            edge_ids=[],
            max_depth=max_depth,
            max_nodes=max_nodes,
        )
    node_ids, edge_ids = _reconstruct_path(parent, from_node_id, to_node_id)
    return _path_payload(
        found=True,
        node_ids=node_ids,
        edge_ids=edge_ids,
        max_depth=max_depth,
        max_nodes=max_nodes,
    )


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
