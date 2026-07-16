"""Domain repositories for sqlPhilosophy slices 2-8."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from ruleatlas_contracts.enums import RuleConflictStatus
from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    RuleConflict,
)


class ConflictRepository(BaseRepository[RuleConflict, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(RuleConflict, session, factory)

    def get_for_project_version(
        self, conflict_id: str, project_id: str, analysis_version_id: str
    ) -> RuleConflict | None:
        conflict = self.get_by_id(conflict_id)
        if conflict is None or conflict.project_id != project_id:
            return None
        if conflict.analysis_version_id != analysis_version_id:
            return None
        return conflict

    def get_for_project(self, conflict_id: str, project_id: str) -> RuleConflict | None:
        conflict = self.get_by_id(conflict_id)
        if conflict is None or conflict.project_id != project_id:
            return None
        return conflict

    def list_for_project_version(
        self,
        project_id: str,
        analysis_version_id: str,
        *,
        status: str | None = None,
    ) -> list[RuleConflict]:
        stmt = self.statement().where(
            RuleConflict.project_id == project_id,
            RuleConflict.analysis_version_id == analysis_version_id,
        )
        if status:
            stmt = stmt.where(RuleConflict.status == status)
        return list(stmt.order_by(RuleConflict.created_at.desc()).scalars().all())

    def list_for_project(
        self,
        project_id: str,
        *,
        status: str | None = None,
        analysis_version_id: str | None = None,
        order_by_area: bool = False,
    ) -> list[RuleConflict]:
        stmt = self.statement().where(RuleConflict.project_id == project_id)
        if analysis_version_id:
            stmt = stmt.where(RuleConflict.analysis_version_id == analysis_version_id)
        if status:
            stmt = stmt.where(RuleConflict.status == status)
        order = RuleConflict.area.asc() if order_by_area else RuleConflict.created_at.desc()
        return list(stmt.order_by(order).scalars().all())

    def list_for_project_by_rule_ids(self, project_id: str, rule_ids: set[str]) -> list[RuleConflict]:
        if not rule_ids:
            return []
        return list(
            self.statement()
            .where(
                RuleConflict.project_id == project_id,
                RuleConflict.rule_id.in_(rule_ids),
            )
            .scalars()
            .all()
        )

    def list_non_ignored_for_rule(self, rule_id: str) -> list[RuleConflict]:
        return list(
            self.statement()
            .where(
                RuleConflict.rule_id == rule_id,
                RuleConflict.status != RuleConflictStatus.IGNORED,
            )
            .scalars()
            .all()
        )

    def list_with_rule_id_for_project(
        self, project_id: str, *, analysis_version_id: str | None = None
    ) -> list[RuleConflict]:
        stmt = self.statement().where(RuleConflict.project_id == project_id)
        if analysis_version_id:
            stmt = stmt.where(RuleConflict.analysis_version_id == analysis_version_id)
        return list(stmt.scalars().all())

    def list_for_analysis_version(self, analysis_version_id: str) -> list[RuleConflict]:
        return list(self.statement().where(RuleConflict.analysis_version_id == analysis_version_id).scalars().all())

    def get_first_for_analysis_version(self, analysis_version_id: str) -> RuleConflict | None:
        return (
            self.statement().where(RuleConflict.analysis_version_id == analysis_version_id).limit(1).scalars().first()
        )

    def get_first_for_project(self, project_id: str) -> RuleConflict | None:
        return self.statement().where(RuleConflict.project_id == project_id).limit(1).scalars().first()

    def count_for_project(self, project_id: str) -> int:
        return self.statement().where(RuleConflict.project_id == project_id).count()
