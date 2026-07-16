"""Repository for optional semantic provider observations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import SemanticObservation

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory


class SemanticObservationRepository(BaseRepository[SemanticObservation, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(SemanticObservation, session, factory)

    def list_for_analysis(
        self, project_id: str, analysis_version_id: str, *, limit: int = 200
    ) -> list[SemanticObservation]:
        return list(
            self.statement()
            .where(
                SemanticObservation.project_id == project_id,
                SemanticObservation.analysis_version_id == analysis_version_id,
            )
            .limit(limit)
            .scalars()
            .all()
        )
