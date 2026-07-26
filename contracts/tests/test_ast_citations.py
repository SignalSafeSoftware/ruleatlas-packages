"""Tests for versioned AST and exact-source citations."""

from __future__ import annotations

import pytest

from ruleatlas_contracts.ast import (
    AstCitationKind,
    AstCitationScope,
    AstCitationValidationCode,
    AstCitationValidationIssue,
    AstCitationValidationResult,
    AstNodeCitation,
    AstPoint,
    AstSourceRange,
    ExactSourceCitation,
    ParserIdentity,
)


@pytest.fixture
def scope() -> AstCitationScope:
    return AstCitationScope(project_id="project-1", analysis_version_id="analysis-1")


@pytest.fixture
def source_range() -> AstSourceRange:
    return AstSourceRange(10, 24, AstPoint(2, 4), AstPoint(2, 18))


@pytest.fixture
def parser() -> ParserIdentity:
    return ParserIdentity(
        parser_key="tree_sitter",
        parser_version="0.26.0",
        language_key="python",
        grammar_key="tree-sitter-python",
        grammar_version="0.25.0",
    )


def test_scope_requires_project_and_analysis_version() -> None:
    with pytest.raises(ValueError, match="project_id"):
        AstCitationScope(project_id=" ", analysis_version_id="analysis-1")
    with pytest.raises(ValueError, match="analysis_version_id"):
        AstCitationScope(project_id="project-1", analysis_version_id="")


def test_exact_source_citation_serializes_stable_identity(
    scope: AstCitationScope,
    source_range: AstSourceRange,
) -> None:
    citation = ExactSourceCitation(
        scope=scope,
        source_file_id="file-1",
        source_path="src/auth.py",
        content_hash="sha256:source",
        source_range=source_range,
        excerpt_hash="sha256:excerpt",
    )

    payload = citation.to_dict()
    assert citation.kind == AstCitationKind.SOURCE_RANGE
    assert payload["scope"] == {
        "project_id": "project-1",
        "analysis_version_id": "analysis-1",
    }
    assert payload["source_range"] == source_range.to_dict()


def test_ast_node_citation_converts_to_exact_source(
    scope: AstCitationScope,
    source_range: AstSourceRange,
    parser: ParserIdentity,
) -> None:
    citation = AstNodeCitation(
        scope=scope,
        document_key="doc-1",
        node_key="node-7",
        source_file_id="file-1",
        source_path="src/auth.py",
        content_hash="sha256:source",
        subtree_hash="sha256:subtree",
        source_range=source_range,
        parser=parser,
        raw_node_type="if_statement",
        field_name="condition",
    )

    exact = citation.to_source_citation(excerpt_hash="sha256:excerpt")
    assert citation.kind == AstCitationKind.AST_NODE
    assert exact.scope == citation.scope
    assert exact.source_range == citation.source_range
    assert exact.excerpt_hash == "sha256:excerpt"
    assert citation.to_dict()["parser"] == parser.to_dict()


@pytest.mark.parametrize(
    "field_name",
    [
        "document_key",
        "node_key",
        "source_file_id",
        "source_path",
        "content_hash",
        "subtree_hash",
        "raw_node_type",
    ],
)
def test_ast_node_citation_rejects_blank_identity(
    field_name: str,
    scope: AstCitationScope,
    source_range: AstSourceRange,
    parser: ParserIdentity,
) -> None:
    values = {
        "scope": scope,
        "document_key": "doc-1",
        "node_key": "node-7",
        "source_file_id": "file-1",
        "source_path": "src/auth.py",
        "content_hash": "sha256:source",
        "subtree_hash": "sha256:subtree",
        "source_range": source_range,
        "parser": parser,
        "raw_node_type": "if_statement",
    }
    values[field_name] = " "

    with pytest.raises(ValueError, match=field_name):
        AstNodeCitation(**values)


def test_valid_result_has_stable_code() -> None:
    result = AstCitationValidationResult()
    assert result.valid
    assert result.code == AstCitationValidationCode.VALID
    assert result.to_dict() == {
        "valid": True,
        "code": "valid",
        "issues": [],
        "warnings": [],
    }


def test_invalid_result_uses_first_issue_as_primary_code() -> None:
    mismatch = AstCitationValidationIssue(
        code=AstCitationValidationCode.CONTENT_HASH_MISMATCH,
        message="Source content changed",
        field_name="content_hash",
    )
    stale = AstCitationValidationIssue(
        code=AstCitationValidationCode.STALE,
        message="Citation targets a stale document",
    )
    result = AstCitationValidationResult(issues=(mismatch, stale))

    assert not result.valid
    assert result.code == AstCitationValidationCode.CONTENT_HASH_MISMATCH
    assert result.to_dict()["issues"][0]["field_name"] == "content_hash"


def test_valid_code_cannot_be_used_as_an_issue() -> None:
    with pytest.raises(ValueError, match="not an issue"):
        AstCitationValidationIssue(
            code=AstCitationValidationCode.VALID,
            message="This should not be represented as an issue",
        )
