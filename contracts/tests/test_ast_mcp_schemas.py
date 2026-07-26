"""Tests for bounded, provider-neutral AST MCP schemas."""

from __future__ import annotations

from dataclasses import fields

import pytest

from ruleatlas_contracts.ast import (
    AstNodeCategory,
    AstNodeFlags,
    AstParseStatus,
    AstPoint,
    AstSourceRange,
    ParserIdentity,
)
from ruleatlas_contracts.ast_mcp import (
    MAX_PAGE_SIZE,
    MAX_SOURCE_EXCERPT_BYTES,
    MAX_SUBTREE_DEPTH,
    MAX_SUBTREE_NODES,
    AstCallDirection,
    AstMcpDocument,
    AstMcpFile,
    AstMcpNode,
    AstMcpPage,
    AstNodesResponse,
    FindAstCallsRequest,
    FindAstCallsResponse,
    FindAstNodesRequest,
    FindConditionsAssignmentsRequest,
    FindRelatedEvidenceRequest,
    FindRelatedEvidenceResponse,
    GetAstDocumentRequest,
    GetAstDocumentResponse,
    GetAstNodeRequest,
    GetAstNodeResponse,
    GetAstSubtreeRequest,
    GetSourceExcerptRequest,
    GetSourceExcerptResponse,
    GetSymbolAstRequest,
    ListAstChildrenRequest,
    ListAstFilesRequest,
    ListAstFilesResponse,
)


def _source_range() -> AstSourceRange:
    return AstSourceRange(0, 10, AstPoint(0, 0), AstPoint(0, 10))


def _file() -> AstMcpFile:
    return AstMcpFile(
        document_id="document-1",
        source_file_id="file-1",
        source_path="src/auth.py",
        language_key="python",
        content_hash="sha256:source",
        status=AstParseStatus.SUCCEEDED,
        source_bytes=10,
        node_count=1,
        error_node_count=0,
    )


def _node() -> AstMcpNode:
    return AstMcpNode(
        node_id="node-1",
        document_id="document-1",
        parent_node_id=None,
        raw_type="module",
        category=AstNodeCategory.DOCUMENT,
        source_range=_source_range(),
        flags=AstNodeFlags(is_named=True),
        sibling_ordinal=0,
    )


def test_requests_never_accept_trusted_scope_fields() -> None:
    request_types = (
        ListAstFilesRequest,
        GetAstDocumentRequest,
        FindAstNodesRequest,
        GetAstNodeRequest,
        ListAstChildrenRequest,
        GetAstSubtreeRequest,
        GetSymbolAstRequest,
        GetSourceExcerptRequest,
        FindAstCallsRequest,
        FindConditionsAssignmentsRequest,
        FindRelatedEvidenceRequest,
    )

    for request_type in request_types:
        field_names = {item.name for item in fields(request_type)}
        assert "project_id" not in field_names
        assert "organization_id" not in field_names
        assert "analysis_version_id" not in field_names


def test_every_list_request_supports_cursor_pagination() -> None:
    list_request_types = (
        ListAstFilesRequest,
        FindAstNodesRequest,
        ListAstChildrenRequest,
        GetAstSubtreeRequest,
        GetSymbolAstRequest,
        FindAstCallsRequest,
        FindConditionsAssignmentsRequest,
        FindRelatedEvidenceRequest,
    )

    for request_type in list_request_types:
        field_names = {item.name for item in fields(request_type)}
        assert {"cursor", "limit"} <= field_names


def test_every_response_reports_truncation() -> None:
    responses = (
        ListAstFilesResponse(),
        GetAstDocumentResponse(document=None),
        AstNodesResponse(),
        GetAstNodeResponse(node=None),
        GetSourceExcerptResponse(excerpt=None),
        FindAstCallsResponse(direction=AstCallDirection.CALLEES),
        FindRelatedEvidenceResponse(),
    )

    for response in responses:
        assert response.to_dict()["page"] == {
            "truncated": False,
            "next_cursor": None,
        }


def test_page_cursor_and_all_caller_limits_are_bounded() -> None:
    with pytest.raises(ValueError, match="next_cursor requires"):
        AstMcpPage(next_cursor="cursor-1")
    with pytest.raises(ValueError, match="limit must be between"):
        ListAstFilesRequest(limit=MAX_PAGE_SIZE + 1)
    with pytest.raises(ValueError, match="max_depth must be between"):
        GetAstSubtreeRequest(node_id="node-1", max_depth=MAX_SUBTREE_DEPTH + 1)
    with pytest.raises(ValueError, match="max_nodes must be between"):
        GetSymbolAstRequest(
            source_symbol_id="symbol-1",
            max_nodes=MAX_SUBTREE_NODES + 1,
        )
    with pytest.raises(ValueError, match="max_bytes must be between"):
        GetSourceExcerptRequest(
            document_id="document-1",
            start_byte=0,
            end_byte=1,
            max_bytes=MAX_SOURCE_EXCERPT_BYTES + 1,
        )


def test_document_selector_and_structural_filters_are_validated() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        GetAstDocumentRequest()
    with pytest.raises(ValueError, match="exactly one"):
        GetAstDocumentRequest(document_id="doc", source_file_id="file")
    with pytest.raises(ValueError, match="provided together"):
        FindAstNodesRequest(start_byte=0)
    with pytest.raises(ValueError, match="document_id or anchor_node_id"):
        FindConditionsAssignmentsRequest()
    with pytest.raises(ValueError, match="at least one evidence"):
        FindRelatedEvidenceRequest(
            node_id="node-1",
            include_tests=False,
            include_bdd=False,
        )


def test_serialization_is_deterministic_and_uses_wire_enum_values() -> None:
    document = AstMcpDocument(
        file=_file(),
        parser=ParserIdentity(
            parser_key="tree_sitter",
            parser_version="0.26.0",
            language_key="python",
            grammar_key="tree-sitter-python",
            grammar_version="0.25.0",
        ),
        root_node_id="node-1",
    )
    response = GetAstDocumentResponse(
        document=document,
        page=AstMcpPage(truncated=True, next_cursor="opaque"),
    )

    assert response.to_dict() == response.to_dict()
    assert response.to_dict()["document"] == document.to_dict()
    assert _file().to_dict()["status"] == "succeeded"
    assert _node().to_dict()["category"] == "document"


def test_request_serialization_contains_only_tool_arguments() -> None:
    request = FindAstCallsRequest(
        node_id="node-1",
        direction=AstCallDirection.CALLERS,
        cursor="opaque",
        limit=25,
    )

    assert request.to_dict() == {
        "cursor": "opaque",
        "limit": 25,
        "node_id": "node-1",
        "direction": "callers",
    }
