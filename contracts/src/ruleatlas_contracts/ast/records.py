"""Normalized AST records shared by parsers, persistence, and query adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ruleatlas_contracts.ast.primitives import (
    AstLinkType,
    AstNodeCategory,
    AstNodeFlags,
    AstParseStatus,
    AstResolutionType,
    AstSourceRange,
    ParserIdentity,
    ParserRuntimeIdentity,
)


def _require_non_blank(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")


def _require_non_negative(value: int, field_name: str) -> None:
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")


def _require_optional_non_blank(value: str | None, field_name: str) -> None:
    if value is not None:
        _require_non_blank(value, field_name)


@dataclass(frozen=True)
class AstProviderCapability:
    """Languages and operating modes supported by one AST parser adapter."""

    parser: ParserRuntimeIdentity
    languages: tuple[str, ...]
    supports_full_repository: bool = True
    supports_file_fragment: bool = True
    supports_incremental_parse: bool = False
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.languages:
            raise ValueError("languages must not be empty")
        if any(not language.strip() for language in self.languages):
            raise ValueError("languages must not contain blank values")
        if len(set(self.languages)) != len(self.languages):
            raise ValueError("languages must not contain duplicates")

    def to_dict(self) -> dict[str, object]:
        return {
            "parser": self.parser.to_dict(),
            "languages": list(self.languages),
            "supports_full_repository": self.supports_full_repository,
            "supports_file_fragment": self.supports_file_fragment,
            "supports_incremental_parse": self.supports_incremental_parse,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class AstParseSummary:
    """Bounded counters describing one parser run."""

    files_attempted: int = 0
    files_succeeded: int = 0
    files_partial: int = 0
    files_failed: int = 0
    files_unsupported: int = 0
    files_reused: int = 0
    documents_created: int = 0
    nodes_created: int = 0
    error_nodes: int = 0
    source_bytes: int = 0
    duration_ms: int | None = None

    def __post_init__(self) -> None:
        fields = {
            "files_attempted": self.files_attempted,
            "files_succeeded": self.files_succeeded,
            "files_partial": self.files_partial,
            "files_failed": self.files_failed,
            "files_unsupported": self.files_unsupported,
            "files_reused": self.files_reused,
            "documents_created": self.documents_created,
            "nodes_created": self.nodes_created,
            "error_nodes": self.error_nodes,
            "source_bytes": self.source_bytes,
        }
        for field_name, value in fields.items():
            _require_non_negative(value, field_name)
        if self.duration_ms is not None:
            _require_non_negative(self.duration_ms, "duration_ms")
        terminal_files = (
            self.files_succeeded + self.files_partial + self.files_failed + self.files_unsupported + self.files_reused
        )
        if terminal_files > self.files_attempted:
            raise ValueError("terminal file counts must not exceed files_attempted")
        if self.error_nodes > self.nodes_created:
            raise ValueError("error_nodes must not exceed nodes_created")

    @property
    def files_completed(self) -> int:
        return (
            self.files_succeeded + self.files_partial + self.files_failed + self.files_unsupported + self.files_reused
        )

    def to_dict(self) -> dict[str, int | None]:
        return {
            "files_attempted": self.files_attempted,
            "files_succeeded": self.files_succeeded,
            "files_partial": self.files_partial,
            "files_failed": self.files_failed,
            "files_unsupported": self.files_unsupported,
            "files_reused": self.files_reused,
            "documents_created": self.documents_created,
            "nodes_created": self.nodes_created,
            "error_nodes": self.error_nodes,
            "source_bytes": self.source_bytes,
            "duration_ms": self.duration_ms,
        }


@dataclass(frozen=True)
class AstParseRunRecord:
    """Application-to-persistence record for one scoped AST parse run."""

    parse_run_id: str
    project_id: str
    analysis_version_id: str
    parser: ParserRuntimeIdentity
    status: AstParseStatus
    summary: AstParseSummary = field(default_factory=AstParseSummary)
    scan_run_id: str | None = None
    error_message: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_blank(self.parse_run_id, "parse_run_id")
        _require_non_blank(self.project_id, "project_id")
        _require_non_blank(self.analysis_version_id, "analysis_version_id")
        _require_optional_non_blank(self.scan_run_id, "scan_run_id")
        _require_optional_non_blank(self.error_message, "error_message")
        if self.status == AstParseStatus.FAILED and self.error_message is None:
            raise ValueError("failed parse runs require error_message")


@dataclass(frozen=True)
class AstDocumentRecord:
    """One immutable source document parsed within an analysis version."""

    document_key: str
    project_id: str
    analysis_version_id: str
    parse_run_id: str
    source_file_id: str
    source_path: str
    parser: ParserIdentity
    content_hash: str
    status: AstParseStatus
    source_bytes: int
    node_count: int
    error_node_count: int = 0
    root_node_key: str | None = None
    scan_run_id: str | None = None
    parse_duration_ms: int | None = None
    error_message: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        required = {
            "document_key": self.document_key,
            "project_id": self.project_id,
            "analysis_version_id": self.analysis_version_id,
            "parse_run_id": self.parse_run_id,
            "source_file_id": self.source_file_id,
            "source_path": self.source_path,
            "content_hash": self.content_hash,
        }
        for field_name, value in required.items():
            _require_non_blank(value, field_name)
        _require_optional_non_blank(self.root_node_key, "root_node_key")
        _require_optional_non_blank(self.scan_run_id, "scan_run_id")
        _require_optional_non_blank(self.error_message, "error_message")
        _require_non_negative(self.source_bytes, "source_bytes")
        _require_non_negative(self.node_count, "node_count")
        _require_non_negative(self.error_node_count, "error_node_count")
        if self.parse_duration_ms is not None:
            _require_non_negative(self.parse_duration_ms, "parse_duration_ms")
        if self.error_node_count > self.node_count:
            raise ValueError("error_node_count must not exceed node_count")
        if self.node_count == 0 and self.root_node_key is not None:
            raise ValueError("root_node_key requires at least one node")
        if self.node_count > 0 and self.root_node_key is None:
            raise ValueError("documents with nodes require root_node_key")
        if self.status == AstParseStatus.FAILED and self.error_message is None:
            raise ValueError("failed documents require error_message")


@dataclass(frozen=True)
class AstNodeRecord:
    """One normalized parser node with a document-local stable key."""

    document_key: str
    node_key: str
    raw_type: str
    source_range: AstSourceRange
    flags: AstNodeFlags
    sibling_ordinal: int
    parent_node_key: str | None = None
    field_name: str | None = None
    category: AstNodeCategory = AstNodeCategory.UNKNOWN
    subtree_hash: str | None = None
    display_name: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_blank(self.document_key, "document_key")
        _require_non_blank(self.node_key, "node_key")
        _require_non_blank(self.raw_type, "raw_type")
        _require_non_negative(self.sibling_ordinal, "sibling_ordinal")
        _require_optional_non_blank(self.parent_node_key, "parent_node_key")
        _require_optional_non_blank(self.field_name, "field_name")
        _require_optional_non_blank(self.subtree_hash, "subtree_hash")
        _require_optional_non_blank(self.display_name, "display_name")
        if self.parent_node_key == self.node_key:
            raise ValueError("a node cannot be its own parent")

    @property
    def is_root(self) -> bool:
        return self.parent_node_key is None


@dataclass(frozen=True)
class AstLinkRecord:
    """Resolved or inferred relationship from an AST node to another artifact."""

    document_key: str
    source_node_key: str
    link_type: AstLinkType
    target_id: str
    resolution_type: AstResolutionType
    resolver_key: str
    resolver_version: str
    confidence: float
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        required = {
            "document_key": self.document_key,
            "source_node_key": self.source_node_key,
            "target_id": self.target_id,
            "resolver_key": self.resolver_key,
            "resolver_version": self.resolver_version,
        }
        for field_name, value in required.items():
            _require_non_blank(value, field_name)
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")


__all__ = [
    "AstDocumentRecord",
    "AstLinkRecord",
    "AstNodeRecord",
    "AstParseRunRecord",
    "AstParseSummary",
    "AstProviderCapability",
]
