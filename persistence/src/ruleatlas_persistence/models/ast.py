"""Persistence models for versioned, parser-independent abstract syntax trees."""

from __future__ import annotations

from dataclasses import dataclass

from ruleatlas_contracts.ast import AstParseStatus
from sqlalchemy import CheckConstraint, LargeBinary

from ._base import (
    FK_PROJECTS_ID,
    FK_SCAN_RUNS_ID,
    FK_SOURCE_FILES_ID,
    JSON,
    Base,
    Float,
    ForeignKey,
    Index,
    Integer,
    Mapped,
    String,
    Text,
    TimestampMixin,
    UniqueConstraint,
    mapped_column,
    uuid_str,
)

CK_ERROR_NODE_COUNT_BOUNDED = "error_node_count <= node_count"


class AstParseRun(Base, TimestampMixin):
    __tablename__ = "ast_parse_runs"
    __table_args__ = (
        Index("ix_ast_parse_runs_project_analysis", "project_id", "analysis_version_id"),
        Index("ix_ast_parse_runs_scan", "scan_run_id"),
        Index("ix_ast_parse_runs_status", "status"),
        CheckConstraint(
            "files_attempted >= 0 AND files_succeeded >= 0 AND files_partial >= 0 "
            "AND files_failed >= 0 AND files_unsupported >= 0 AND files_reused >= 0",
            name="ck_ast_parse_runs_file_counts_nonnegative",
        ),
        CheckConstraint(
            "nodes_count >= 0 AND error_nodes_count >= 0 AND source_bytes >= 0",
            name="ck_ast_parse_runs_size_counts_nonnegative",
        ),
        CheckConstraint(
            "error_nodes_count <= nodes_count",
            name="ck_ast_parse_runs_error_nodes_bounded",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str] = mapped_column(ForeignKey("analysis_versions.id"), nullable=False)
    scan_run_id: Mapped[str | None] = mapped_column(ForeignKey(FK_SCAN_RUNS_ID))
    parser_key: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=AstParseStatus.PENDING.value)
    files_attempted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_succeeded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_partial: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_unsupported: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_reused: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    documents_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nodes_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_nodes_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class AstPayload(Base, TimestampMixin):
    """Immutable syntax-tree payload shared by version-scoped documents."""

    __tablename__ = "ast_payloads"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "document_key",
            "content_hash",
            "language_key",
            "parser_key",
            "parser_version",
            "grammar_key",
            "grammar_version",
            name="uq_ast_payloads_parser_identity",
        ),
        Index("ix_ast_payloads_project_content", "project_id", "content_hash"),
        CheckConstraint(
            "source_bytes >= 0 AND node_count >= 0 AND error_node_count >= 0",
            name="ck_ast_payloads_counts_nonnegative",
        ),
        CheckConstraint(
            CK_ERROR_NODE_COUNT_BOUNDED,
            name="ck_ast_payloads_error_nodes_bounded",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    document_key: Mapped[str] = mapped_column(String(512), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    language_key: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_key: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(64), nullable=False)
    grammar_key: Mapped[str] = mapped_column(String(128), nullable=False)
    grammar_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    node_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_node_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    root_node_key: Mapped[str | None] = mapped_column(String(512))
    attributes_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class AstPayloadBlob(Base, TimestampMixin):
    """Immutable, versioned compressed representation of an AST payload."""

    __tablename__ = "ast_payload_blobs"
    __table_args__ = (
        UniqueConstraint("ast_payload_id", name="uq_ast_payload_blobs_payload"),
        CheckConstraint(
            "uncompressed_bytes >= 0 AND compressed_bytes >= 0 AND node_count >= 0 "
            "AND error_node_count >= 0",
            name="ck_ast_payload_blobs_size_counts_nonnegative",
        ),
        CheckConstraint(
            CK_ERROR_NODE_COUNT_BOUNDED,
            name="ck_ast_payload_blobs_error_nodes_bounded",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    ast_payload_id: Mapped[str] = mapped_column(ForeignKey("ast_payloads.id"), nullable=False)
    encoding_version: Mapped[str] = mapped_column(String(64), nullable=False)
    compression_codec: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_bytes: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    uncompressed_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    uncompressed_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    compressed_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    node_count: Mapped[int] = mapped_column(Integer, nullable=False)
    error_node_count: Mapped[int] = mapped_column(Integer, nullable=False)
    root_node_key: Mapped[str | None] = mapped_column(String(512))


class AstDocument(Base, TimestampMixin):
    __tablename__ = "ast_documents"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "analysis_version_id",
            "source_file_id",
            name="uq_ast_documents_analysis_source_file",
        ),
        UniqueConstraint(
            "analysis_version_id",
            "document_key",
            name="uq_ast_documents_analysis_key",
        ),
        Index("ix_ast_documents_project_analysis", "project_id", "analysis_version_id"),
        Index("ix_ast_documents_parse_run", "parse_run_id"),
        Index("ix_ast_documents_payload", "ast_payload_id"),
        Index("ix_ast_documents_source_file", "source_file_id"),
        Index("ix_ast_documents_language", "language_key"),
        Index("ix_ast_documents_content_grammar", "content_hash", "grammar_version"),
        CheckConstraint(
            "source_bytes >= 0 AND node_count >= 0 AND error_node_count >= 0",
            name="ck_ast_documents_counts_nonnegative",
        ),
        CheckConstraint(
            CK_ERROR_NODE_COUNT_BOUNDED,
            name="ck_ast_documents_error_nodes_bounded",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str] = mapped_column(ForeignKey("analysis_versions.id"), nullable=False)
    scan_run_id: Mapped[str | None] = mapped_column(ForeignKey(FK_SCAN_RUNS_ID))
    parse_run_id: Mapped[str] = mapped_column(ForeignKey("ast_parse_runs.id"), nullable=False)
    ast_payload_id: Mapped[str] = mapped_column(ForeignKey("ast_payloads.id"), nullable=False)
    source_file_id: Mapped[str] = mapped_column(ForeignKey(FK_SOURCE_FILES_ID), nullable=False)
    document_key: Mapped[str] = mapped_column(String(512), nullable=False)
    source_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    language_key: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_key: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(64), nullable=False)
    grammar_key: Mapped[str] = mapped_column(String(128), nullable=False)
    grammar_version: Mapped[str] = mapped_column(String(64), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=AstParseStatus.PENDING.value)
    source_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    node_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_node_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    root_node_key: Mapped[str | None] = mapped_column(String(512))
    parse_duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    attributes_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


@dataclass(frozen=True)
class AstNode:
    """Decoded AST node view.

    AST nodes are stored exclusively in immutable packed payloads.  This small
    value object preserves the read contract used by application services while
    making it impossible to accidentally issue a relational ``ast_nodes`` query.
    """

    id: str
    ast_payload_id: str
    parent_node_id: str | None
    node_key: str
    sibling_ordinal: int
    raw_type: str
    category: str
    field_name: str | None
    is_named: bool
    is_extra: bool
    is_error: bool
    is_missing: bool
    has_error: bool
    has_changes: bool
    start_byte: int
    end_byte: int
    start_row: int
    start_column: int
    end_row: int
    end_column: int
    subtree_hash: str | None
    display_name: str | None
    attributes_json: dict


class AstNodeLink(Base, TimestampMixin):
    __tablename__ = "ast_node_links"
    __table_args__ = (
        Index("ix_ast_node_links_document", "ast_document_id"),
        Index("ix_ast_node_links_document_key", "ast_document_id", "ast_node_key"),
        Index("ix_ast_node_links_graph_node", "graph_node_id"),
        Index("ix_ast_node_links_source_symbol", "source_symbol_id"),
        Index("ix_ast_node_links_evidence", "rule_evidence_id"),
        Index(
            "ix_ast_node_links_target_document_key",
            "target_ast_document_id",
            "target_ast_node_key",
        ),
        Index("ix_ast_node_links_target", "target_type", "target_id"),
        CheckConstraint(
            "(CASE WHEN graph_node_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN source_symbol_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN rule_evidence_id IS NOT NULL THEN 1 ELSE 0 END) <= 1",
            name="ck_ast_node_links_at_most_one_typed_target",
        ),
        CheckConstraint(
            "(target_ast_document_id IS NULL) = (target_ast_node_key IS NULL)",
            name="ck_ast_node_links_target_ast_pointer_complete",
        ),
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="ck_ast_node_links_confidence",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    ast_document_id: Mapped[str] = mapped_column(ForeignKey("ast_documents.id"), nullable=False)
    ast_node_key: Mapped[str] = mapped_column(String(512), nullable=False)
    link_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(512), nullable=False)
    graph_node_id: Mapped[str | None] = mapped_column(ForeignKey("graph_nodes.id"))
    source_symbol_id: Mapped[str | None] = mapped_column(ForeignKey("source_symbols.id"))
    rule_evidence_id: Mapped[str | None] = mapped_column(ForeignKey("rule_evidence.id"))
    target_ast_document_id: Mapped[str | None] = mapped_column(ForeignKey("ast_documents.id"))
    target_ast_node_key: Mapped[str | None] = mapped_column(String(512))
    resolution_type: Mapped[str] = mapped_column(String(32), nullable=False)
    resolver_key: Mapped[str] = mapped_column(String(64), nullable=False)
    resolver_version: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    attributes_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "AstDocument",
    "AstNode",
    "AstNodeLink",
    "AstParseRun",
    "AstPayload",
    "AstPayloadBlob",
]
