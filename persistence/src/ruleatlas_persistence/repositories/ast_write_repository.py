"""Scoped write repositories for versioned AST persistence."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from ruleatlas_contracts.ast import (
    AstDocumentRecord,
    AstLinkRecord,
    AstLinkType,
    AstNodeCategory,
    AstNodeFlags,
    AstNodeRecord,
    AstParseRunRecord,
    AstParseStatus,
    AstParseSummary,
    AstPoint,
    AstSourceRange,
)
from sqlalchemy import Table, and_, delete, insert, or_, select, update
from sqlalchemy.orm import Session, aliased
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.ast_payload_codec import (
    COMPRESSION_CODEC,
    ENCODING_VERSION,
    DecodedAstPayload,
    decode_ast_payload,
    encode_ast_payload,
)
from ruleatlas_persistence.mixins import uuid_str
from ruleatlas_persistence.models import (
    AstDocument,
    AstNode,
    AstNodeLink,
    AstParseRun,
    AstPayload,
    AstPayloadBlob,
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
        self._session.execute(
            update(AstDocument)
            .where(AstDocument.id == document.id)
            .values(root_node_id=None, root_node_key=None)
        )
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


class AstPayloadBlobRepository(BaseRepository[AstPayloadBlob, "RepositoryFactory"]):
    """Write-once compressed payloads used during the RA-01 dual-write phase."""

    MAX_DECODE_DOCUMENTS_PER_BATCH = 64

    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(AstPayloadBlob, session, factory)
        self._session = session
        self._decoded_by_scope: dict[tuple[str, str, str], DecodedAstPayload] = {}

    def get_for_payload(self, ast_payload_id: str) -> AstPayloadBlob | None:
        return self._session.scalar(
            select(AstPayloadBlob).where(AstPayloadBlob.ast_payload_id == ast_payload_id)
        )

    def list_payloads_without_blob(
        self,
        *,
        limit: int,
        after_payload_id: str | None = None,
    ) -> list[AstPayload]:
        """Return a stable, bounded page for a resumable populated-db backfill."""

        if limit < 1:
            raise ValueError("limit must be at least 1")
        statement = (
            select(AstPayload)
            .outerjoin(AstPayloadBlob, AstPayloadBlob.ast_payload_id == AstPayload.id)
            .where(AstPayloadBlob.id.is_(None))
            .order_by(AstPayload.id)
            .limit(limit)
        )
        if after_payload_id is not None:
            statement = statement.where(AstPayload.id > after_payload_id)
        return list(self._session.scalars(statement))

    def create_for_node_records(
        self,
        payload: AstPayload,
        records: list[AstNodeRecord],
    ) -> AstPayloadBlob:
        """Persist the canonical blob once, rejecting a conflicting rewrite."""

        encoded = encode_ast_payload(records, document_key=payload.document_key)
        existing = self.get_for_payload(payload.id)
        if existing is not None:
            if existing.uncompressed_sha256 != encoded.uncompressed_sha256:
                raise ValueError("AST payload blob already exists with different node content")
            decoded = decode_ast_payload(
                existing.payload_bytes,
                expected_sha256=existing.uncompressed_sha256,
            )
            if (
                existing.encoding_version != encoded.encoding_version
                or existing.compression_codec != encoded.compression_codec
                or existing.node_count != encoded.node_count
                or existing.error_node_count != encoded.error_node_count
            or existing.root_node_key != decoded.root_node_key
                or existing.uncompressed_bytes != decoded.uncompressed_bytes
                or existing.compressed_bytes != len(existing.payload_bytes)
            ):
                raise ValueError("AST payload blob metadata does not match its contents")
            return existing
        row = AstPayloadBlob(
            ast_payload_id=payload.id,
            encoding_version=encoded.encoding_version,
            compression_codec=encoded.compression_codec,
            payload_bytes=encoded.payload_bytes,
            uncompressed_sha256=encoded.uncompressed_sha256,
            uncompressed_bytes=encoded.uncompressed_bytes,
            compressed_bytes=encoded.compressed_bytes,
            node_count=encoded.node_count,
            error_node_count=encoded.error_node_count,
            root_node_key=encoded.root_node_key,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def backfill_payload(self, ast_payload_id: str) -> AstPayloadBlob:
        """Create and verify one blob from existing rows; safe to resume per ID."""

        payload = self._session.get(AstPayload, ast_payload_id)
        if payload is None:
            raise LookupError(f"AST payload not found: {ast_payload_id}")
        existing = self.get_for_payload(payload.id)
        if existing is None:
            existing = self.create_for_node_records(payload, self._records_from_nodes(payload))
        self.verify_against_relational_nodes(payload)
        return existing

    def decode_for_document(
        self,
        *,
        project_id: str,
        analysis_version_id: str,
        document_id: str,
    ) -> DecodedAstPayload | None:
        """Return one decoded blob only after document ownership is established.

        The cache belongs to the session-scoped repository factory.  Every cache
        lookup first resolves the requested document within the caller's project
        and analysis version, preventing a cached payload from crossing scope.
        """

        return self.decode_for_documents(
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            document_ids=(document_id,),
            cache=True,
        ).get(document_id)

    def decode_for_documents(
        self,
        *,
        project_id: str,
        analysis_version_id: str,
        document_ids: tuple[str, ...] | list[str],
        cache: bool = False,
    ) -> dict[str, DecodedAstPayload]:
        """Decode a bounded, scope-checked batch of packed documents in one query.

        Callers that process a whole analysis must supply small batches and keep
        ``cache=False`` so the session does not retain every decoded tree.  The
        single-document API keeps its per-session cache for interactive reads.
        Documents with no packed payload are omitted so callers can apply their
        explicit legacy fallback without weakening project/version scoping.
        """

        ids = tuple(dict.fromkeys(document_ids))
        if not ids:
            return {}
        if len(ids) > self.MAX_DECODE_DOCUMENTS_PER_BATCH:
            raise ValueError(
                "decode_for_documents exceeds the bounded batch size "
                f"({self.MAX_DECODE_DOCUMENTS_PER_BATCH})"
            )
        rows = self._session.execute(
            select(AstDocument, AstPayloadBlob)
            .join(AstPayloadBlob, AstPayloadBlob.ast_payload_id == AstDocument.ast_payload_id)
            .where(
                AstDocument.id.in_(ids),
                AstDocument.project_id == project_id,
                AstDocument.analysis_version_id == analysis_version_id,
            )
        ).all()
        decoded_by_document: dict[str, DecodedAstPayload] = {}
        for document, blob in rows:
            cache_key = (project_id, analysis_version_id, document.ast_payload_id)
            decoded = self._decoded_by_scope.get(cache_key) if cache else None
            if decoded is None:
                decoded = self._decode_blob(blob)
                if cache:
                    self._decoded_by_scope[cache_key] = decoded
            if (
                decoded.document_key != document.document_key
                or len(decoded.records) != document.node_count
            ):
                raise ValueError("AST payload blob does not match its scoped document metadata")
            decoded_by_document[document.id] = decoded
        return decoded_by_document

    def verify_against_relational_nodes(self, payload: AstPayload) -> DecodedAstPayload:
        """Prove an existing packed payload preserves the current node projection."""

        blob = self.get_for_payload(payload.id)
        if blob is None:
            raise LookupError(f"AST payload blob not found: {payload.id}")
        decoded = self._decode_blob(blob)
        relational_records = self._records_from_nodes(payload)
        relational = encode_ast_payload(relational_records, document_key=payload.document_key)
        if relational.uncompressed_sha256 != blob.uncompressed_sha256:
            raise ValueError("AST payload blob differs from its relational node projection")
        root_node_key: str | None = None
        if payload.root_node_id is not None:
            root_node_key = self._session.scalar(
                select(AstNode.node_key).where(
                    AstNode.id == payload.root_node_id,
                    AstNode.ast_payload_id == payload.id,
                )
            )
        if root_node_key != decoded.root_node_key:
            raise ValueError("AST payload blob root key differs from its relational root")
        if (
            payload.node_count != decoded.node_count
            or payload.error_node_count != decoded.error_node_count
        ):
            raise ValueError("AST payload blob counts differ from relational metadata")
        return decoded

    def _decode_blob(self, blob: AstPayloadBlob) -> DecodedAstPayload:
        if blob.encoding_version != ENCODING_VERSION or blob.compression_codec != COMPRESSION_CODEC:
            raise ValueError("AST payload blob uses an unsupported encoding")
        decoded = decode_ast_payload(
            blob.payload_bytes,
            expected_sha256=blob.uncompressed_sha256,
        )
        if (
            blob.uncompressed_bytes != decoded.uncompressed_bytes
            or blob.compressed_bytes != len(blob.payload_bytes)
            or blob.node_count != decoded.node_count
            or blob.error_node_count != decoded.error_node_count
            or blob.root_node_key != decoded.root_node_key
        ):
            raise ValueError("AST payload blob metadata does not match its contents")
        return decoded

    def _records_from_nodes(self, payload: AstPayload) -> list[AstNodeRecord]:
        nodes = self._session.scalars(
            select(AstNode)
            .where(AstNode.ast_payload_id == payload.id)
            .order_by(AstNode.node_key)
        ).all()
        key_by_id = {node.id: node.node_key for node in nodes}
        return [
            AstNodeRecord(
                document_key=payload.document_key,
                node_key=node.node_key,
                parent_node_key=(key_by_id.get(node.parent_node_id) if node.parent_node_id is not None else None),
                sibling_ordinal=node.sibling_ordinal,
                raw_type=node.raw_type,
                category=AstNodeCategory(node.category),
                field_name=node.field_name,
                flags=AstNodeFlags(
                    is_named=node.is_named,
                    is_extra=node.is_extra,
                    is_error=node.is_error,
                    is_missing=node.is_missing,
                    has_error=node.has_error,
                    has_changes=node.has_changes,
                ),
                source_range=AstSourceRange(
                    node.start_byte,
                    node.end_byte,
                    AstPoint(node.start_row, node.start_column),
                    AstPoint(node.end_row, node.end_column),
                ),
                subtree_hash=node.subtree_hash,
                display_name=node.display_name,
                attributes=dict(node.attributes_json),
            )
            for node in nodes
        ]


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
        self._validate_parent_tree(records)
        # The self-reference is deferrable, so one executemany statement can
        # retain the preassigned parent IDs without a flush for every AST
        # depth.  Validation remains in-process: a malformed/cyclic tree
        # fails before any rows are written, while PostgreSQL still validates
        # the parent foreign key at transaction commit.
        self._session.execute(
            insert(cast(Table, AstNode.__table__)),
            [payload_by_key[record.node_key] for record in records],
        )
        self._session.flush()
        packed_payload = self.factory.ast_payload_blobs().create_for_node_records(payload, records)
        payload.root_node_id = key_to_id[roots[0].node_key]
        payload.root_node_key = roots[0].node_key
        payload.node_count = packed_payload.node_count
        payload.error_node_count = packed_payload.error_node_count
        document.root_node_id = payload.root_node_id
        document.root_node_key = payload.root_node_key
        document.node_count = packed_payload.node_count
        document.error_node_count = payload.error_node_count
        self._session.flush()
        return key_to_id

    def persist_packed_for_document(
        self,
        document: AstDocument,
        records: list[AstNodeRecord],
    ) -> None:
        """Persist the canonical payload without adding a relational node projection.

        This is the RA-01 contraction writer for new scans. Existing documents with
        no blob still use ``bulk_create_for_document`` during the expand transition,
        but application parsing must use this method once readers and link writers
        can resolve stable document/key pointers.
        """

        if document.ast_payload_id is None:
            raise ValueError("document must reference an AST payload")
        payload = self._session.get(AstPayload, document.ast_payload_id)
        if payload is None:
            raise ValueError("document AST payload does not exist")
        if any(record.document_key != document.document_key for record in records):
            raise ValueError("every node must match the target document_key")
        if records:
            self._validate_parent_tree(records)

        packed_payload = self.factory.ast_payload_blobs().create_for_node_records(
            payload,
            records,
        )
        payload.root_node_id = None
        payload.root_node_key = packed_payload.root_node_key
        payload.node_count = packed_payload.node_count
        payload.error_node_count = packed_payload.error_node_count
        document.root_node_id = None
        document.root_node_key = packed_payload.root_node_key
        document.node_count = packed_payload.node_count
        document.error_node_count = packed_payload.error_node_count
        self._session.flush()

    @staticmethod
    def _validate_parent_tree(records: list[AstNodeRecord]) -> None:
        """Prove every node is reachable from the one root without SQL flushes."""

        by_parent: dict[str | None, list[str]] = {}
        for record in records:
            by_parent.setdefault(record.parent_node_key, []).append(record.node_key)
        roots = by_parent.get(None, [])
        if len(roots) != 1:
            raise ValueError("a document node batch must contain exactly one root")

        seen: set[str] = set()
        frontier = roots
        while frontier:
            node_key = frontier.pop()
            if node_key in seen:
                continue
            seen.add(node_key)
            frontier.extend(by_parent.get(node_key, ()))
        if len(seen) != len(records):
            unresolved = ", ".join(sorted({record.node_key for record in records} - seen)[:3])
            raise ValueError(f"node parents contain a cycle or missing key: {unresolved}")


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

        decoded = self.factory.ast_payload_blobs().decode_for_documents(
            project_id=document.project_id,
            analysis_version_id=document.analysis_version_id,
            document_ids=(document.id,),
            cache=False,
        ).get(document.id)
        source_node_ids: dict[str, str] = {}
        if decoded is not None:
            source_node_keys = {node.node_key for node in decoded.records}
        else:
            source_node_ids = self._legacy_node_ids(document)
            source_node_keys = set(source_node_ids)
        missing = {
            record.source_node_key
            for record in records
            if record.source_node_key not in source_node_keys
        }
        if missing:
            raise ValueError(f"source nodes are missing from document: {sorted(missing)}")

        target_pointers = self._stable_target_pointers(document, records)
        ast_target_ids = {
            record.target_id
            for record in records
            if self._is_ast_target(record) and record.target_document_key is None
        }
        legacy_target_pointers = {
            node_id: (target_document_id, node_key)
            for node_id, target_document_id, node_key in self._session.execute(
                select(AstNode.id, AstDocument.id, AstNode.node_key)
                .join(AstDocument, AstDocument.ast_payload_id == AstNode.ast_payload_id)
                .where(AstNode.id.in_(ast_target_ids))
            )
        }

        payloads = []
        for record in records:
            target_pointer = (
                target_pointers.get((record.target_document_key, record.target_node_key))
                if record.target_document_key is not None and record.target_node_key is not None
                else None
            )
            legacy_target_pointer = legacy_target_pointers.get(record.target_id)
            if (
                self._is_ast_target(record)
                and target_pointer is None
                and legacy_target_pointer is None
            ):
                raise ValueError(f"target AST node is missing: {record.target_id}")
            typed_targets = self._typed_target(
                record,
                target_ast_node_id=(
                    record.target_id
                    if target_pointer is None and legacy_target_pointer is not None
                    else None
                ),
            )
            if target_pointer is not None:
                typed_targets["target_ast_document_id"] = target_pointer[0]
                typed_targets["target_ast_node_key"] = target_pointer[1]
            elif legacy_target_pointer is not None:
                typed_targets["target_ast_document_id"] = legacy_target_pointer[0]
                typed_targets["target_ast_node_key"] = legacy_target_pointer[1]
            payloads.append(
                {
                    "id": uuid_str(),
                    "ast_document_id": document.id,
                    "ast_node_id": source_node_ids.get(record.source_node_key),
                    "ast_node_key": record.source_node_key,
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

    def _stable_target_pointers(
        self,
        document: AstDocument,
        records: list[AstLinkRecord],
    ) -> dict[tuple[str, str], tuple[str, str]]:
        """Validate supplied packed target pointers without reading relational nodes."""

        target_keys = {
            (record.target_document_key, record.target_node_key)
            for record in records
            if self._is_ast_target(record)
            and record.target_document_key is not None
            and record.target_node_key is not None
        }
        if not target_keys:
            return {}
        documents = {
            target.document_key: target
            for target in self._session.scalars(
                select(AstDocument).where(
                    AstDocument.project_id == document.project_id,
                    AstDocument.analysis_version_id == document.analysis_version_id,
                    AstDocument.document_key.in_({key[0] for key in target_keys}),
                )
            )
        }
        missing_documents = sorted({key[0] for key in target_keys} - documents.keys())
        if missing_documents:
            raise ValueError(f"target documents are missing from analysis: {missing_documents}")

        decoded_by_document: dict[str, DecodedAstPayload] = {}
        targets = list(documents.values())
        blobs = self.factory.ast_payload_blobs()
        for offset in range(0, len(targets), blobs.MAX_DECODE_DOCUMENTS_PER_BATCH):
            batch = targets[offset : offset + blobs.MAX_DECODE_DOCUMENTS_PER_BATCH]
            decoded_by_document.update(
                blobs.decode_for_documents(
                    project_id=document.project_id,
                    analysis_version_id=document.analysis_version_id,
                    document_ids=[target.id for target in batch],
                    cache=False,
                )
            )

        legacy_keys_by_document = {
            target.id: self._legacy_node_ids(target)
            for target in targets
            if target.id not in decoded_by_document
        }
        pointers: dict[tuple[str, str], tuple[str, str]] = {}
        for document_key, node_key in target_keys:
            target = documents[document_key]
            decoded = decoded_by_document.get(target.id)
            available_keys = (
                {node.node_key for node in decoded.records}
                if decoded is not None
                else set(legacy_keys_by_document[target.id])
            )
            if node_key not in available_keys:
                raise ValueError(
                    f"target node is missing from document {document_key}: {node_key}"
                )
            pointers[(document_key, node_key)] = (target.id, node_key)
        return pointers

    def _legacy_node_ids(self, document: AstDocument) -> dict[str, str]:
        rows = self._session.execute(
            select(AstNode.node_key, AstNode.id).where(
                AstNode.ast_payload_id == document.ast_payload_id
            )
        ).tuples().all()
        return dict(cast(list[tuple[str, str]], rows))

    def backfill_stable_node_keys(self, *, limit: int) -> int:
        """Fill one bounded page of legacy link keys from their retained UUID FK."""

        if limit < 1:
            raise ValueError("limit must be at least 1")
        pending = (
            select(AstNodeLink.id, AstNode.node_key)
            .join(AstNode, AstNode.id == AstNodeLink.ast_node_id)
            .where(AstNodeLink.ast_node_key.is_(None))
            .order_by(AstNodeLink.id)
            .limit(limit)
            .cte("pending_ast_node_links")
        )
        result = self._session.execute(
            update(cast(Table, AstNodeLink.__table__))
            .where(AstNodeLink.__table__.c.id == pending.c.id)
            .values(ast_node_key=pending.c.node_key)
            .returning(AstNodeLink.__table__.c.id)
        )
        self._session.flush()
        return len(result.scalars().all())

    def backfill_stable_target_node_pointers(self, *, limit: int) -> int:
        """Fill durable target document/key pointers for legacy AST-to-AST links."""

        if limit < 1:
            raise ValueError("limit must be at least 1")
        source_document = aliased(AstDocument)
        target_document = aliased(AstDocument)
        pending = (
            select(
                AstNodeLink.id,
                target_document.id.label("target_document_id"),
                AstNode.node_key.label("target_node_key"),
            )
            .join(source_document, source_document.id == AstNodeLink.ast_document_id)
            .join(AstNode, AstNode.id == AstNodeLink.target_ast_node_id)
            .join(
                target_document,
                and_(
                    target_document.ast_payload_id == AstNode.ast_payload_id,
                    target_document.project_id == source_document.project_id,
                    target_document.analysis_version_id == source_document.analysis_version_id,
                ),
            )
            .where(
                AstNodeLink.target_ast_node_id.is_not(None),
                or_(
                    AstNodeLink.target_ast_document_id.is_(None),
                    AstNodeLink.target_ast_node_key.is_(None),
                ),
            )
            .order_by(AstNodeLink.id)
            .limit(limit)
            .cte("pending_ast_link_targets")
        )
        table = cast(Table, AstNodeLink.__table__)
        result = self._session.execute(
            update(table)
            .where(table.c.id == pending.c.id)
            .values(
                target_ast_document_id=pending.c.target_document_id,
                target_ast_node_key=pending.c.target_node_key,
            )
            .returning(table.c.id)
        )
        self._session.flush()
        return len(result.scalars().all())

    @staticmethod
    def _is_ast_target(record: AstLinkRecord) -> bool:
        return record.link_type in {
            AstLinkType.CALL_TARGET,
            AstLinkType.DEFINITION,
            AstLinkType.REFERENCE,
        }

    @staticmethod
    def _typed_target(
        record: AstLinkRecord,
        *,
        target_ast_node_id: str | None,
    ) -> dict[str, str | None]:
        targets: dict[str, str | None] = {
            "graph_node_id": None,
            "source_symbol_id": None,
            "rule_evidence_id": None,
            "target_ast_node_id": None,
            "target_ast_document_id": None,
            "target_ast_node_key": None,
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
            targets[field_name] = (
                target_ast_node_id if field_name == "target_ast_node_id" else record.target_id
            )
        return targets


__all__ = [
    "AstDocumentRepository",
    "AstNodeLinkRepository",
    "AstNodeRepository",
    "AstParseRunRepository",
    "AstPayloadBlobRepository",
    "AstPayloadRepository",
]
