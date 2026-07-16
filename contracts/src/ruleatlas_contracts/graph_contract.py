"""Structural graph provider contract (provider-neutral)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ProviderCapability:
    provider_key: str
    provider_version: str
    languages: tuple[str, ...]
    supports_full_repo: bool = True
    supports_file_fragment: bool = True
    notes: str = ""


@dataclass
class NormalizedGraphNode:
    provider_object_id: str
    canonical_key: str
    node_type: str
    display_name: str
    language_key: str | None = None
    source_path: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    content_hash: str | None = None
    symbol_kind: str | None = None
    confidence: float = 1.0
    attributes: dict = field(default_factory=dict)


@dataclass
class NormalizedGraphEdge:
    provider_object_id: str
    canonical_key: str
    edge_type: str
    from_canonical_key: str
    to_canonical_key: str
    confidence: float = 1.0
    resolution_type: str = "extracted"
    attributes: dict = field(default_factory=dict)


@dataclass
class StructuralAnalysisResult:
    provider_key: str
    provider_version: str
    status: str
    nodes: list[NormalizedGraphNode] = field(default_factory=list)
    edges: list[NormalizedGraphEdge] = field(default_factory=list)
    files_attempted: int = 0
    files_succeeded: int = 0
    files_failed: int = 0
    files_unsupported: int = 0
    duration_ms: int | None = None
    error_message: str | None = None
    raw_payload_hash: str | None = None
    summary: dict = field(default_factory=dict)


class StructuralGraphProvider(Protocol):
    def capabilities(self) -> ProviderCapability: ...

    def analyze_paths(self, root: str, relative_paths: list[str]) -> StructuralAnalysisResult: ...


__all__ = [
    "ProviderCapability",
    "NormalizedGraphNode",
    "NormalizedGraphEdge",
    "StructuralAnalysisResult",
    "StructuralGraphProvider",
]
