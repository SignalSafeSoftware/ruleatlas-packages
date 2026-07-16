"""Domain repositories for sqlPhilosophy slices 2-8."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from ruleatlas_contracts.enums import SourceTreeNodeKind
from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    SourceTreeNode,
)


class SourceTreeNodeRepository(BaseRepository[SourceTreeNode, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(SourceTreeNode, session, factory)

    def delete_for_scan(self, project_id: str, scan_run_id: str) -> int:
        from sqlalchemy import delete

        result = self._session.execute(
            delete(SourceTreeNode).where(
                SourceTreeNode.project_id == project_id,
                SourceTreeNode.scan_run_id == scan_run_id,
            )
        )
        rowcount = getattr(result, "rowcount", 0)
        return rowcount if isinstance(rowcount, int) else 0

    def count_for_scan(self, project_id: str, scan_run_id: str) -> int:
        return (
            self.statement()
            .where(
                SourceTreeNode.project_id == project_id,
                SourceTreeNode.scan_run_id == scan_run_id,
            )
            .count()
        )

    def get_folder_by_display_path(self, scan_run_id: str, display_path: str) -> SourceTreeNode | None:
        return (
            self.statement()
            .where(
                SourceTreeNode.scan_run_id == scan_run_id,
                SourceTreeNode.display_path == display_path,
                SourceTreeNode.node_kind == SourceTreeNodeKind.FOLDER,
            )
            .scalars()
            .first()
        )

    def list_children(self, scan_run_id: str, *, parent_id: str | None) -> list[SourceTreeNode]:
        stmt = self.statement().where(SourceTreeNode.scan_run_id == scan_run_id)
        if parent_id:
            stmt = stmt.where(SourceTreeNode.parent_id == parent_id)
        else:
            stmt = stmt.where(SourceTreeNode.parent_id.is_(None))
        return list(stmt.order_by(SourceTreeNode.node_kind.desc(), SourceTreeNode.name.asc()).scalars().all())
