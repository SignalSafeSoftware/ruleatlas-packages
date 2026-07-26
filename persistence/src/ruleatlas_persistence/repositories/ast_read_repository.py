"""Tenant-scoped, bounded read operations for persisted abstract syntax trees."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ruleatlas_contracts.ast import AstNodeCategory
from sqlalchemy import Select, and_, or_, select
from sqlalchemy.orm import Session

from ruleatlas_persistence.models import AstDocument, AstNode, AstNodeLink

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

MAX_PAGE_SIZE = 200
MAX_SUBTREE_DEPTH = 32
MAX_SUBTREE_NODES = 2_000


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

    def get_node(
        self,
        *,
        project_id: str,
        analysis_version_id: str,
        node_id: str,
    ) -> AstNode | None:
        return self._session.scalar(self._node_scope(project_id, analysis_version_id).where(AstNode.id == node_id))

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
        parent = self.get_node(
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            node_id=parent_node_id,
        )
        if parent is None:
            return AstNodePage(items=[], next_cursor=None)
        statement = self._node_scope(project_id, analysis_version_id).where(
            AstNode.ast_document_id == parent.ast_document_id,
            AstNode.parent_node_id == parent.id,
        )
        if cursor is not None:
            statement = statement.where(
                or_(
                    AstNode.sibling_ordinal > cursor.sibling_ordinal,
                    and_(
                        AstNode.sibling_ordinal == cursor.sibling_ordinal,
                        AstNode.id > cursor.node_id,
                    ),
                )
            )
        rows = list(self._session.scalars(statement.order_by(AstNode.sibling_ordinal, AstNode.id).limit(page_size + 1)))
        has_more = len(rows) > page_size
        items = rows[:page_size]
        next_cursor = AstNodeCursor(items[-1].sibling_ordinal, items[-1].id) if has_more and items else None
        return AstNodePage(items=items, next_cursor=next_cursor)

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
        root = self.get_node(
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            node_id=root_node_id,
        )
        if root is None:
            return AstSubtreeResult(items=[], truncated=False)

        items = [AstSubtreeNode(root, 0)]
        frontier = [root.id]
        depth = 0
        truncated = False
        while frontier and depth < max_depth and len(items) < max_nodes:
            remaining = max_nodes - len(items)
            children = list(
                self._session.scalars(
                    self._node_scope(project_id, analysis_version_id)
                    .where(
                        AstNode.ast_document_id == root.ast_document_id,
                        AstNode.parent_node_id.in_(frontier),
                    )
                    .order_by(AstNode.parent_node_id, AstNode.sibling_ordinal, AstNode.id)
                    .limit(remaining + 1)
                )
            )
            if len(children) > remaining:
                truncated = True
                children = children[:remaining]
            depth += 1
            items.extend(AstSubtreeNode(node, depth) for node in children)
            frontier = [node.id for node in children]
        if frontier and (depth == max_depth or len(items) == max_nodes):
            truncated = True
        return AstSubtreeResult(items=items, truncated=truncated)

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

        statement = self._node_scope(project_id, analysis_version_id)
        if document_id is not None:
            statement = statement.where(AstNode.ast_document_id == document_id)
        if raw_types:
            statement = statement.where(AstNode.raw_type.in_(raw_types))
        if categories:
            statement = statement.where(AstNode.category.in_([item.value for item in categories]))
        if start_byte is not None and end_byte is not None:
            statement = statement.where(
                AstNode.start_byte < end_byte,
                AstNode.end_byte > start_byte,
            )
        return list(
            self._session.scalars(
                statement.order_by(
                    AstDocument.source_path,
                    AstNode.start_byte,
                    AstNode.end_byte,
                    AstNode.id,
                ).limit(page_size)
            )
        )

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
        return self._session.scalar(
            self._node_scope(project_id, analysis_version_id)
            .where(
                AstNode.ast_document_id == document_id,
                AstNode.start_byte <= byte_offset,
                AstNode.end_byte > byte_offset,
            )
            .order_by(
                (AstNode.end_byte - AstNode.start_byte),
                AstNode.start_byte.desc(),
                AstNode.id,
            )
            .limit(1)
        )

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
        statement = (
            select(AstNodeLink)
            .join(AstNode, AstNode.id == AstNodeLink.ast_node_id)
            .join(AstDocument, AstDocument.id == AstNode.ast_document_id)
            .where(
                AstDocument.project_id == project_id,
                AstDocument.analysis_version_id == analysis_version_id,
                AstNode.id == node_id,
            )
        )
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

    @staticmethod
    def _node_scope(project_id: str, analysis_version_id: str) -> Select[tuple[AstNode]]:
        return (
            select(AstNode)
            .join(AstDocument, AstDocument.id == AstNode.ast_document_id)
            .where(
                AstDocument.project_id == project_id,
                AstDocument.analysis_version_id == analysis_version_id,
            )
        )


__all__ = [
    "MAX_PAGE_SIZE",
    "MAX_SUBTREE_DEPTH",
    "MAX_SUBTREE_NODES",
    "AstNodeCursor",
    "AstNodePage",
    "AstQueryRepository",
    "AstSubtreeNode",
    "AstSubtreeResult",
]
