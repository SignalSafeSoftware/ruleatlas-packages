"""Domain repositories for sqlPhilosophy slices 2-8."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    ImplementationGap,
)


class GapRepository(BaseRepository[ImplementationGap, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(ImplementationGap, session, factory)

    def get_for_project_version(
        self, gap_id: str, project_id: str, analysis_version_id: str
    ) -> ImplementationGap | None:
        gap = self.get_by_id(gap_id)
        if gap is None or gap.project_id != project_id:
            return None
        if gap.analysis_version_id != analysis_version_id:
            return None
        return gap

    def get_for_project(self, gap_id: str, project_id: str) -> ImplementationGap | None:
        gap = self.get_by_id(gap_id)
        if gap is None or gap.project_id != project_id:
            return None
        return gap

    def list_for_project_version(
        self,
        project_id: str,
        analysis_version_id: str,
        *,
        status: str | None = None,
        priority: str | None = None,
    ) -> list[ImplementationGap]:
        stmt = self.statement().where(
            ImplementationGap.project_id == project_id,
            ImplementationGap.analysis_version_id == analysis_version_id,
        )
        if status:
            stmt = stmt.where(ImplementationGap.status == status)
        if priority:
            stmt = stmt.where(ImplementationGap.priority == priority)
        return list(stmt.order_by(ImplementationGap.created_at.desc()).scalars().all())

    def list_for_project(
        self,
        project_id: str,
        *,
        status: str | None = None,
        priority: str | None = None,
        analysis_version_id: str | None = None,
        order_by_title: bool = False,
    ) -> list[ImplementationGap]:
        stmt = self.statement().where(ImplementationGap.project_id == project_id)
        if analysis_version_id:
            stmt = stmt.where(ImplementationGap.analysis_version_id == analysis_version_id)
        if status:
            stmt = stmt.where(ImplementationGap.status == status)
        if priority:
            stmt = stmt.where(ImplementationGap.priority == priority)
        order = ImplementationGap.title.asc() if order_by_title else ImplementationGap.created_at.desc()
        return list(stmt.order_by(order).scalars().all())

    def list_for_project_by_rule_ids(self, project_id: str, rule_ids: set[str]) -> list[ImplementationGap]:
        if not rule_ids:
            return []
        return list(
            self.statement()
            .where(
                ImplementationGap.project_id == project_id,
                ImplementationGap.rule_id.in_(rule_ids),
            )
            .scalars()
            .all()
        )

    def list_with_rule_id_for_project(
        self, project_id: str, *, analysis_version_id: str | None = None
    ) -> list[ImplementationGap]:
        stmt = self.statement().where(ImplementationGap.project_id == project_id)
        if analysis_version_id:
            stmt = stmt.where(ImplementationGap.analysis_version_id == analysis_version_id)
        return list(stmt.scalars().all())

    def list_for_analysis_version(self, analysis_version_id: str) -> list[ImplementationGap]:
        return list(
            self.statement().where(ImplementationGap.analysis_version_id == analysis_version_id).scalars().all()
        )

    def get_first_for_analysis_version(self, analysis_version_id: str) -> ImplementationGap | None:
        return (
            self.statement()
            .where(ImplementationGap.analysis_version_id == analysis_version_id)
            .limit(1)
            .scalars()
            .first()
        )

    def list_for_project_with_title_ilike(self, project_id: str, title_pattern: str) -> list[ImplementationGap]:
        return list(
            self.statement()
            .where(
                ImplementationGap.project_id == project_id,
                ImplementationGap.title.ilike(title_pattern),
            )
            .scalars()
            .all()
        )

    def count_for_project(self, project_id: str) -> int:
        return self.statement().where(ImplementationGap.project_id == project_id).count()
