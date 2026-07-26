"""Provider-neutral AST MCP tool outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ruleatlas_contracts.ast_mcp.common import (
    AstCallDirection,
    AstMcpDocument,
    AstMcpFile,
    AstMcpLink,
    AstMcpNode,
    AstMcpPage,
    AstMcpRelatedEvidence,
    AstMcpSourceExcerpt,
)


class _Serializable(Protocol):
    def to_dict(self) -> dict[str, object]: ...


def _items[T: _Serializable](values: tuple[T, ...]) -> list[object]:
    return [value.to_dict() for value in values]


@dataclass(frozen=True)
class ListAstFilesResponse:
    files: tuple[AstMcpFile, ...] = field(default_factory=tuple)
    page: AstMcpPage = field(default_factory=AstMcpPage)

    def to_dict(self) -> dict[str, object]:
        return {"files": _items(self.files), "page": self.page.to_dict()}


@dataclass(frozen=True)
class GetAstDocumentResponse:
    document: AstMcpDocument | None
    page: AstMcpPage = field(default_factory=AstMcpPage)

    def to_dict(self) -> dict[str, object]:
        return {
            "document": self.document.to_dict() if self.document else None,
            "page": self.page.to_dict(),
        }


@dataclass(frozen=True)
class AstNodesResponse:
    nodes: tuple[AstMcpNode, ...] = field(default_factory=tuple)
    page: AstMcpPage = field(default_factory=AstMcpPage)

    def to_dict(self) -> dict[str, object]:
        return {"nodes": _items(self.nodes), "page": self.page.to_dict()}


@dataclass(frozen=True)
class GetAstNodeResponse:
    node: AstMcpNode | None
    links: tuple[AstMcpLink, ...] = field(default_factory=tuple)
    page: AstMcpPage = field(default_factory=AstMcpPage)

    def to_dict(self) -> dict[str, object]:
        return {
            "node": self.node.to_dict() if self.node else None,
            "links": _items(self.links),
            "page": self.page.to_dict(),
        }


@dataclass(frozen=True)
class GetSourceExcerptResponse:
    excerpt: AstMcpSourceExcerpt | None
    page: AstMcpPage = field(default_factory=AstMcpPage)

    def to_dict(self) -> dict[str, object]:
        return {
            "excerpt": self.excerpt.to_dict() if self.excerpt else None,
            "page": self.page.to_dict(),
        }


@dataclass(frozen=True)
class FindAstCallsResponse:
    direction: AstCallDirection
    nodes: tuple[AstMcpNode, ...] = field(default_factory=tuple)
    links: tuple[AstMcpLink, ...] = field(default_factory=tuple)
    page: AstMcpPage = field(default_factory=AstMcpPage)

    def __post_init__(self) -> None:
        if self.links and len(self.links) != len(self.nodes):
            raise ValueError("links must be empty or align one-to-one with nodes")

    def to_dict(self) -> dict[str, object]:
        return {
            "direction": self.direction.value,
            "nodes": _items(self.nodes),
            "links": _items(self.links),
            "page": self.page.to_dict(),
        }


@dataclass(frozen=True)
class FindRelatedEvidenceResponse:
    evidence: tuple[AstMcpRelatedEvidence, ...] = field(default_factory=tuple)
    page: AstMcpPage = field(default_factory=AstMcpPage)

    def to_dict(self) -> dict[str, object]:
        return {
            "evidence": _items(self.evidence),
            "page": self.page.to_dict(),
        }


__all__ = [
    "AstNodesResponse",
    "FindAstCallsResponse",
    "FindRelatedEvidenceResponse",
    "GetAstDocumentResponse",
    "GetAstNodeResponse",
    "GetSourceExcerptResponse",
    "ListAstFilesResponse",
]
