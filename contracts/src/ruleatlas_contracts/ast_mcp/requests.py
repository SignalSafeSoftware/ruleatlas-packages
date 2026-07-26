"""Provider-neutral AST MCP tool inputs.

Project, organization, and analysis-version scope are intentionally absent. The application must
inject those values from authenticated trusted context rather than accepting model-supplied scope.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ruleatlas_contracts.ast import AstNodeCategory, AstParseStatus
from ruleatlas_contracts.ast_mcp.common import (
    DEFAULT_PAGE_SIZE,
    MAX_SOURCE_EXCERPT_BYTES,
    MAX_SUBTREE_DEPTH,
    MAX_SUBTREE_NODES,
    AstCallDirection,
    require_limit,
    require_non_blank,
    require_optional_non_blank,
)


@dataclass(frozen=True)
class AstMcpPageRequest:
    cursor: str | None = None
    limit: int = DEFAULT_PAGE_SIZE

    def __post_init__(self) -> None:
        require_optional_non_blank(self.cursor, "cursor")
        require_limit(self.limit)

    def page_dict(self) -> dict[str, object]:
        return {"cursor": self.cursor, "limit": self.limit}


@dataclass(frozen=True)
class ListAstFilesRequest(AstMcpPageRequest):
    path_prefix: str | None = None
    language_key: str | None = None
    statuses: tuple[AstParseStatus, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        super().__post_init__()
        require_optional_non_blank(self.path_prefix, "path_prefix")
        require_optional_non_blank(self.language_key, "language_key")

    def to_dict(self) -> dict[str, object]:
        return {
            **self.page_dict(),
            "path_prefix": self.path_prefix,
            "language_key": self.language_key,
            "statuses": [status.value for status in self.statuses],
        }


@dataclass(frozen=True)
class GetAstDocumentRequest:
    document_id: str | None = None
    source_file_id: str | None = None

    def __post_init__(self) -> None:
        require_optional_non_blank(self.document_id, "document_id")
        require_optional_non_blank(self.source_file_id, "source_file_id")
        if (self.document_id is None) == (self.source_file_id is None):
            raise ValueError("provide exactly one of document_id or source_file_id")

    def to_dict(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "source_file_id": self.source_file_id,
        }


@dataclass(frozen=True)
class FindAstNodesRequest(AstMcpPageRequest):
    document_id: str | None = None
    raw_types: tuple[str, ...] = field(default_factory=tuple)
    categories: tuple[AstNodeCategory, ...] = field(default_factory=tuple)
    display_name: str | None = None
    start_byte: int | None = None
    end_byte: int | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        require_optional_non_blank(self.document_id, "document_id")
        require_optional_non_blank(self.display_name, "display_name")
        if any(not item.strip() for item in self.raw_types):
            raise ValueError("raw_types must not contain blank values")
        if (self.start_byte is None) != (self.end_byte is None):
            raise ValueError("start_byte and end_byte must be provided together")
        if (
            self.start_byte is not None
            and self.end_byte is not None
            and (self.start_byte < 0 or self.end_byte <= self.start_byte)
        ):
            raise ValueError("source range must be non-negative and non-empty")

    def to_dict(self) -> dict[str, object]:
        return {
            **self.page_dict(),
            "document_id": self.document_id,
            "raw_types": list(self.raw_types),
            "categories": [category.value for category in self.categories],
            "display_name": self.display_name,
            "start_byte": self.start_byte,
            "end_byte": self.end_byte,
        }


@dataclass(frozen=True)
class GetAstNodeRequest:
    node_id: str
    include_links: bool = True
    link_limit: int = DEFAULT_PAGE_SIZE

    def __post_init__(self) -> None:
        require_non_blank(self.node_id, "node_id")
        require_limit(self.link_limit)

    def to_dict(self) -> dict[str, object]:
        return {
            "node_id": self.node_id,
            "include_links": self.include_links,
            "link_limit": self.link_limit,
        }


@dataclass(frozen=True)
class ListAstChildrenRequest(AstMcpPageRequest):
    node_id: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        require_non_blank(self.node_id, "node_id")

    def to_dict(self) -> dict[str, object]:
        return {**self.page_dict(), "node_id": self.node_id}


@dataclass(frozen=True)
class GetAstSubtreeRequest(AstMcpPageRequest):
    node_id: str = ""
    max_depth: int = 8
    max_nodes: int = 500

    def __post_init__(self) -> None:
        super().__post_init__()
        require_non_blank(self.node_id, "node_id")
        if not 0 <= self.max_depth <= MAX_SUBTREE_DEPTH:
            raise ValueError(f"max_depth must be between 0 and {MAX_SUBTREE_DEPTH}")
        if not 1 <= self.max_nodes <= MAX_SUBTREE_NODES:
            raise ValueError(f"max_nodes must be between 1 and {MAX_SUBTREE_NODES}")

    def to_dict(self) -> dict[str, object]:
        return {
            **self.page_dict(),
            "node_id": self.node_id,
            "max_depth": self.max_depth,
            "max_nodes": self.max_nodes,
        }


@dataclass(frozen=True)
class GetSymbolAstRequest(AstMcpPageRequest):
    source_symbol_id: str = ""
    max_depth: int = 8
    max_nodes: int = 500

    def __post_init__(self) -> None:
        super().__post_init__()
        require_non_blank(self.source_symbol_id, "source_symbol_id")
        if not 0 <= self.max_depth <= MAX_SUBTREE_DEPTH:
            raise ValueError(f"max_depth must be between 0 and {MAX_SUBTREE_DEPTH}")
        if not 1 <= self.max_nodes <= MAX_SUBTREE_NODES:
            raise ValueError(f"max_nodes must be between 1 and {MAX_SUBTREE_NODES}")

    def to_dict(self) -> dict[str, object]:
        return {
            **self.page_dict(),
            "source_symbol_id": self.source_symbol_id,
            "max_depth": self.max_depth,
            "max_nodes": self.max_nodes,
        }


@dataclass(frozen=True)
class GetSourceExcerptRequest:
    document_id: str
    start_byte: int
    end_byte: int
    max_bytes: int = MAX_SOURCE_EXCERPT_BYTES
    cursor: str | None = None

    def __post_init__(self) -> None:
        require_non_blank(self.document_id, "document_id")
        require_optional_non_blank(self.cursor, "cursor")
        if self.start_byte < 0 or self.end_byte <= self.start_byte:
            raise ValueError("source range must be non-negative and non-empty")
        if not 1 <= self.max_bytes <= MAX_SOURCE_EXCERPT_BYTES:
            raise ValueError(f"max_bytes must be between 1 and {MAX_SOURCE_EXCERPT_BYTES}")

    def to_dict(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "start_byte": self.start_byte,
            "end_byte": self.end_byte,
            "max_bytes": self.max_bytes,
            "cursor": self.cursor,
        }


@dataclass(frozen=True)
class FindAstCallsRequest(AstMcpPageRequest):
    node_id: str = ""
    direction: AstCallDirection = AstCallDirection.CALLEES

    def __post_init__(self) -> None:
        super().__post_init__()
        require_non_blank(self.node_id, "node_id")

    def to_dict(self) -> dict[str, object]:
        return {
            **self.page_dict(),
            "node_id": self.node_id,
            "direction": self.direction.value,
        }


@dataclass(frozen=True)
class FindConditionsAssignmentsRequest(AstMcpPageRequest):
    document_id: str | None = None
    anchor_node_id: str | None = None
    include_conditions: bool = True
    include_assignments: bool = True

    def __post_init__(self) -> None:
        super().__post_init__()
        require_optional_non_blank(self.document_id, "document_id")
        require_optional_non_blank(self.anchor_node_id, "anchor_node_id")
        if self.document_id is None and self.anchor_node_id is None:
            raise ValueError("document_id or anchor_node_id is required")
        if not self.include_conditions and not self.include_assignments:
            raise ValueError("at least one of include_conditions or include_assignments is required")

    def to_dict(self) -> dict[str, object]:
        return {
            **self.page_dict(),
            "document_id": self.document_id,
            "anchor_node_id": self.anchor_node_id,
            "include_conditions": self.include_conditions,
            "include_assignments": self.include_assignments,
        }


@dataclass(frozen=True)
class FindRelatedEvidenceRequest(AstMcpPageRequest):
    node_id: str = ""
    include_tests: bool = True
    include_bdd: bool = True

    def __post_init__(self) -> None:
        super().__post_init__()
        require_non_blank(self.node_id, "node_id")
        if not self.include_tests and not self.include_bdd:
            raise ValueError("at least one evidence kind must be requested")

    def to_dict(self) -> dict[str, object]:
        return {
            **self.page_dict(),
            "node_id": self.node_id,
            "include_tests": self.include_tests,
            "include_bdd": self.include_bdd,
        }


__all__ = [
    "AstMcpPageRequest",
    "FindAstCallsRequest",
    "FindAstNodesRequest",
    "FindConditionsAssignmentsRequest",
    "FindRelatedEvidenceRequest",
    "GetAstDocumentRequest",
    "GetAstNodeRequest",
    "GetAstSubtreeRequest",
    "GetSourceExcerptRequest",
    "GetSymbolAstRequest",
    "ListAstChildrenRequest",
    "ListAstFilesRequest",
]
