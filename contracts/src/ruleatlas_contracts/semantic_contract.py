"""Semantic analysis provider contract (optional enrichers)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from ruleatlas_contracts.graph_contract import ProviderCapability


@dataclass
class SemanticSymbol:
    symbol_key: str
    display_name: str
    kind: str
    source_path: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    confidence: float = 1.0
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticReference:
    from_symbol_key: str
    to_symbol_key: str
    reference_kind: str
    source_path: str | None = None
    start_line: int | None = None
    confidence: float = 1.0
    resolution_type: str = "extracted"
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticImplementation:
    interface_symbol_key: str
    implementation_symbol_key: str
    confidence: float = 1.0
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticDiagnostic:
    code: str
    message: str
    severity: str = "warning"
    source_path: str | None = None
    start_line: int | None = None


@dataclass
class SemanticAnalysisResult:
    provider_key: str
    provider_version: str
    status: str
    symbols: list[SemanticSymbol] = field(default_factory=list)
    references: list[SemanticReference] = field(default_factory=list)
    implementations: list[SemanticImplementation] = field(default_factory=list)
    diagnostics: list[SemanticDiagnostic] = field(default_factory=list)
    duration_ms: int | None = None
    error_message: str | None = None
    summary: dict[str, Any] = field(default_factory=dict)


class SemanticProvider(Protocol):
    def capabilities(self) -> ProviderCapability: ...

    def analyze_paths(self, root: str, relative_paths: list[str]) -> SemanticAnalysisResult: ...


__all__ = [
    "SemanticAnalysisResult",
    "SemanticDiagnostic",
    "SemanticImplementation",
    "SemanticProvider",
    "SemanticReference",
    "SemanticSymbol",
]
