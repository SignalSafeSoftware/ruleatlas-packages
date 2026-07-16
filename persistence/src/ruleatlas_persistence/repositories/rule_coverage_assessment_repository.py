"""Additional domain repositories for full sqlPhilosophy query-boundary coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    Rule,
    RuleCoverageAssessment,
)


class RuleCoverageAssessmentRepository(BaseRepository[RuleCoverageAssessment, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(RuleCoverageAssessment, session, factory)

    def list_with_rules_for_project(
        self,
        project_id: str,
        *,
        analysis_version_id: str | None = None,
        rule_id: str | None = None,
    ) -> list[tuple[RuleCoverageAssessment, Rule]]:
        stmt = (
            self.statement()
            .select_columns(RuleCoverageAssessment, Rule)
            .join(Rule, RuleCoverageAssessment.rule_id == Rule.id)
            .where(Rule.project_id == project_id)
            .order_by(RuleCoverageAssessment.created_at.desc())
        )
        if analysis_version_id:
            stmt = stmt.where(Rule.analysis_version_id == analysis_version_id)
        if rule_id:
            stmt = stmt.where(Rule.id == rule_id)
        return [
            (cast(RuleCoverageAssessment, row[0]), cast(Rule, row[1]))
            for row in self._session.execute(stmt.build_select()).all()
        ]

    def count_for_project(self, project_id: str) -> int:
        return (
            self.statement()
            .join(Rule, RuleCoverageAssessment.rule_id == Rule.id)
            .where(Rule.project_id == project_id)
            .count()
        )

    def list_for_project_joined_rules(
        self,
        project_id: str,
        *,
        analysis_version_id: str | None = None,
    ) -> list[tuple[RuleCoverageAssessment, Rule]]:
        stmt = (
            self.statement()
            .select_columns(RuleCoverageAssessment, Rule)
            .join(Rule, RuleCoverageAssessment.rule_id == Rule.id)
            .where(Rule.project_id == project_id)
            .order_by(Rule.name.asc())
        )
        if analysis_version_id:
            stmt = stmt.where(Rule.analysis_version_id == analysis_version_id)
        return [
            (cast(RuleCoverageAssessment, row[0]), cast(Rule, row[1]))
            for row in self._session.execute(stmt.build_select()).all()
        ]

    def get_first_for_project_joined_rules(self, project_id: str) -> tuple[RuleCoverageAssessment, Rule] | None:
        rows = self.list_for_project_joined_rules(project_id)
        return rows[0] if rows else None

    def list_for_rule(self, rule_id: str) -> list[RuleCoverageAssessment]:
        return list(self.statement().where(RuleCoverageAssessment.rule_id == rule_id).scalars().all())
