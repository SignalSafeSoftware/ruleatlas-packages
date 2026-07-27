"""Metadata and constraint tests for versioned AST persistence models."""

from __future__ import annotations

from typing import cast

from sqlalchemy import Table, create_engine, inspect

import ruleatlas_persistence.models as _models  # noqa: F401
from ruleatlas_persistence.base import Base
from ruleatlas_persistence.models import AstDocument, AstNode, AstNodeLink, AstParseRun, AstPayload


def test_ast_models_are_exported() -> None:
    assert AstParseRun.__tablename__ == "ast_parse_runs"
    assert AstPayload.__tablename__ == "ast_payloads"
    assert AstDocument.__tablename__ == "ast_documents"
    assert AstNode.__tablename__ == "ast_nodes"
    assert AstNodeLink.__tablename__ == "ast_node_links"


def test_ast_tables_have_expected_scope_and_navigation_columns() -> None:
    parse_run = Base.metadata.tables["ast_parse_runs"]
    document = Base.metadata.tables["ast_documents"]
    node = Base.metadata.tables["ast_nodes"]
    link = Base.metadata.tables["ast_node_links"]

    assert {"project_id", "analysis_version_id", "scan_run_id"} <= set(parse_run.columns.keys())
    assert {
        "project_id",
        "analysis_version_id",
        "source_file_id",
        "parse_run_id",
        "ast_payload_id",
        "root_node_id",
    } <= set(document.columns.keys())
    assert {
        "ast_payload_id",
        "parent_node_id",
        "sibling_ordinal",
        "start_byte",
        "end_byte",
        "subtree_hash",
    } <= set(node.columns.keys())
    assert {
        "ast_document_id",
        "ast_node_id",
        "graph_node_id",
        "source_symbol_id",
        "rule_evidence_id",
        "target_ast_node_id",
        "target_type",
        "target_id",
    } <= set(link.columns.keys())


def test_ast_uniqueness_and_check_constraints_are_declared() -> None:
    document_names = {
        constraint.name
        for constraint in cast(Table, AstDocument.__table__).constraints
    }
    node_names = {
        constraint.name for constraint in cast(Table, AstNode.__table__).constraints
    }
    link_names = {
        constraint.name
        for constraint in cast(Table, AstNodeLink.__table__).constraints
    }

    assert "uq_ast_documents_analysis_source_file" in document_names
    assert "uq_ast_documents_analysis_key" in document_names
    assert "uq_ast_nodes_payload_key" in node_names
    assert "uq_ast_nodes_payload_parent_ordinal" in node_names
    assert "ck_ast_node_links_at_most_one_typed_target" in link_names
    assert "ck_ast_node_links_confidence" in link_names


def test_ast_schema_creates_in_sqlite_with_indexes() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)

    assert {
        "ast_parse_runs",
        "ast_payloads",
        "ast_documents",
        "ast_nodes",
        "ast_node_links",
    } <= set(inspector.get_table_names())
    node_indexes = {index["name"] for index in inspector.get_indexes("ast_nodes")}
    assert "ix_ast_nodes_payload_parent_ordinal" not in node_indexes
    assert "ix_ast_nodes_payload_range" in node_indexes
    engine.dispose()
