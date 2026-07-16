"""Additional domain repositories for full sqlPhilosophy query-boundary coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    AiSuggestion,
)


class AiSuggestionRepository(BaseRepository[AiSuggestion, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(AiSuggestion, session, factory)

    def list_for_project(
        self,
        project_id: str,
        *,
        status: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
    ) -> list[AiSuggestion]:
        stmt = self.statement().where(AiSuggestion.project_id == project_id)
        if status is not None:
            stmt = stmt.where(AiSuggestion.status == status)
        if target_type:
            stmt = stmt.where(AiSuggestion.target_type == target_type)
        if target_id:
            stmt = stmt.where(AiSuggestion.target_id == target_id)
        return list(stmt.order_by(AiSuggestion.created_at.desc()).scalars().all())

    def get_for_project(self, suggestion_id: str, project_id: str) -> AiSuggestion | None:
        row = self.get_by_id(suggestion_id)
        if row is None or row.project_id != project_id:
            return None
        return row
