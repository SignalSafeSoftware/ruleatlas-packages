"""Tenant-scoped, bounded read operations for persisted abstract syntax trees."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ruleatlas_contracts.ast import AstNodeCategory, AstNodeRecord
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from ruleatlas_persistence.ast_payload_codec import DecodedAstPayload
from ruleatlas_persistence.models import AstDocument, AstNode, AstNodeLink

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

MAX_PAGE_SIZE = 200
MAX_SUBTREE_DEPTH = 32
MAX_SUBTREE_NODES = 2_000
PACKED_NODE_REFERENCE_PREFIX = "astref:"


@dataclass(frozen=True)
class AstNodeCursor:
    """Stable continuation position within an ordered child collection."""

    sibling_ordinal: int
    node_id: str


@dataclass(frozen=True)
class AstNodePage:
    items: list[AstNode]
    next_cursor: AstNodeCursor | None


@dataclass(frozen=True)
class AstSubtreeNode:
    node: AstNode
    depth: int


@dataclass(frozen=True)
class AstSubtreeResult:
    items: list[AstSubtreeNode]
    truncated: bool


@dataclass(frozen=True)
class _PackedNodeContext:
    document: AstDocument
    payload: DecodedAstPayload
    record: AstNodeRecord


class AstQueryRepository:
    """Read AST data only after establishing project and analysis-version ownership."""

    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        self._session = session
        self._factory = factory

    def get_document(
        self,
        *,
        project_id: str,
        analysis_version_id: str,
        document_id: str,
    ) -> AstDocument | None:
        return self._session.scalar(
            self._document_scope(project_id, analysis_version_id).where(AstDocument.id == document_id)
        )

    def get_document_for_source(
        self,
        *,
        project_id: str,
        analysis_version_id: str,
        source_file_id: str,
    ) -> AstDocument | None:
        return self._session.scalar(
            self._document_scope(project_id, analysis_version_id).where(AstDocument.source_file_id == source_file_id)
        )

    def get_document_for_key(
        self,
        *,
        project_id: str,
        analysis_version_id: str,
        document_key: str,
    ) -> AstDocument | None:
        """Resolve a stable document key only inside the caller's scope."""

        return self._session.scalar(
            self._document_scope(project_id, analysis_version_id).where(
                AstDocument.document_key == document_key
            )
        )

    def get_node(
        self,
        *,
        project_id: str,
        analysis_version_id: str,
        node_id: str,
    ) -> AstNode | None:
        packed = self._packed_node_context(
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            node_id=node_id,
        )
        if packed is not None:
            return self._packed_node(packed.document, packed.record)
        return None

    def get_document_for_node(
        self,
        *,
        project_id: str,
        analysis_version_id: str,
        node_id: str,
    ) -> AstDocument | None:
        packed = self._packed_node_context(
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            node_id=node_id,
        )
        if packed is not None:
            return packed.document
        return None

    def get_parent(
        self,
        *,
        project_id: str,
        analysis_version_id: str,
        node_id: str,
    ) -> AstNode | None:
        child = self.get_node(
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            node_id=node_id,
        )
        if child is None or child.parent_node_id is None:
            return None
        return self.get_node(
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            node_id=child.parent_node_id,
        )

    def list_children(
        self,
        *,
        project_id: str,
        analysis_version_id: str,
        parent_node_id: str,
        limit: int = 100,
        cursor: AstNodeCursor | None = None,
    ) -> AstNodePage:
        page_size = self._bounded_limit(limit)
        packed_parent = self._packed_node_context(
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            node_id=parent_node_id,
        )
        if packed_parent is not None:
            rows = sorted(
                (
                    self._packed_node(packed_parent.document, record)
                    for record in packed_parent.payload.records
                    if record.parent_node_key == packed_parent.record.node_key
                ),
                key=lambda node: (node.sibling_ordinal, node.id),
            )
            if cursor is not None:
                rows = [
                    node
                    for node in rows
                    if (node.sibling_ordinal, node.id) > (cursor.sibling_ordinal, cursor.node_id)
                ]
            has_more = len(rows) > page_size
            items = rows[:page_size]
            next_cursor = AstNodeCursor(items[-1].sibling_ordinal, items[-1].id) if has_more and items else None
            return AstNodePage(items=items, next_cursor=next_cursor)
        return AstNodePage(items=[], next_cursor=None)

    def bounded_subtree(
        self,
        *,
        project_id: str,
        analysis_version_id: str,
        root_node_id: str,
        max_depth: int = 8,
        max_nodes: int = 500,
    ) -> AstSubtreeResult:
        if not 0 <= max_depth <= MAX_SUBTREE_DEPTH:
            raise ValueError(f"max_depth must be between 0 and {MAX_SUBTREE_DEPTH}")
        if not 1 <= max_nodes <= MAX_SUBTREE_NODES:
            raise ValueError(f"max_nodes must be between 1 and {MAX_SUBTREE_NODES}")
        packed_root = self._packed_node_context(
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            node_id=root_node_id,
        )
        if packed_root is not None:
            children_by_parent: dict[str, list[AstNodeRecord]] = {}
            for record in packed_root.payload.records:
                if record.parent_node_key is not None:
                    children_by_parent.setdefault(record.parent_node_key, []).append(record)
            for packed_children in children_by_parent.values():
                packed_children.sort(key=lambda record: (record.sibling_ordinal, record.node_key))
            items = [AstSubtreeNode(self._packed_node(packed_root.document, packed_root.record), 0)]
            frontier = [packed_root.record.node_key]
            depth = 0
            truncated = False
            while frontier and depth < max_depth and len(items) < max_nodes:
                remaining = max_nodes - len(items)
                packed_children = [
                    child
                    for parent_key in frontier
                    for child in children_by_parent.get(parent_key, ())
                ]
                if len(packed_children) > remaining:
                    truncated = True
                    packed_children = packed_children[:remaining]
                depth += 1
                items.extend(
                    AstSubtreeNode(self._packed_node(packed_root.document, node), depth)
                    for node in packed_children
                )
                frontier = [node.node_key for node in packed_children]
            if frontier and (depth == max_depth or len(items) == max_nodes):
                truncated = True
            return AstSubtreeResult(items=items, truncated=truncated)
        return AstSubtreeResult(items=[], truncated=False)

    def search_nodes(
        self,
        *,
        project_id: str,
        analysis_version_id: str,
        document_id: str | None = None,
        raw_types: set[str] | None = None,
        categories: set[AstNodeCategory] | None = None,
        start_byte: int | None = None,
        end_byte: int | None = None,
        limit: int = 100,
    ) -> list[AstNode]:
        page_size = self._bounded_limit(limit)
        if (start_byte is None) != (end_byte is None):
            raise ValueError("start_byte and end_byte must be provided together")
        if start_byte is not None and end_byte is not None and (start_byte < 0 or end_byte <= start_byte):
            raise ValueError("search range must be non-negative and non-empty")

        if document_id is not None:
            document = self.get_document(
                project_id=project_id,
                analysis_version_id=analysis_version_id,
                document_id=document_id,
            )
            if document is not None:
                payload = self._decoded_payload_for_document(
                    project_id=project_id,
                    analysis_version_id=analysis_version_id,
                    document=document,
                )
                if payload is not None:
                    return [
                        self._packed_node(document, record)
                        for record in self._filter_packed_records(
                            payload.records,
                            raw_types=raw_types,
                            categories=categories,
                            start_byte=start_byte,
                            end_byte=end_byte,
                        )[:page_size]
                    ]
        else:
            documents = list(
                self._session.scalars(
                    self._document_scope(project_id, analysis_version_id).order_by(
                        AstDocument.source_path,
                        AstDocument.id,
                    )
                )
            )
            blobs = self._factory.ast_payload_blobs()
            packed_nodes: list[AstNode] = []
            for offset in range(0, len(documents), blobs.MAX_DECODE_DOCUMENTS_PER_BATCH):
                batch = documents[offset : offset + blobs.MAX_DECODE_DOCUMENTS_PER_BATCH]
                decoded_by_document = blobs.decode_for_documents(
                    project_id=project_id,
                    analysis_version_id=analysis_version_id,
                    document_ids=[document.id for document in batch],
                    cache=False,
                )
                if len(decoded_by_document) != len(batch):
                    raise ValueError("AST analysis contains a document without a packed payload")
                for document in batch:
                    records = sorted(
                        self._filter_packed_records(
                            decoded_by_document[document.id].records,
                            raw_types=raw_types,
                            categories=categories,
                            start_byte=start_byte,
                            end_byte=end_byte,
                        ),
                        key=lambda record: (
                            record.source_range.start_byte,
                            record.source_range.end_byte,
                            record.node_key,
                        ),
                    )
                    for record in records:
                        packed_nodes.append(self._packed_node(document, record))
                        if len(packed_nodes) == page_size:
                            return packed_nodes
            return packed_nodes

        return []

    def find_containing_node(
        self,
        *,
        project_id: str,
        analysis_version_id: str,
        document_id: str,
        byte_offset: int,
    ) -> AstNode | None:
        if byte_offset < 0:
            raise ValueError("byte_offset must be non-negative")
        document = self.get_document(
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            document_id=document_id,
        )
        if document is not None:
            payload = self._decoded_payload_for_document(
                project_id=project_id,
                analysis_version_id=analysis_version_id,
                document=document,
            )
            if payload is not None:
                candidates = [
                    record
                    for record in payload.records
                    if record.source_range.start_byte <= byte_offset < record.source_range.end_byte
                ]
                if not candidates:
                    return None
                best = min(
                    candidates,
                    key=lambda record: (
                        record.source_range.byte_length,
                        -record.source_range.start_byte,
                        record.node_key,
                    ),
                )
                return self._packed_node(document, best)
        return None

    def list_definitions(
        self,
        *,
        project_id: str,
        analysis_version_id: str,
        document_id: str | None = None,
        limit: int = 100,
    ) -> list[AstNode]:
        definitions = {
            AstNodeCategory.TYPE_DEFINITION,
            AstNodeCategory.CLASS_DEFINITION,
            AstNodeCategory.INTERFACE_DEFINITION,
            AstNodeCategory.FUNCTION_DEFINITION,
            AstNodeCategory.METHOD_DEFINITION,
        }
        return self.search_nodes(
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            document_id=document_id,
            categories=definitions,
            limit=limit,
        )

    def list_links_for_node(
        self,
        *,
        project_id: str,
        analysis_version_id: str,
        node_id: str,
        link_types: set[str] | None = None,
        limit: int = 100,
    ) -> list[AstNodeLink]:
        page_size = self._bounded_limit(limit)
        packed = self._packed_node_context(
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            node_id=node_id,
        )
        if packed is not None:
            statement = select(AstNodeLink).where(
                AstNodeLink.ast_document_id == packed.document.id,
                AstNodeLink.ast_node_key == packed.record.node_key,
            )
        else:
            return []
        if link_types:
            statement = statement.where(AstNodeLink.link_type.in_(link_types))
        return list(
            self._session.scalars(
                statement.order_by(AstNodeLink.link_type, AstNodeLink.target_type, AstNodeLink.target_id).limit(
                    page_size
                )
            )
        )

    @staticmethod
    def packed_node_reference(document_key: str, node_key: str) -> str:
        """Return an opaque, deterministic node ID independent of a database UUID."""

        value = json.dumps([document_key, node_key], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        encoded = base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
        return f"{PACKED_NODE_REFERENCE_PREFIX}{encoded}"

    def _packed_node_context(
        self,
        *,
        project_id: str,
        analysis_version_id: str,
        node_id: str,
    ) -> _PackedNodeContext | None:
        reference = self._decode_node_reference(node_id)
        if reference is None:
            return None
        document_key, node_key = reference
        document = self._session.scalar(
            self._document_scope(project_id, analysis_version_id).where(AstDocument.document_key == document_key)
        )
        if document is None:
            return None
        payload = self._decoded_payload_for_document(
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            document=document,
        )
        if payload is None:
            return None
        record = next((item for item in payload.records if item.node_key == node_key), None)
        if record is None:
            return None
        return _PackedNodeContext(document=document, payload=payload, record=record)

    def _decoded_payload_for_document(
        self,
        *,
        project_id: str,
        analysis_version_id: str,
        document: AstDocument,
    ) -> DecodedAstPayload | None:
        return self._factory.ast_payload_blobs().decode_for_document(
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            document_id=document.id,
        )

    @classmethod
    def _packed_node(cls, document: AstDocument, record: AstNodeRecord) -> AstNode:
        """Adapt a packed record to the existing ORM-shaped read contract.

        The object is deliberately transient: read callers may keep using the
        existing ``AstNode`` fields, but its IDs are packed references rather
        than persistence UUIDs and must never be flushed.
        """

        return AstNode(
            id=cls.packed_node_reference(document.document_key, record.node_key),
            ast_payload_id=document.ast_payload_id,
            parent_node_id=(
                cls.packed_node_reference(document.document_key, record.parent_node_key)
                if record.parent_node_key is not None
                else None
            ),
            node_key=record.node_key,
            sibling_ordinal=record.sibling_ordinal,
            raw_type=record.raw_type,
            category=record.category.value,
            field_name=record.field_name,
            is_named=record.flags.is_named,
            is_extra=record.flags.is_extra,
            is_error=record.flags.is_error,
            is_missing=record.flags.is_missing,
            has_error=record.flags.has_error,
            has_changes=record.flags.has_changes,
            start_byte=record.source_range.start_byte,
            end_byte=record.source_range.end_byte,
            start_row=record.source_range.start_point.row,
            start_column=record.source_range.start_point.column,
            end_row=record.source_range.end_point.row,
            end_column=record.source_range.end_point.column,
            subtree_hash=record.subtree_hash,
            display_name=record.display_name,
            attributes_json=dict(record.attributes),
        )

    @staticmethod
    def _filter_packed_records(
        records: tuple[AstNodeRecord, ...],
        *,
        raw_types: set[str] | None,
        categories: set[AstNodeCategory] | None,
        start_byte: int | None,
        end_byte: int | None,
    ) -> list[AstNodeRecord]:
        category_values = {item.value for item in categories} if categories else None
        filtered = [
            record
            for record in records
            if (not raw_types or record.raw_type in raw_types)
            and (not category_values or record.category.value in category_values)
            and (
                start_byte is None
                or end_byte is None
                or (
                    record.source_range.start_byte < end_byte
                    and record.source_range.end_byte > start_byte
                )
            )
        ]
        return sorted(
            filtered,
            key=lambda record: (record.source_range.start_byte, record.source_range.end_byte, record.node_key),
        )

    @staticmethod
    def _decode_node_reference(node_id: str) -> tuple[str, str] | None:
        if not node_id.startswith(PACKED_NODE_REFERENCE_PREFIX):
            return None
        encoded = node_id.removeprefix(PACKED_NODE_REFERENCE_PREFIX)
        try:
            decoded = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
            value = json.loads(decoded.decode("utf-8"))
        except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
            return None
        if (
            not isinstance(value, list)
            or len(value) != 2
            or not all(isinstance(item, str) and item for item in value)
        ):
            return None
        return value[0], value[1]

    @staticmethod
    def _bounded_limit(limit: int) -> int:
        if not 1 <= limit <= MAX_PAGE_SIZE:
            raise ValueError(f"limit must be between 1 and {MAX_PAGE_SIZE}")
        return limit

    @staticmethod
    def _document_scope(project_id: str, analysis_version_id: str) -> Select[tuple[AstDocument]]:
        return select(AstDocument).where(
            AstDocument.project_id == project_id,
            AstDocument.analysis_version_id == analysis_version_id,
        )

__all__ = [
    "MAX_PAGE_SIZE",
    "MAX_SUBTREE_DEPTH",
    "MAX_SUBTREE_NODES",
    "PACKED_NODE_REFERENCE_PREFIX",
    "AstNodeCursor",
    "AstNodePage",
    "AstQueryRepository",
    "AstSubtreeNode",
    "AstSubtreeResult",
]
