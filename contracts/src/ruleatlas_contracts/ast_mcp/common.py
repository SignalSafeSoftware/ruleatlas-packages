"""Shared, transport-neutral values returned by AST MCP tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ruleatlas_contracts.ast import (
    AstLinkType,
    AstNodeCategory,
    AstNodeFlags,
    AstParseStatus,
    AstSourceRange,
    ParserIdentity,
)

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200
MAX_SOURCE_EXCERPT_BYTES = 32_000
MAX_SUBTREE_DEPTH = 32
MAX_SUBTREE_NODES = 2_000


def require_non_blank(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")


def require_optional_non_blank(value: str | None, field_name: str) -> None:
    if value is not None:
        require_non_blank(value, field_name)


def require_limit(value: int) -> None:
    if not 1 <= value <= MAX_PAGE_SIZE:
        raise ValueError(f"limit must be between 1 and {MAX_PAGE_SIZE}")


class AstCallDirection(StrEnum):
    CALLERS = "callers"
    CALLEES = "callees"


class AstEvidenceKind(StrEnum):
    TEST = "test"
    BDD_FEATURE = "bdd_feature"
    BDD_SCENARIO = "bdd_scenario"
    BDD_STEP = "bdd_step"


@dataclass(frozen=True)
class AstMcpPage:
    """Pagination/truncation metadata included by every tool response."""

    truncated: bool = False
    next_cursor: str | None = None

    def __post_init__(self) -> None:
        require_optional_non_blank(self.next_cursor, "next_cursor")
        if self.next_cursor is not None and not self.truncated:
            raise ValueError("next_cursor requires truncated=True")

    def to_dict(self) -> dict[str, object]:
        return {
            "truncated": self.truncated,
            "next_cursor": self.next_cursor,
        }


@dataclass(frozen=True)
class AstMcpFile:
    document_id: str
    source_file_id: str
    source_path: str
    language_key: str
    content_hash: str
    status: AstParseStatus
    source_bytes: int
    node_count: int
    error_node_count: int

    def __post_init__(self) -> None:
        for name, value in {
            "document_id": self.document_id,
            "source_file_id": self.source_file_id,
            "source_path": self.source_path,
            "language_key": self.language_key,
            "content_hash": self.content_hash,
        }.items():
            require_non_blank(value, name)
        if min(self.source_bytes, self.node_count, self.error_node_count) < 0:
            raise ValueError("file counts must be non-negative")
        if self.error_node_count > self.node_count:
            raise ValueError("error_node_count must not exceed node_count")

    def to_dict(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "source_file_id": self.source_file_id,
            "source_path": self.source_path,
            "language_key": self.language_key,
            "content_hash": self.content_hash,
            "status": self.status.value,
            "source_bytes": self.source_bytes,
            "node_count": self.node_count,
            "error_node_count": self.error_node_count,
        }


@dataclass(frozen=True)
class AstMcpDocument:
    file: AstMcpFile
    parser: ParserIdentity
    root_node_id: str | None
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_optional_non_blank(self.root_node_id, "root_node_id")
        if self.file.node_count > 0 and self.root_node_id is None:
            raise ValueError("documents with nodes require root_node_id")

    def to_dict(self) -> dict[str, object]:
        return {
            "file": self.file.to_dict(),
            "parser": self.parser.to_dict(),
            "root_node_id": self.root_node_id,
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True)
class AstMcpNode:
    node_id: str
    document_id: str
    parent_node_id: str | None
    raw_type: str
    category: AstNodeCategory
    source_range: AstSourceRange
    flags: AstNodeFlags
    sibling_ordinal: int
    field_name: str | None = None
    display_name: str | None = None
    subtree_hash: str | None = None
    depth: int | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_non_blank(self.node_id, "node_id")
        require_non_blank(self.document_id, "document_id")
        require_non_blank(self.raw_type, "raw_type")
        for name, value in {
            "parent_node_id": self.parent_node_id,
            "field_name": self.field_name,
            "display_name": self.display_name,
            "subtree_hash": self.subtree_hash,
        }.items():
            require_optional_non_blank(value, name)
        if self.sibling_ordinal < 0:
            raise ValueError("sibling_ordinal must be non-negative")
        if self.depth is not None and self.depth < 0:
            raise ValueError("depth must be non-negative")

    def to_dict(self) -> dict[str, object]:
        return {
            "node_id": self.node_id,
            "document_id": self.document_id,
            "parent_node_id": self.parent_node_id,
            "raw_type": self.raw_type,
            "category": self.category.value,
            "source_range": self.source_range.to_dict(),
            "flags": self.flags.to_dict(),
            "sibling_ordinal": self.sibling_ordinal,
            "field_name": self.field_name,
            "display_name": self.display_name,
            "subtree_hash": self.subtree_hash,
            "depth": self.depth,
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True)
class AstMcpLink:
    link_id: str
    source_node_id: str
    link_type: AstLinkType
    target_type: str
    target_id: str
    confidence: float

    def __post_init__(self) -> None:
        for name, value in {
            "link_id": self.link_id,
            "source_node_id": self.source_node_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
        }.items():
            require_non_blank(value, name)
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")

    def to_dict(self) -> dict[str, object]:
        return {
            "link_id": self.link_id,
            "source_node_id": self.source_node_id,
            "link_type": self.link_type.value,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class AstMcpSourceExcerpt:
    document_id: str
    source_path: str
    content_hash: str
    source_range: AstSourceRange
    text: str

    def __post_init__(self) -> None:
        require_non_blank(self.document_id, "document_id")
        require_non_blank(self.source_path, "source_path")
        require_non_blank(self.content_hash, "content_hash")
        if len(self.text.encode("utf-8")) > MAX_SOURCE_EXCERPT_BYTES:
            raise ValueError(f"text must not exceed {MAX_SOURCE_EXCERPT_BYTES} UTF-8 bytes")

    def to_dict(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "source_path": self.source_path,
            "content_hash": self.content_hash,
            "source_range": self.source_range.to_dict(),
            "text": self.text,
        }


@dataclass(frozen=True)
class AstMcpRelatedEvidence:
    evidence_kind: AstEvidenceKind
    evidence_id: str
    title: str
    source_path: str | None = None
    relationship: AstLinkType = AstLinkType.RELATED_TEST

    def __post_init__(self) -> None:
        require_non_blank(self.evidence_id, "evidence_id")
        require_non_blank(self.title, "title")
        require_optional_non_blank(self.source_path, "source_path")

    def to_dict(self) -> dict[str, object]:
        return {
            "evidence_kind": self.evidence_kind.value,
            "evidence_id": self.evidence_id,
            "title": self.title,
            "source_path": self.source_path,
            "relationship": self.relationship.value,
        }


__all__ = [
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "MAX_SOURCE_EXCERPT_BYTES",
    "MAX_SUBTREE_DEPTH",
    "MAX_SUBTREE_NODES",
    "AstCallDirection",
    "AstEvidenceKind",
    "AstMcpDocument",
    "AstMcpFile",
    "AstMcpLink",
    "AstMcpNode",
    "AstMcpPage",
    "AstMcpRelatedEvidence",
    "AstMcpSourceExcerpt",
    "require_limit",
    "require_non_blank",
    "require_optional_non_blank",
]
