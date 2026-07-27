"""Integration tests for tenant-scoped, bounded AST read operations."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from ruleatlas_contracts.ast import AstLinkType, AstNodeCategory
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

import ruleatlas_persistence.models as _models  # noqa: F401
from ruleatlas_persistence.base import Base
from ruleatlas_persistence.models import AstDocument, AstNode, AstNodeLink, AstPayload
from ruleatlas_persistence.repositories import RepositoryFactory
from ruleatlas_persistence.repositories.ast_read_repository import AstNodeCursor


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as value:
        yield value
        value.rollback()
    engine.dispose()


def _document(
    *,
    document_id: str = "doc-1",
    project_id: str = "project-1",
    analysis_version_id: str = "analysis-1",
    source_file_id: str = "file-1",
) -> AstDocument:
    return AstDocument(
        id=document_id,
        project_id=project_id,
        analysis_version_id=analysis_version_id,
        parse_run_id=f"parse-{document_id}",
        ast_payload_id=f"payload-{document_id}",
        source_file_id=source_file_id,
        document_key=f"src/{document_id}.py",
        source_path=f"src/{document_id}.py",
        language_key="python",
        parser_key="tree_sitter",
        parser_version="0.26.0",
        grammar_key="tree-sitter-python",
        grammar_version="0.25.0",
        content_hash=f"sha256:{document_id}",
        status="succeeded",
        source_bytes=100,
    )


def _node(
    node_id: str,
    *,
    document_id: str = "doc-1",
    parent_id: str | None = None,
    ordinal: int = 0,
    raw_type: str = "expression",
    category: AstNodeCategory = AstNodeCategory.UNKNOWN,
    start_byte: int = 0,
    end_byte: int = 100,
) -> AstNode:
    return AstNode(
        id=node_id,
        ast_payload_id=f"payload-{document_id}",
        parent_node_id=parent_id,
        node_key=node_id,
        sibling_ordinal=ordinal,
        raw_type=raw_type,
        category=category.value,
        is_named=True,
        start_byte=start_byte,
        end_byte=end_byte,
        start_row=0,
        start_column=start_byte,
        end_row=0,
        end_column=end_byte,
    )


def _seed_tree(session: Session) -> None:
    session.add(
        AstPayload(
            id="payload-doc-1",
            project_id="project-1",
            document_key="src/doc-1.py",
            content_hash="sha256:doc-1",
            language_key="python",
            parser_key="tree_sitter",
            parser_version="0.26.0",
            grammar_key="tree-sitter-python",
            grammar_version="0.25.0",
            source_bytes=100,
        )
    )
    session.add(_document())
    session.add_all(
        [
            _node("root"),
            _node(
                "class",
                parent_id="root",
                ordinal=0,
                raw_type="class_definition",
                category=AstNodeCategory.CLASS_DEFINITION,
                start_byte=0,
                end_byte=60,
            ),
            _node(
                "function",
                parent_id="root",
                ordinal=1,
                raw_type="function_definition",
                category=AstNodeCategory.FUNCTION_DEFINITION,
                start_byte=60,
                end_byte=100,
            ),
            _node(
                "condition",
                parent_id="class",
                ordinal=0,
                raw_type="if_statement",
                category=AstNodeCategory.CONDITION,
                start_byte=10,
                end_byte=30,
            ),
            _node(
                "call",
                parent_id="condition",
                ordinal=0,
                raw_type="call",
                category=AstNodeCategory.CALL,
                start_byte=15,
                end_byte=20,
            ),
        ]
    )
    session.flush()


def test_document_and_node_lookups_require_exact_scope(session: Session) -> None:
    _seed_tree(session)
    queries = RepositoryFactory(session).ast_queries()

    assert (
        queries.get_document(
            project_id="project-1",
            analysis_version_id="analysis-1",
            document_id="doc-1",
        )
        is not None
    )
    assert (
        queries.get_document_for_source(
            project_id="project-1",
            analysis_version_id="analysis-1",
            source_file_id="file-1",
        )
        is not None
    )
    assert (
        queries.get_node(
            project_id="project-1",
            analysis_version_id="analysis-1",
            node_id="call",
        )
        is not None
    )
    assert (
        queries.get_node(
            project_id="other-project",
            analysis_version_id="analysis-1",
            node_id="call",
        )
        is None
    )
    assert (
        queries.get_node(
            project_id="project-1",
            analysis_version_id="other-analysis",
            node_id="call",
        )
        is None
    )


def test_children_use_stable_cursor_pagination(session: Session) -> None:
    _seed_tree(session)
    queries = RepositoryFactory(session).ast_queries()

    first = queries.list_children(
        project_id="project-1",
        analysis_version_id="analysis-1",
        parent_node_id="root",
        limit=1,
    )
    assert [node.id for node in first.items] == ["class"]
    assert first.next_cursor == AstNodeCursor(0, "class")

    second = queries.list_children(
        project_id="project-1",
        analysis_version_id="analysis-1",
        parent_node_id="root",
        limit=1,
        cursor=first.next_cursor,
    )
    assert [node.id for node in second.items] == ["function"]
    assert second.next_cursor is None


def test_bounded_subtree_respects_depth_node_limit_and_query_budget(session: Session) -> None:
    _seed_tree(session)
    queries = RepositoryFactory(session).ast_queries()
    select_count = 0

    def count_selects(_conn, _cursor, statement, _parameters, _context, _executemany) -> None:
        nonlocal select_count
        if statement.lstrip().upper().startswith("SELECT"):
            select_count += 1

    event.listen(session.get_bind(), "before_cursor_execute", count_selects)
    try:
        result = queries.bounded_subtree(
            project_id="project-1",
            analysis_version_id="analysis-1",
            root_node_id="root",
            max_depth=2,
            max_nodes=10,
        )
    finally:
        event.remove(session.get_bind(), "before_cursor_execute", count_selects)

    assert [(item.node.id, item.depth) for item in result.items] == [
        ("root", 0),
        ("class", 1),
        ("function", 1),
        ("condition", 2),
    ]
    assert result.truncated
    assert select_count == 3  # root plus one breadth query per requested depth

    limited = queries.bounded_subtree(
        project_id="project-1",
        analysis_version_id="analysis-1",
        root_node_id="root",
        max_depth=8,
        max_nodes=2,
    )
    assert len(limited.items) == 2
    assert limited.truncated


def test_structural_range_containing_and_definition_queries(session: Session) -> None:
    _seed_tree(session)
    queries = RepositoryFactory(session).ast_queries()

    matches = queries.search_nodes(
        project_id="project-1",
        analysis_version_id="analysis-1",
        document_id="doc-1",
        raw_types={"if_statement", "call"},
        start_byte=12,
        end_byte=18,
    )
    assert [node.id for node in matches] == ["condition", "call"]
    containing = queries.find_containing_node(
        project_id="project-1",
        analysis_version_id="analysis-1",
        document_id="doc-1",
        byte_offset=16,
    )
    assert containing is not None
    assert containing.id == "call"
    definitions = queries.list_definitions(
        project_id="project-1",
        analysis_version_id="analysis-1",
        document_id="doc-1",
    )
    assert [node.id for node in definitions] == ["class", "function"]


def test_parent_and_links_cannot_cross_scope(session: Session) -> None:
    _seed_tree(session)
    session.add(
        AstNodeLink(
            id="link-1",
            ast_document_id="doc-1",
            ast_node_id="call",
            link_type=AstLinkType.REFERENCE.value,
            target_type=AstLinkType.REFERENCE.value,
            target_id="class",
            target_ast_node_id="class",
            resolution_type="resolved",
            resolver_key="test",
            resolver_version="1",
            confidence=1.0,
        )
    )
    session.flush()
    queries = RepositoryFactory(session).ast_queries()

    parent = queries.get_parent(
        project_id="project-1",
        analysis_version_id="analysis-1",
        node_id="call",
    )
    assert parent is not None
    assert parent.id == "condition"
    assert [
        link.id
        for link in queries.list_links_for_node(
            project_id="project-1",
            analysis_version_id="analysis-1",
            node_id="call",
            link_types={AstLinkType.REFERENCE.value},
        )
    ] == ["link-1"]
    assert (
        queries.list_links_for_node(
            project_id="other-project",
            analysis_version_id="analysis-1",
            node_id="call",
        )
        == []
    )


@pytest.mark.parametrize(
    ("operation", "message"),
    [
        ("limit", "limit must be between"),
        ("depth", "max_depth must be between"),
        ("nodes", "max_nodes must be between"),
        ("range", "search range must be"),
    ],
)
def test_bounds_are_rejected(session: Session, operation: str, message: str) -> None:
    _seed_tree(session)
    queries = RepositoryFactory(session).ast_queries()
    with pytest.raises(ValueError, match=message):
        if operation == "limit":
            queries.search_nodes(project_id="project-1", analysis_version_id="analysis-1", limit=0)
        elif operation == "depth":
            queries.bounded_subtree(
                project_id="project-1",
                analysis_version_id="analysis-1",
                root_node_id="root",
                max_depth=33,
            )
        elif operation == "nodes":
            queries.bounded_subtree(
                project_id="project-1",
                analysis_version_id="analysis-1",
                root_node_id="root",
                max_nodes=0,
            )
        else:
            queries.search_nodes(
                project_id="project-1",
                analysis_version_id="analysis-1",
                start_byte=10,
                end_byte=10,
            )
