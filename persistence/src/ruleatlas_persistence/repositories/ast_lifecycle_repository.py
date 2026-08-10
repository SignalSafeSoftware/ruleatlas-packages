"""Retention, reuse, accounting, and integrity operations for persisted ASTs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from ruleatlas_contracts.ast import AstParseStatus
from ruleatlas_contracts.enums import AnalysisVersionStatus
from sqlalchemy import delete, exists, func, or_, select, update
from sqlalchemy.orm import Session, aliased

from ruleatlas_persistence.models import (
    AnalysisVersion,
    AstDocument,
    AstNodeLink,
    AstParseRun,
    AstPayload,
    AstPayloadBlob,
    GraphNode,
    RuleEvidence,
    SourceSymbol,
)

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

MAX_ORPHAN_REPORT_ROWS = 2_000


@dataclass(frozen=True)
class AstVersionUsage:
    project_id: str
    analysis_version_id: str
    parse_runs: int
    documents: int
    nodes: int
    error_nodes: int
    source_bytes: int


@dataclass(frozen=True)
class AstRetentionResult:
    expired_analysis_version_ids: list[str]
    protected_document_ids: list[str]
    parse_runs_deleted: int
    documents_deleted: int
    nodes_deleted: int
    links_deleted: int


@dataclass(frozen=True)
class AstOrphanedLink:
    link_id: str
    source_node_id: str
    target_type: str
    target_id: str


class AstLifecycleRepository:
    """Perform explicitly scoped AST lifecycle operations without committing."""

    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        self._session = session
        self._factory = factory

    def usage_for_version(
        self,
        *,
        project_id: str,
        analysis_version_id: str,
    ) -> AstVersionUsage:
        parse_runs = self._session.scalar(
            select(func.count())
            .select_from(AstParseRun)
            .where(
                AstParseRun.project_id == project_id,
                AstParseRun.analysis_version_id == analysis_version_id,
            )
        )
        document_counts = self._session.execute(
            select(
                func.count(AstDocument.id),
                func.coalesce(func.sum(AstDocument.source_bytes), 0),
            ).where(
                AstDocument.project_id == project_id,
                AstDocument.analysis_version_id == analysis_version_id,
            )
        ).one()
        node_counts = self._session.execute(
            select(
                func.coalesce(func.sum(AstDocument.node_count), 0),
                func.coalesce(func.sum(AstDocument.error_node_count), 0),
            ).where(
                AstDocument.project_id == project_id,
                AstDocument.analysis_version_id == analysis_version_id,
            )
        ).one()
        return AstVersionUsage(
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            parse_runs=int(parse_runs or 0),
            documents=int(document_counts[0]),
            nodes=int(node_counts[0]),
            error_nodes=int(node_counts[1]),
            source_bytes=int(document_counts[1]),
        )

    def find_reusable_document(
        self,
        *,
        project_id: str,
        source_file_id: str,
        content_hash: str,
        parser_key: str,
        parser_version: str,
        grammar_key: str,
        grammar_version: str,
        excluding_analysis_version_id: str | None = None,
    ) -> AstDocument | None:
        """Find compatible immutable syntax metadata; callers still create a version-owned copy."""

        statement = select(AstDocument).where(
            AstDocument.project_id == project_id,
            AstDocument.source_file_id == source_file_id,
            AstDocument.content_hash == content_hash,
            AstDocument.parser_key == parser_key,
            AstDocument.parser_version == parser_version,
            AstDocument.grammar_key == grammar_key,
            AstDocument.grammar_version == grammar_version,
            AstDocument.status.in_(
                [
                    AstParseStatus.SUCCEEDED.value,
                    AstParseStatus.PARTIAL.value,
                    AstParseStatus.REUSED.value,
                ]
            ),
        )
        if excluding_analysis_version_id is not None:
            statement = statement.where(AstDocument.analysis_version_id != excluding_analysis_version_id)
        return self._session.scalar(statement.order_by(AstDocument.created_at.desc(), AstDocument.id.desc()).limit(1))

    def delete_expired_versions(
        self,
        *,
        project_id: str,
        completed_before: datetime,
        retain_analysis_version_ids: set[str] | None = None,
        protected_document_ids: set[str] | None = None,
    ) -> AstRetentionResult:
        """Delete AST data for old terminal versions while preserving referenced documents."""

        retained_versions = retain_analysis_version_ids or set()
        explicitly_protected = protected_document_ids or set()
        expiry_time = func.coalesce(
            AnalysisVersion.superseded_at,
            AnalysisVersion.completed_at,
            AnalysisVersion.created_at,
        )
        version_statement = select(AnalysisVersion.id).where(
            AnalysisVersion.project_id == project_id,
            AnalysisVersion.status.in_([AnalysisVersionStatus.SUPERSEDED, AnalysisVersionStatus.FAILED]),
            expiry_time < completed_before,
        )
        if retained_versions:
            version_statement = version_statement.where(AnalysisVersion.id.not_in(retained_versions))
        version_ids = list(self._session.scalars(version_statement.order_by(AnalysisVersion.id)))
        if not version_ids:
            return AstRetentionResult([], [], 0, 0, 0, 0)

        documents = list(
            self._session.scalars(
                select(AstDocument).where(
                    AstDocument.project_id == project_id,
                    AstDocument.analysis_version_id.in_(version_ids),
                )
            )
        )
        candidate_document_ids = {document.id for document in documents}
        protected_ids = explicitly_protected & candidate_document_ids
        deleted_document_ids = candidate_document_ids - protected_ids

        links_deleted = int(
            self._session.scalar(
                select(func.count())
                .select_from(AstNodeLink)
                .where(
                    AstNodeLink.ast_document_id.in_(deleted_document_ids)
                    | AstNodeLink.target_ast_document_id.in_(deleted_document_ids)
                )
            )
            or 0
        )
        nodes_deleted = 0
        documents_deleted = 0
        if deleted_document_ids:
            payload_ids = set(
                self._session.scalars(
                    select(AstDocument.ast_payload_id).where(
                        AstDocument.id.in_(deleted_document_ids),
                        AstDocument.ast_payload_id.is_not(None),
                    )
                )
            )
            self._session.execute(
                delete(AstNodeLink).where(
                    AstNodeLink.ast_document_id.in_(deleted_document_ids)
                    | AstNodeLink.target_ast_document_id.in_(deleted_document_ids)
                )
            )
            self._session.execute(
                update(AstDocument)
                .where(AstDocument.id.in_(deleted_document_ids))
                .values(root_node_key=None)
            )
            self._session.execute(delete(AstDocument).where(AstDocument.id.in_(deleted_document_ids)))
            documents_deleted = len(deleted_document_ids)
            unreferenced_payload_ids = set(
                self._session.scalars(
                    select(AstPayload.id).where(
                        AstPayload.id.in_(payload_ids),
                        ~exists(
                            select(AstDocument.id).where(
                                AstDocument.ast_payload_id == AstPayload.id
                            )
                        ),
                    )
                )
            )
            if unreferenced_payload_ids:
                nodes_deleted = int(
                    self._session.scalar(
                        select(func.coalesce(func.sum(AstPayload.node_count), 0)).where(
                            AstPayload.id.in_(unreferenced_payload_ids)
                        )
                    )
                    or 0
                )
                self._session.execute(
                    update(AstPayload)
                    .where(AstPayload.id.in_(unreferenced_payload_ids))
                    .values(root_node_key=None)
                )
                self._session.execute(
                    delete(AstPayloadBlob).where(
                        AstPayloadBlob.ast_payload_id.in_(unreferenced_payload_ids)
                    )
                )
                self._session.execute(
                    delete(AstPayload).where(
                        AstPayload.id.in_(unreferenced_payload_ids)
                    )
                )

        remaining_parse_run = exists(select(AstDocument.id).where(AstDocument.parse_run_id == AstParseRun.id))
        deletable_parse_run_ids = list(
            self._session.scalars(
                select(AstParseRun.id).where(
                    AstParseRun.project_id == project_id,
                    AstParseRun.analysis_version_id.in_(version_ids),
                    ~remaining_parse_run,
                )
            )
        )
        self._session.execute(
            delete(AstParseRun).where(
                AstParseRun.id.in_(deletable_parse_run_ids),
            )
        )
        self._session.flush()
        return AstRetentionResult(
            expired_analysis_version_ids=version_ids,
            protected_document_ids=sorted(protected_ids),
            parse_runs_deleted=len(deletable_parse_run_ids),
            documents_deleted=documents_deleted,
            nodes_deleted=nodes_deleted,
            links_deleted=links_deleted,
        )

    def report_orphaned_links(
        self,
        *,
        project_id: str,
        analysis_version_id: str,
        limit: int = 500,
    ) -> list[AstOrphanedLink]:
        if not 1 <= limit <= MAX_ORPHAN_REPORT_ROWS:
            raise ValueError(f"limit must be between 1 and {MAX_ORPHAN_REPORT_ROWS}")
        target_graph_node = aliased(GraphNode)
        target_source_symbol = aliased(SourceSymbol)
        target_rule_evidence = aliased(RuleEvidence)
        missing_typed_target = or_(
            (
                AstNodeLink.graph_node_id.is_not(None)
                & ~exists(
                    select(target_graph_node.id).where(target_graph_node.id == AstNodeLink.graph_node_id)
                ).correlate(AstNodeLink)
            ),
            (
                AstNodeLink.source_symbol_id.is_not(None)
                & ~exists(
                    select(target_source_symbol.id).where(target_source_symbol.id == AstNodeLink.source_symbol_id)
                ).correlate(AstNodeLink)
            ),
            (
                AstNodeLink.rule_evidence_id.is_not(None)
                & ~exists(
                    select(target_rule_evidence.id).where(target_rule_evidence.id == AstNodeLink.rule_evidence_id)
                ).correlate(AstNodeLink)
            ),
        )
        rows = self._session.scalars(
            select(AstNodeLink)
            .join(AstDocument, AstDocument.id == AstNodeLink.ast_document_id)
            .where(
                AstDocument.project_id == project_id,
                AstDocument.analysis_version_id == analysis_version_id,
                missing_typed_target,
            )
            .order_by(AstNodeLink.id)
            .limit(limit)
        )
        return [
            AstOrphanedLink(
                link_id=row.id,
                source_node_id=row.ast_node_key,
                target_type=row.target_type,
                target_id=row.target_id,
            )
            for row in rows
        ]


__all__ = [
    "MAX_ORPHAN_REPORT_ROWS",
    "AstLifecycleRepository",
    "AstOrphanedLink",
    "AstRetentionResult",
    "AstVersionUsage",
]
