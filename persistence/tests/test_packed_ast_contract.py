"""Packed-only AST persistence contract tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from ruleatlas_contracts.ast import (
    AstDocumentRecord,
    AstLinkRecord,
    AstLinkType,
    AstNodeFlags,
    AstNodeRecord,
    AstParseRunRecord,
    AstParseStatus,
    AstPoint,
    AstResolutionType,
    AstSourceRange,
    ParserIdentity,
    ParserRuntimeIdentity,
)
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

import ruleatlas_persistence.models as _models  # noqa: F401
from ruleatlas_persistence.base import Base
from ruleatlas_persistence.models import AstDocument, AstNode, AstNodeLink, AstPayload, AstPayloadBlob
from ruleatlas_persistence.repositories import RepositoryFactory


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as value:
        yield value
        value.rollback()
    engine.dispose()


@pytest.fixture
def parser() -> ParserIdentity:
    return ParserIdentity(
        parser_key="tree_sitter",
        parser_version="0.26.0",
        language_key="python",
        grammar_key="tree-sitter-python",
        grammar_version="0.25.0",
    )


def _parse_run() -> AstParseRunRecord:
    return AstParseRunRecord(
        parse_run_id="parse-1",
        project_id="project-1",
        analysis_version_id="analysis-1",
        scan_run_id="scan-1",
        parser=ParserRuntimeIdentity("tree_sitter", "0.26.0"),
        status=AstParseStatus.RUNNING,
    )


def _document_record(parser: ParserIdentity) -> AstDocumentRecord:
    return AstDocumentRecord(
        document_key="src/auth.py:sha256:first",
        project_id="project-1",
        analysis_version_id="analysis-1",
        parse_run_id="parse-1",
        scan_run_id="scan-1",
        source_file_id="file-1",
        source_path="src/auth.py",
        parser=parser,
        content_hash="sha256:first",
        status=AstParseStatus.SUCCEEDED,
        source_bytes=24,
        node_count=2,
        root_node_key="root",
    )


def _records(document_key: str) -> list[AstNodeRecord]:
    return [
        AstNodeRecord(
            document_key=document_key,
            node_key="root",
            raw_type="module",
            source_range=AstSourceRange(0, 24, AstPoint(0, 0), AstPoint(1, 0)),
            flags=AstNodeFlags(is_named=True),
            sibling_ordinal=0,
            subtree_hash="sha256:root",
        ),
        AstNodeRecord(
            document_key=document_key,
            node_key="condition",
            parent_node_key="root",
            raw_type="if_statement",
            source_range=AstSourceRange(0, 23, AstPoint(0, 0), AstPoint(0, 23)),
            flags=AstNodeFlags(is_named=True),
            sibling_ordinal=0,
            field_name="body",
            subtree_hash="sha256:condition",
        ),
    ]


def _document(repositories: RepositoryFactory, parser: ParserIdentity) -> AstDocument:
    record = _document_record(parser)
    payload = repositories.ast_payloads().create_for_record(record)
    return repositories.ast_documents().create_from_record(record, ast_payload_id=payload.id)


def test_schema_contains_no_relational_node_projection() -> None:
    assert "ast_nodes" not in Base.metadata.tables
    assert not hasattr(AstPayload, "root_node_id")
    assert not hasattr(AstDocument, "root_node_id")
    assert not hasattr(AstNodeLink, "ast_node_id")
    assert not hasattr(AstNodeLink, "target_ast_node_id")
    assert hasattr(AstNode, "__dataclass_fields__")

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    assert "ast_nodes" not in inspector.get_table_names()
    columns = {column["name"] for column in inspector.get_columns("ast_node_links")}
    assert {"ast_document_id", "ast_node_key", "target_ast_document_id", "target_ast_node_key"} <= columns
    assert {"ast_node_id", "target_ast_node_id"}.isdisjoint(columns)
    engine.dispose()


def test_packed_writer_and_reader_keep_scoped_stable_node_identity(
    session: Session,
    parser: ParserIdentity,
) -> None:
    repositories = RepositoryFactory(session)
    repositories.ast_parse_runs().create_from_record(_parse_run())
    document = _document(repositories, parser)
    repositories.ast_nodes().persist_packed_for_document(document, _records(document.document_key))

    payload = session.get(AstPayload, document.ast_payload_id)
    blob = session.scalar(select(AstPayloadBlob).where(AstPayloadBlob.ast_payload_id == document.ast_payload_id))
    assert payload is not None
    assert blob is not None
    assert payload.root_node_key == document.root_node_key == "root"
    assert document.node_count == blob.node_count == 2

    queries = repositories.ast_queries()
    root_id = queries.packed_node_reference(document.document_key, "root")
    root = queries.get_node(
        project_id="project-1",
        analysis_version_id="analysis-1",
        node_id=root_id,
    )
    assert root is not None
    assert root.id == root_id
    assert queries.get_node(
        project_id="other-project",
        analysis_version_id="analysis-1",
        node_id=root_id,
    ) is None
    assert queries.get_node(
        project_id="project-1",
        analysis_version_id="analysis-1",
        node_id="legacy-uuid",
    ) is None
    children = queries.list_children(
        project_id="project-1",
        analysis_version_id="analysis-1",
        parent_node_id=root_id,
    )
    assert [node.node_key for node in children.items] == ["condition"]


def test_links_are_key_only_and_validate_packed_targets(session: Session, parser: ParserIdentity) -> None:
    repositories = RepositoryFactory(session)
    repositories.ast_parse_runs().create_from_record(_parse_run())
    document = _document(repositories, parser)
    repositories.ast_nodes().persist_packed_for_document(document, _records(document.document_key))
    links = [
        AstLinkRecord(
            document_key=document.document_key,
            source_node_key="condition",
            link_type=AstLinkType.CALL_TARGET,
            target_id="root",
            target_document_key=document.document_key,
            target_node_key="root",
            resolution_type=AstResolutionType.RESOLVED,
            resolver_key="test",
            resolver_version="1",
            confidence=0.9,
        )
    ]

    assert repositories.ast_node_links().bulk_create_for_document(document, links) == 1
    link = session.scalar(select(AstNodeLink))
    assert link is not None
    assert link.ast_node_key == "condition"
    assert link.target_ast_document_id == document.id
    assert link.target_ast_node_key == "root"
