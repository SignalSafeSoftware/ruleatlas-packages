"""Tests for normalized AST records and their invariants."""

from __future__ import annotations

import pytest

from ruleatlas_contracts.ast import (
    AstDocumentRecord,
    AstLinkRecord,
    AstLinkType,
    AstNodeFlags,
    AstNodeRecord,
    AstParseRunRecord,
    AstParseStatus,
    AstParseSummary,
    AstPoint,
    AstProviderCapability,
    AstResolutionType,
    AstSourceRange,
    ParserIdentity,
    ParserRuntimeIdentity,
)


@pytest.fixture
def parser() -> ParserRuntimeIdentity:
    return ParserRuntimeIdentity(
        parser_key="tree_sitter",
        parser_version="0.26.0",
    )


@pytest.fixture
def document_parser() -> ParserIdentity:
    return ParserIdentity(
        parser_key="tree_sitter",
        parser_version="0.26.0",
        language_key="python",
        grammar_key="tree-sitter-python",
        grammar_version="0.25.0",
    )


def test_provider_capability_requires_unique_languages(parser: ParserRuntimeIdentity) -> None:
    capability = AstProviderCapability(parser=parser, languages=("python", "typescript"))
    assert capability.to_dict()["languages"] == ["python", "typescript"]

    with pytest.raises(ValueError, match="duplicates"):
        AstProviderCapability(parser=parser, languages=("python", "python"))


def test_parse_summary_validates_counts() -> None:
    summary = AstParseSummary(
        files_attempted=3,
        files_succeeded=1,
        files_partial=1,
        files_reused=1,
        documents_created=2,
        nodes_created=12,
        error_nodes=1,
    )
    assert summary.files_completed == 3
    assert summary.to_dict()["nodes_created"] == 12

    with pytest.raises(ValueError, match="terminal file counts"):
        AstParseSummary(files_attempted=1, files_succeeded=1, files_failed=1)
    with pytest.raises(ValueError, match="error_nodes"):
        AstParseSummary(files_attempted=1, nodes_created=1, error_nodes=2)


def test_failed_parse_run_requires_error(parser: ParserRuntimeIdentity) -> None:
    with pytest.raises(ValueError, match="error_message"):
        AstParseRunRecord(
            parse_run_id="parse-1",
            project_id="project-1",
            analysis_version_id="analysis-1",
            parser=parser,
            status=AstParseStatus.FAILED,
        )


def test_document_requires_root_when_nodes_exist(document_parser: ParserIdentity) -> None:
    with pytest.raises(ValueError, match="root_node_key"):
        AstDocumentRecord(
            document_key="doc-1",
            project_id="project-1",
            analysis_version_id="analysis-1",
            parse_run_id="parse-1",
            source_file_id="file-1",
            source_path="src/auth.py",
            parser=document_parser,
            content_hash="sha256:abc",
            status=AstParseStatus.SUCCEEDED,
            source_bytes=100,
            node_count=3,
        )


def test_empty_unsupported_document_has_no_root(document_parser: ParserIdentity) -> None:
    document = AstDocumentRecord(
        document_key="doc-1",
        project_id="project-1",
        analysis_version_id="analysis-1",
        parse_run_id="parse-1",
        source_file_id="file-1",
        source_path="src/auth.unknown",
        parser=document_parser,
        content_hash="sha256:abc",
        status=AstParseStatus.UNSUPPORTED,
        source_bytes=100,
        node_count=0,
    )
    assert document.root_node_key is None


def test_node_identifies_root_and_rejects_self_parent() -> None:
    source_range = AstSourceRange(0, 10, AstPoint(0, 0), AstPoint(0, 10))
    root = AstNodeRecord(
        document_key="doc-1",
        node_key="node-1",
        raw_type="module",
        source_range=source_range,
        flags=AstNodeFlags(is_named=True),
        sibling_ordinal=0,
    )
    assert root.is_root

    parent_flags = AstNodeFlags(is_named=True)
    with pytest.raises(ValueError, match="own parent"):
        AstNodeRecord(
            document_key="doc-1",
            node_key="node-1",
            parent_node_key="node-1",
            raw_type="identifier",
            source_range=source_range,
            flags=parent_flags,
            sibling_ordinal=0,
        )


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_link_confidence_is_bounded(confidence: float) -> None:
    with pytest.raises(ValueError, match="confidence"):
        AstLinkRecord(
            document_key="doc-1",
            source_node_key="node-1",
            link_type=AstLinkType.GRAPH_NODE,
            target_id="graph-1",
            resolution_type=AstResolutionType.RESOLVED,
            resolver_key="symbol-linker",
            resolver_version="1",
            confidence=confidence,
        )


def test_link_preserves_resolution_strength() -> None:
    link = AstLinkRecord(
        document_key="doc-1",
        source_node_key="node-1",
        link_type=AstLinkType.CALL_TARGET,
        target_id="node-2",
        resolution_type=AstResolutionType.AMBIGUOUS,
        resolver_key="call-linker",
        resolver_version="1",
        confidence=0.4,
    )
    assert link.resolution_type == AstResolutionType.AMBIGUOUS
