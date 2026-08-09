"""Regression coverage for graph-result persistence query volume."""

from __future__ import annotations

import ruleatlas_persistence.models  # noqa: F401
from ruleatlas_contracts.graph_contract import (
    NormalizedGraphEdge,
    NormalizedGraphNode,
    StructuralAnalysisResult,
)
from ruleatlas_persistence.base import Base
from ruleatlas_persistence.models import GraphEdge, GraphNode, GraphObservation
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from ruleatlas_claims.graph.graph_service import upsert_provider_result


def test_upsert_provider_result_prefetches_graph_rows_and_batches_observations() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    statements: list[str] = []

    def record_statement(conn, cursor, statement, parameters, context, executemany) -> None:
        del conn, cursor, parameters, context, executemany
        statements.append(statement)

    result = StructuralAnalysisResult(
        provider_key="test-provider",
        provider_version="1",
        status="succeeded",
        raw_payload_hash="test-payload",
        nodes=[
            NormalizedGraphNode(
                provider_object_id="node-a",
                canonical_key="symbol:billing:a",
                node_type="function",
                display_name="a",
            ),
            NormalizedGraphNode(
                provider_object_id="node-b",
                canonical_key="symbol:billing:b",
                node_type="function",
                display_name="b",
            ),
            NormalizedGraphNode(
                provider_object_id="node-c",
                canonical_key="symbol:billing:c",
                node_type="function",
                display_name="c",
            ),
        ],
        edges=[
            NormalizedGraphEdge(
                provider_object_id="edge-a-b",
                canonical_key="edge:calls:symbol:billing:a->symbol:billing:b",
                edge_type="calls",
                from_canonical_key="symbol:billing:a",
                to_canonical_key="symbol:billing:b",
            ),
            NormalizedGraphEdge(
                provider_object_id="edge-b-c",
                canonical_key="edge:calls:symbol:billing:b->symbol:billing:c",
                edge_type="calls",
                from_canonical_key="symbol:billing:b",
                to_canonical_key="symbol:billing:c",
            ),
        ],
    )
    try:
        event.listen(session.bind, "before_cursor_execute", record_statement)
        try:
            run = upsert_provider_result(
                session,
                project_id="project-id",
                analysis_version_id="analysis-id",
                scan_run_id=None,
                result=result,
            )
        finally:
            event.remove(session.bind, "before_cursor_execute", record_statement)

        assert run.nodes_count == 3
        assert run.edges_count == 2
        assert session.query(GraphNode).count() == 3
        assert session.query(GraphEdge).count() == 2
        assert session.query(GraphObservation).count() == 5
        selects = [
            statement.lower()
            for statement in statements
            if statement.lstrip().upper().startswith("SELECT")
        ]
        assert sum("from graph_nodes" in statement for statement in selects) == 1
        assert sum("from graph_edges" in statement for statement in selects) == 1
        assert not any("from graph_observations" in statement for statement in selects)
    finally:
        session.close()
        Base.metadata.drop_all(engine)
