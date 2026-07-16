"""Additional domain repositories for full sqlPhilosophy query-boundary coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from ruleatlas_contracts.enums import (
    RelationshipSuggestionStatus,
)
from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    RuleRelationshipSuggestion,
)


class RuleRelationshipSuggestionRepository(BaseRepository[RuleRelationshipSuggestion, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(RuleRelationshipSuggestion, session, factory)

    def list_for_project(
        self,
        project_id: str,
        *,
        analysis_version_id: str | None = None,
        status: Any=None,
    ) -> list[RuleRelationshipSuggestion]:
        stmt = self.statement().where(RuleRelationshipSuggestion.project_id == project_id)
        if analysis_version_id:
            stmt = stmt.where(RuleRelationshipSuggestion.analysis_version_id == analysis_version_id)
        if status is not None:
            stmt = stmt.where(RuleRelationshipSuggestion.status == status)
        return list(stmt.scalars().all())

    def list_rejected_for_project(self, project_id: str) -> list[RuleRelationshipSuggestion]:
        return list(
            self.statement()
            .where(
                RuleRelationshipSuggestion.project_id == project_id,
                RuleRelationshipSuggestion.status == RelationshipSuggestionStatus.REJECTED,
            )
            .scalars()
            .all()
        )

    def get_for_project(self, suggestion_id: str, project_id: str) -> RuleRelationshipSuggestion | None:
        suggestion = self.get_by_id(suggestion_id)
        if suggestion is None or suggestion.project_id != project_id:
            return None
        return suggestion

    def get_by_unique_key(
        self,
        project_id: str,
        analysis_version_id: str | None,
        source_rule_id: str,
        target_rule_id: str,
        suggested_relationship_type: Any,
    ) -> RuleRelationshipSuggestion | None:
        stmt = self.statement().where(
            RuleRelationshipSuggestion.project_id == project_id,
            RuleRelationshipSuggestion.source_rule_id == source_rule_id,
            RuleRelationshipSuggestion.target_rule_id == target_rule_id,
            RuleRelationshipSuggestion.suggested_relationship_type == suggested_relationship_type,
        )
        if analysis_version_id:
            stmt = stmt.where(RuleRelationshipSuggestion.analysis_version_id == analysis_version_id)
        return stmt.scalars().first()
