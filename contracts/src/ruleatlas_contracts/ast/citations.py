"""Versioned AST and source citation contracts.

Citations carry enough immutable identity for an application service to verify that a model
referenced the expected project, analysis version, source document, parser output, and exact source
range. Database existence and authorization checks remain outside this dependency-free package.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from ruleatlas_contracts.ast.primitives import AstSourceRange, ParserIdentity


def _require_non_blank(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")


def _require_optional_non_blank(value: str | None, field_name: str) -> None:
    if value is not None:
        _require_non_blank(value, field_name)


class AstCitationKind(StrEnum):
    """Evidence identity represented by a citation."""

    AST_NODE = "ast_node"
    SOURCE_RANGE = "source_range"


class AstCitationValidationCode(StrEnum):
    """Stable result codes produced while validating persisted citations."""

    VALID = "valid"
    MALFORMED = "malformed"
    NOT_FOUND = "not_found"
    PROJECT_MISMATCH = "project_mismatch"
    ANALYSIS_VERSION_MISMATCH = "analysis_version_mismatch"
    SOURCE_FILE_MISMATCH = "source_file_mismatch"
    SOURCE_PATH_MISMATCH = "source_path_mismatch"
    DOCUMENT_MISMATCH = "document_mismatch"
    NODE_MISMATCH = "node_mismatch"
    PARSER_MISMATCH = "parser_mismatch"
    CONTENT_HASH_MISMATCH = "content_hash_mismatch"
    SUBTREE_HASH_MISMATCH = "subtree_hash_mismatch"
    RANGE_MISMATCH = "range_mismatch"
    STALE = "stale"
    UNAUTHORIZED = "unauthorized"


@dataclass(frozen=True)
class AstCitationScope:
    """Tenant and analysis-version boundary for a citation."""

    project_id: str
    analysis_version_id: str

    def __post_init__(self) -> None:
        _require_non_blank(self.project_id, "project_id")
        _require_non_blank(self.analysis_version_id, "analysis_version_id")

    def to_dict(self) -> dict[str, str]:
        return {
            "project_id": self.project_id,
            "analysis_version_id": self.analysis_version_id,
        }


@dataclass(frozen=True)
class ExactSourceCitation:
    """Citation to an immutable range in a retained source document."""

    scope: AstCitationScope
    source_file_id: str
    source_path: str
    content_hash: str
    source_range: AstSourceRange
    excerpt_hash: str | None = None

    def __post_init__(self) -> None:
        _require_non_blank(self.source_file_id, "source_file_id")
        _require_non_blank(self.source_path, "source_path")
        _require_non_blank(self.content_hash, "content_hash")
        _require_optional_non_blank(self.excerpt_hash, "excerpt_hash")

    @property
    def kind(self) -> AstCitationKind:
        return AstCitationKind.SOURCE_RANGE

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "scope": self.scope.to_dict(),
            "source_file_id": self.source_file_id,
            "source_path": self.source_path,
            "content_hash": self.content_hash,
            "source_range": self.source_range.to_dict(),
            "excerpt_hash": self.excerpt_hash,
        }


@dataclass(frozen=True)
class AstNodeCitation:
    """Citation to one persisted AST node and its exact source range."""

    scope: AstCitationScope
    document_key: str
    node_key: str
    source_file_id: str
    source_path: str
    content_hash: str
    subtree_hash: str
    source_range: AstSourceRange
    parser: ParserIdentity
    raw_node_type: str
    field_name: str | None = None

    def __post_init__(self) -> None:
        required = {
            "document_key": self.document_key,
            "node_key": self.node_key,
            "source_file_id": self.source_file_id,
            "source_path": self.source_path,
            "content_hash": self.content_hash,
            "subtree_hash": self.subtree_hash,
            "raw_node_type": self.raw_node_type,
        }
        for field_name, value in required.items():
            _require_non_blank(value, field_name)
        _require_optional_non_blank(self.field_name, "field_name")

    @property
    def kind(self) -> AstCitationKind:
        return AstCitationKind.AST_NODE

    def to_source_citation(self, *, excerpt_hash: str | None = None) -> ExactSourceCitation:
        return ExactSourceCitation(
            scope=self.scope,
            source_file_id=self.source_file_id,
            source_path=self.source_path,
            content_hash=self.content_hash,
            source_range=self.source_range,
            excerpt_hash=excerpt_hash,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "scope": self.scope.to_dict(),
            "document_key": self.document_key,
            "node_key": self.node_key,
            "source_file_id": self.source_file_id,
            "source_path": self.source_path,
            "content_hash": self.content_hash,
            "subtree_hash": self.subtree_hash,
            "source_range": self.source_range.to_dict(),
            "parser": self.parser.to_dict(),
            "raw_node_type": self.raw_node_type,
            "field_name": self.field_name,
        }


@dataclass(frozen=True)
class AstCitationValidationIssue:
    """One machine-readable citation validation failure or warning."""

    code: AstCitationValidationCode
    message: str
    field_name: str | None = None

    def __post_init__(self) -> None:
        _require_non_blank(self.message, "message")
        _require_optional_non_blank(self.field_name, "field_name")
        if self.code == AstCitationValidationCode.VALID:
            raise ValueError("VALID is not an issue code")

    def to_dict(self) -> dict[str, str | None]:
        return {
            "code": self.code.value,
            "message": self.message,
            "field_name": self.field_name,
        }


@dataclass(frozen=True)
class AstCitationValidationResult:
    """Validation outcome without database or authorization dependencies."""

    issues: tuple[AstCitationValidationIssue, ...] = field(default_factory=tuple)
    warnings: tuple[AstCitationValidationIssue, ...] = field(default_factory=tuple)

    @property
    def valid(self) -> bool:
        return not self.issues

    @property
    def code(self) -> AstCitationValidationCode:
        return AstCitationValidationCode.VALID if self.valid else self.issues[0].code

    def to_dict(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "code": self.code.value,
            "issues": [issue.to_dict() for issue in self.issues],
            "warnings": [warning.to_dict() for warning in self.warnings],
        }


__all__ = [
    "AstCitationKind",
    "AstCitationScope",
    "AstCitationValidationCode",
    "AstCitationValidationIssue",
    "AstCitationValidationResult",
    "AstNodeCitation",
    "ExactSourceCitation",
]
