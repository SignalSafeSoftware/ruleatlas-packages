"""Integration tests for AST accounting, reuse, retention, and integrity checks."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from ruleatlas_contracts.ast import AstLinkType
from ruleatlas_contracts.enums import AnalysisVersionStatus
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

import ruleatlas_persistence.models as _models  # noqa: F401
from ruleatlas_persistence.base import Base
from ruleatlas_persistence.models import (
    AnalysisVersion,
    AstDocument,
    AstNode,
    AstNodeLink,
    AstParseRun,
    AstPayload,
)
from ruleatlas_persistence.repositories import RepositoryFactory


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as value:
        yield value
        value.rollback()
    engine.dispose()


def _version(
    version_id: str,
    *,
    project_id: str = "project-1",
    status: AnalysisVersionStatus = AnalysisVersionStatus.SUPERSEDED,
    age_days: int = 60,
) -> AnalysisVersion:
    timestamp = datetime.now(UTC) - timedelta(days=age_days)
    return AnalysisVersion(
        id=version_id,
        project_id=project_id,
        version_number=int(version_id.rsplit("-", 1)[-1]),
        status=status,
        completed_at=timestamp,
        superseded_at=timestamp if status == AnalysisVersionStatus.SUPERSEDED else None,
        created_at=timestamp,
        updated_at=timestamp,
    )


def _parse_run(
    parse_run_id: str,
    analysis_version_id: str,
    *,
    project_id: str = "project-1",
) -> AstParseRun:
    return AstParseRun(
        id=parse_run_id,
        project_id=project_id,
        analysis_version_id=analysis_version_id,
        parser_key="tree_sitter",
        parser_version="0.26.0",
        status="succeeded",
    )


def _document(
    document_id: str,
    analysis_version_id: str,
    parse_run_id: str,
    *,
    project_id: str = "project-1",
    source_file_id: str | None = None,
    content_hash: str | None = None,
) -> AstDocument:
    return AstDocument(
        id=document_id,
        project_id=project_id,
        analysis_version_id=analysis_version_id,
        parse_run_id=parse_run_id,
        ast_payload_id=f"payload-{document_id}",
        source_file_id=source_file_id or f"file-{document_id}",
        document_key=f"src/{document_id}.py",
        source_path=f"src/{document_id}.py",
        language_key="python",
        parser_key="tree_sitter",
        parser_version="0.26.0",
        grammar_key="tree-sitter-python",
        grammar_version="0.25.0",
        content_hash=content_hash or f"sha256:{document_id}",
        status="succeeded",
        source_bytes=100,
        node_count=1,
        error_node_count=0,
    )


def _node(node_id: str, document_id: str) -> AstNode:
    return AstNode(
        id=node_id,
        ast_payload_id=f"payload-{document_id}",
        node_key=node_id,
        sibling_ordinal=0,
        raw_type="module",
        category="document",
        is_named=True,
        start_byte=0,
        end_byte=100,
        start_row=0,
        start_column=0,
        end_row=1,
        end_column=0,
    )


def _payload(
    document_id: str,
    *,
    project_id: str = "project-1",
    content_hash: str | None = None,
) -> AstPayload:
    return AstPayload(
        id=f"payload-{document_id}",
        project_id=project_id,
        document_key=f"src/{document_id}.py",
        content_hash=content_hash or f"sha256:{document_id}",
        language_key="python",
        parser_key="tree_sitter",
        parser_version="0.26.0",
        grammar_key="tree-sitter-python",
        grammar_version="0.25.0",
        source_bytes=100,
        node_count=1,
    )


def test_usage_counts_only_the_requested_project_and_version(session: Session) -> None:
    session.add_all(
        [
            _parse_run("parse-1", "analysis-1"),
            _payload("doc-1"),
            _document("doc-1", "analysis-1", "parse-1"),
            _node("node-1", "doc-1"),
            _parse_run("parse-other", "analysis-1", project_id="other-project"),
            _payload("doc-other", project_id="other-project"),
            _document(
                "doc-other",
                "analysis-1",
                "parse-other",
                project_id="other-project",
            ),
            _node("node-other", "doc-other"),
        ]
    )
    session.flush()

    usage = (
        RepositoryFactory(session)
        .ast_lifecycle()
        .usage_for_version(
            project_id="project-1",
            analysis_version_id="analysis-1",
        )
    )

    assert usage.parse_runs == 1
    assert usage.documents == 1
    assert usage.nodes == 1
    assert usage.error_nodes == 0
    assert usage.source_bytes == 100


def test_reuse_requires_exact_content_and_parser_identity(session: Session) -> None:
    compatible = _document(
        "doc-old",
        "analysis-1",
        "parse-1",
        source_file_id="file-shared",
        content_hash="sha256:same",
    )
    incompatible = _document(
        "doc-new",
        "analysis-2",
        "parse-2",
        source_file_id="file-shared",
        content_hash="sha256:changed",
    )
    session.add_all(
        [
            _parse_run("parse-1", "analysis-1"),
            _parse_run("parse-2", "analysis-2"),
            _payload("doc-old", content_hash="sha256:same"),
            _payload("doc-new", content_hash="sha256:changed"),
            compatible,
            incompatible,
        ]
    )
    session.flush()

    reusable = (
        RepositoryFactory(session)
        .ast_lifecycle()
        .find_reusable_document(
            project_id="project-1",
            source_file_id="file-shared",
            content_hash="sha256:same",
            parser_key="tree_sitter",
            parser_version="0.26.0",
            grammar_key="tree-sitter-python",
            grammar_version="0.25.0",
            excluding_analysis_version_id="analysis-2",
        )
    )

    assert reusable is compatible
    assert (
        RepositoryFactory(session)
        .ast_lifecycle()
        .find_reusable_document(
            project_id="project-1",
            source_file_id="file-shared",
            content_hash="sha256:same",
            parser_key="tree_sitter",
            parser_version="different",
            grammar_key="tree-sitter-python",
            grammar_version="0.25.0",
        )
        is None
    )


def test_expired_deletion_preserves_inbound_provenance_and_retained_versions(
    session: Session,
) -> None:
    session.add_all(
        [
            _version("analysis-1"),
            _version("analysis-2"),
            _version(
                "analysis-3",
                status=AnalysisVersionStatus.READY,
                age_days=0,
            ),
            _parse_run("parse-delete", "analysis-1"),
            _parse_run("parse-protected", "analysis-1"),
            _parse_run("parse-retained", "analysis-2"),
            _parse_run("parse-current", "analysis-3"),
            _payload("doc-delete"),
            _payload("doc-protected"),
            _payload("doc-retained"),
            _payload("doc-current"),
            _document("doc-delete", "analysis-1", "parse-delete"),
            _document("doc-protected", "analysis-1", "parse-protected"),
            _document("doc-retained", "analysis-2", "parse-retained"),
            _document("doc-current", "analysis-3", "parse-current"),
            _node("node-delete", "doc-delete"),
            _node("node-protected", "doc-protected"),
            _node("node-retained", "doc-retained"),
            _node("node-current", "doc-current"),
        ]
    )
    session.flush()
    session.add(
        AstNodeLink(
            id="provenance-link",
            ast_document_id="doc-current",
            ast_node_id="node-current",
            link_type=AstLinkType.REFERENCE.value,
            target_type=AstLinkType.REFERENCE.value,
            target_id="node-protected",
            target_ast_node_id="node-protected",
            resolution_type="resolved",
            resolver_key="test",
            resolver_version="1",
            confidence=1.0,
        )
    )
    session.flush()

    result = (
        RepositoryFactory(session)
        .ast_lifecycle()
        .delete_expired_versions(
            project_id="project-1",
            completed_before=datetime.now(UTC) - timedelta(days=30),
            retain_analysis_version_ids={"analysis-2"},
        )
    )

    assert result.expired_analysis_version_ids == ["analysis-1"]
    assert result.protected_document_ids == []
    assert result.documents_deleted == 2
    assert result.nodes_deleted == 1
    assert result.parse_runs_deleted == 2
    assert session.get(AstDocument, "doc-delete") is None
    assert session.get(AstDocument, "doc-protected") is None
    assert session.get(AstNode, "node-protected") is not None
    assert session.get(AstDocument, "doc-retained") is not None
    assert session.get(AstNodeLink, "provenance-link") is not None

    session.rollback()
    assert session.scalar(select(func.count()).select_from(AstDocument)) == 0


def test_orphan_report_is_scoped_bounded_and_detects_missing_typed_target(
    session: Session,
) -> None:
    session.add_all(
        [
            _parse_run("parse-1", "analysis-1"),
            _payload("doc-1"),
            _document("doc-1", "analysis-1", "parse-1"),
            _node("node-1", "doc-1"),
        ]
    )
    session.flush()
    session.add(
        AstNodeLink(
            id="orphan-link",
            ast_document_id="doc-1",
            ast_node_id="node-1",
            link_type=AstLinkType.REFERENCE.value,
            target_type=AstLinkType.REFERENCE.value,
            target_id="missing-node",
            target_ast_node_id="missing-node",
            resolution_type="unresolved",
            resolver_key="test",
            resolver_version="1",
            confidence=0.5,
        )
    )
    session.flush()
    lifecycle = RepositoryFactory(session).ast_lifecycle()

    report = lifecycle.report_orphaned_links(
        project_id="project-1",
        analysis_version_id="analysis-1",
    )

    assert [(item.link_id, item.target_id) for item in report] == [("orphan-link", "missing-node")]
    assert (
        lifecycle.report_orphaned_links(
            project_id="other-project",
            analysis_version_id="analysis-1",
        )
        == []
    )
    with pytest.raises(ValueError, match="limit must be between"):
        lifecycle.report_orphaned_links(
            project_id="project-1",
            analysis_version_id="analysis-1",
            limit=0,
        )
