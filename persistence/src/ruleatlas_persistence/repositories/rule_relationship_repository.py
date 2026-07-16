"""Additional domain repositories for full sqlPhilosophy query-boundary coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    RuleRelationship,
)


class RuleRelationshipRepository(BaseRepository[RuleRelationship, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(RuleRelationship, session, factory)

    def list_for_project(self, project_id: str) -> list[RuleRelationship]:
        return list(self.statement().where(RuleRelationship.project_id == project_id).scalars().all())

    def list_for_analysis_version(self, analysis_version_id: str) -> list[RuleRelationship]:
        return list(self.statement().where(RuleRelationship.analysis_version_id == analysis_version_id).scalars().all())

    def list_parent_of_incoming_for_rule(self, rule_id: str) -> list[RuleRelationship]:
        return list(self.statement().where(RuleRelationship.to_rule_id == rule_id).scalars().all())

    def list_parent_of_incoming_for_rule_in_project(self, project_id: str, rule_id: str) -> list[RuleRelationship]:
        return list(
            self.statement()
            .where(
                RuleRelationship.project_id == project_id,
                RuleRelationship.relationship_type == "parent_of",
                RuleRelationship.to_rule_id == rule_id,
            )
            .scalars()
            .all()
        )

    def get_by_project_rules_and_type(
        self,
        project_id: str,
        from_rule_id: str,
        to_rule_id: str,
        relationship_type: Any,
    ) -> RuleRelationship | None:
        return (
            self.statement()
            .where(
                RuleRelationship.project_id == project_id,
                RuleRelationship.from_rule_id == from_rule_id,
                RuleRelationship.to_rule_id == to_rule_id,
                RuleRelationship.relationship_type == relationship_type,
            )
            .scalars()
            .first()
        )
