"""Scoped write repositories for versioned AST persistence."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from ruleatlas_contracts.ast import (
    AstDocumentRecord,
    AstLinkRecord,
    AstLinkType,
    AstNodeRecord,
    AstParseRunRecord,
    AstParseStatus,
    AstParseSummary,
)
from sqlalchemy import Table, delete, insert, select, update
from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.mixins import uuid_str
from ruleatlas_persistence.models import (
    AstDocument,
    AstNode,
    AstNodeLink,
    AstParseRun,
    AstPayload,
)


class AstParseRunRepository(BaseRepository[AstParseRun, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(AstParseRun, session, factory)
        self._session = session

    def create_from_record(self, record: AstParseRunRecord) -> AstParseRun:
        row = AstParseRun(
            id=record.parse_run_id,
            project_id=record.project_id,
            analysis_version_id=record.analysis_version_id,
            scan_run_id=record.scan_run_id,
            parser_key=record.parser.parser_key,
            parser_version=record.parser.parser_version,
            status=record.status.value,
            error_message=record.error_message,
            summary_json=dict(record.attributes),
        )
        self._apply_summary(row, record.summary)
        self._session.add(row)
        self._session.flush()
        return row

    def update_outcome(
        self,
        parse_run_id: str,
        *,
        status: AstParseStatus,
        summary: AstParseSummary,
        error_message: str | None = None,
        summary_json: dict | None = None,
    ) -> AstParseRun:
        row = self._session.get(AstParseRun, parse_run_id)
        if row is None:
            raise LookupError(f"AST parse run not found: {parse_run_id}")
        if status == AstParseStatus.FAILED and not error_message:
            raise ValueError("failed parse runs require error_message")
        row.status = status.value
        row.error_message = error_message
        if summary_json is not None:
            row.summary_json = dict(summary_json)
        self._apply_summary(row, summary)
        self._session.flush()
        return row

    @staticmethod
    def _apply_summary(row: AstParseRun, summary: AstParseSummary) -> None:
        row.files_attempted = summary.files_attempted
        row.files_succeeded = summary.files_succeeded
        row.files_partial = summary.files_partial
        row.files_failed = summary.files_failed
        row.files_unsupported = summary.files_unsupported
        row.files_reused = summary.files_reused
        row.documents_count = summary.documents_created
        row.nodes_count = summary.nodes_created
        row.error_nodes_count = summary.error_nodes
        row.source_bytes = summary.source_bytes
        row.duration_ms = summary.duration_ms


class AstDocumentRepository(BaseRepository[AstDocument, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(AstDocument, session, factory)
        self._session = session

    def create_from_record(
        self,
        record: AstDocumentRecord,
        *,
        ast_payload_id: str,
    ) -> AstDocument:
        row = AstDocument(
            project_id=record.project_id,
            analysis_version_id=record.analysis_version_id,
            scan_run_id=record.scan_run_id,
            parse_run_id=record.parse_run_id,
            ast_payload_id=ast_payload_id,
            source_file_id=record.source_file_id,
            document_key=record.document_key,
            source_path=record.source_path,
            language_key=record.parser.language_key,
            parser_key=record.parser.parser_key,
            parser_version=record.parser.parser_version,
            grammar_key=record.parser.grammar_key,
            grammar_version=record.parser.grammar_version,
            content_hash=record.content_hash,
            status=record.status.value,
            source_bytes=record.source_bytes,
            node_count=0,
            error_node_count=0,
            parse_duration_ms=record.parse_duration_ms,
            error_message=record.error_message,
            attributes_json=dict(record.attributes),
        )
        self._session.add(row)
        self._session.flush()
        return row

    def replace_for_source(
        self,
        record: AstDocumentRecord,
        *,
        ast_payload_id: str,
    ) -> AstDocument:
        existing = self._session.scalar(
            select(AstDocument).where(
                AstDocument.project_id == record.project_id,
                AstDocument.analysis_version_id == record.analysis_version_id,
                AstDocument.source_file_id == record.source_file_id,
            )
        )
        if existing is not None:
            self.delete_scoped(
                project_id=record.project_id,
                analysis_version_id=record.analysis_version_id,
                document_id=existing.id,
            )
        return self.create_from_record(record, ast_payload_id=ast_payload_id)

    def delete_scoped(
        self,
        *,
        project_id: str,
        analysis_version_id: str,
        document_id: str,
    ) -> int:
        document = self._session.scalar(
            select(AstDocument).where(
                AstDocument.id == document_id,
                AstDocument.project_id == project_id,
                AstDocument.analysis_version_id == analysis_version_id,
            )
        )
        if document is None:
            return 0
        self._session.execute(update(AstDocument).where(AstDocument.id == document.id).values(root_node_id=None))
        self._session.execute(
            delete(AstNodeLink).where(AstNodeLink.ast_document_id == document.id)
        )
        self._session.execute(delete(AstDocument).where(AstDocument.id == document.id))
        self._session.flush()
        return 1


class AstPayloadRepository(BaseRepository[AstPayload, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(AstPayload, session, factory)
        self._session = session

    def get_for_record(self, record: AstDocumentRecord) -> AstPayload | None:
        return self._session.scalar(
            select(AstPayload).where(
                AstPayload.project_id == record.project_id,
                AstPayload.document_key == record.document_key,
                AstPayload.content_hash == record.content_hash,
                AstPayload.language_key == record.parser.language_key,
                AstPayload.parser_key == record.parser.parser_key,
                AstPayload.parser_version == record.parser.parser_version,
                AstPayload.grammar_key == record.parser.grammar_key,
                AstPayload.grammar_version == record.parser.grammar_version,
            )
        )

    def create_for_record(self, record: AstDocumentRecord) -> AstPayload:
        row = AstPayload(
            project_id=record.project_id,
            document_key=record.document_key,
            content_hash=record.content_hash,
            language_key=record.parser.language_key,
            parser_key=record.parser.parser_key,
            parser_version=record.parser.parser_version,
            grammar_key=record.parser.grammar_key,
            grammar_version=record.parser.grammar_version,
            source_bytes=record.source_bytes,
            node_count=record.node_count,
            error_node_count=record.error_node_count,
            attributes_json={},
        )
        self._session.add(row)
        self._session.flush()
        return row


class AstNodeRepository(BaseRepository[AstNode, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(AstNode, session, factory)
        self._session = session

    def bulk_create_for_document(
        self,
        document: AstDocument,
        records: list[AstNodeRecord],
    ) -> dict[str, str]:
        if not records:
            raise ValueError("records must not be empty")
        if document.ast_payload_id is None:
            raise ValueError("document must reference an AST payload")
        payload = self._session.get(AstPayload, document.ast_payload_id)
        if payload is None:
            raise ValueError("document AST payload does not exist")
        if payload.root_node_id is not None:
            raise ValueError("document already has persisted AST nodes")
        if any(record.document_key != document.document_key for record in records):
            raise ValueError("every node must match the target document_key")

        keys = [record.node_key for record in records]
        if len(set(keys)) != len(keys):
            raise ValueError("node_key values must be unique within a document")
        key_to_id = {key: uuid_str() for key in keys}
        roots = [record for record in records if record.parent_node_key is None]
        if len(roots) != 1:
            raise ValueError("a document node batch must contain exactly one root")
        for record in records:
            if record.parent_node_key is not None and record.parent_node_key not in key_to_id:
                raise ValueError(f"parent node is missing from batch: {record.parent_node_key}")

        payload_by_key = {
            record.node_key: {
                "id": key_to_id[record.node_key],
                "ast_payload_id": payload.id,
                "parent_node_id": (key_to_id[record.parent_node_key] if record.parent_node_key is not None else None),
                "node_key": record.node_key,
                "sibling_ordinal": record.sibling_ordinal,
                "raw_type": record.raw_type,
                "category": record.category.value,
                "field_name": record.field_name,
                "is_named": record.flags.is_named,
                "is_extra": record.flags.is_extra,
                "is_error": record.flags.is_error,
                "is_missing": record.flags.is_missing,
                "has_error": record.flags.has_error,
                "has_changes": record.flags.has_changes,
                "start_byte": record.source_range.start_byte,
                "end_byte": record.source_range.end_byte,
                "start_row": record.source_range.start_point.row,
                "start_column": record.source_range.start_point.column,
                "end_row": record.source_range.end_point.row,
                "end_column": record.source_range.end_point.column,
                "subtree_hash": record.subtree_hash,
                "display_name": record.display_name,
                "attributes_json": dict(record.attributes),
            }
            for record in records
        }
        remaining = {record.node_key: record for record in records}
        persisted_keys: set[str] = set()
        while remaining:
            layer = [
                record
                for record in remaining.values()
                if record.parent_node_key is None or record.parent_node_key in persisted_keys
            ]
            if not layer:
                unresolved = ", ".join(sorted(remaining)[:3])
                raise ValueError(
                    f"node parents contain a cycle or missing key: {unresolved}"
                )
            self._session.execute(
                insert(cast(Table, AstNode.__table__)),
                [payload_by_key[record.node_key] for record in layer],
            )
            self._session.flush()
            for record in layer:
                persisted_keys.add(record.node_key)
                remaining.pop(record.node_key)
        payload.root_node_id = key_to_id[roots[0].node_key]
        payload.node_count = len(records)
        payload.error_node_count = sum(1 for record in records if record.flags.is_error)
        document.root_node_id = payload.root_node_id
        document.node_count = len(records)
        document.error_node_count = payload.error_node_count
        self._session.flush()
        return key_to_id


class AstNodeLinkRepository(BaseRepository[AstNodeLink, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(AstNodeLink, session, factory)
        self._session = session

    def bulk_create_for_document(
        self,
        document: AstDocument,
        records: list[AstLinkRecord],
    ) -> int:
        if not records:
            return 0
        if any(record.document_key != document.document_key for record in records):
            raise ValueError("every link must match the target document_key")
        node_rows = self._session.execute(
            select(AstNode.node_key, AstNode.id).where(
                AstNode.ast_payload_id == document.ast_payload_id
            )
        ).all()
        node_ids: dict[str, str] = {}
        for node_key, node_id in node_rows:
            node_ids[node_key] = node_id
        missing = {record.source_node_key for record in records if record.source_node_key not in node_ids}
        if missing:
            raise ValueError(f"source nodes are missing from document: {sorted(missing)}")

        payloads = []
        for record in records:
            typed_targets = self._typed_target(record)
            payloads.append(
                {
                    "id": uuid_str(),
                    "ast_document_id": document.id,
                    "ast_node_id": node_ids[record.source_node_key],
                    "link_type": record.link_type.value,
                    "target_type": record.link_type.value,
                    "target_id": record.target_id,
                    **typed_targets,
                    "resolution_type": record.resolution_type.value,
                    "resolver_key": record.resolver_key,
                    "resolver_version": record.resolver_version,
                    "confidence": record.confidence,
                    "attributes_json": dict(record.attributes),
                }
            )
        self._session.execute(insert(cast(Table, AstNodeLink.__table__)), payloads)
        self._session.flush()
        return len(payloads)

    @staticmethod
    def _typed_target(record: AstLinkRecord) -> dict[str, str | None]:
        targets: dict[str, str | None] = {
            "graph_node_id": None,
            "source_symbol_id": None,
            "rule_evidence_id": None,
            "target_ast_node_id": None,
        }
        field_by_type = {
            AstLinkType.GRAPH_NODE: "graph_node_id",
            AstLinkType.SOURCE_SYMBOL: "source_symbol_id",
            AstLinkType.EVIDENCE: "rule_evidence_id",
            AstLinkType.CALL_TARGET: "target_ast_node_id",
            AstLinkType.DEFINITION: "target_ast_node_id",
            AstLinkType.REFERENCE: "target_ast_node_id",
        }
        field_name = field_by_type.get(record.link_type)
        if field_name is not None:
            targets[field_name] = record.target_id
        return targets


__all__ = [
    "AstDocumentRepository",
    "AstNodeLinkRepository",
    "AstNodeRepository",
    "AstParseRunRepository",
    "AstPayloadRepository",
]
