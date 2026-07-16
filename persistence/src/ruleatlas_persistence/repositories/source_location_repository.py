"""Additional domain repositories for full sqlPhilosophy query-boundary coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    SourceLocation,
)


class SourceLocationRepository(BaseRepository[SourceLocation, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(SourceLocation, session, factory)

    def list_for_project(self, project_id: str, *, source_location_id: str | None = None) -> list[SourceLocation]:
        stmt = self.statement().where(SourceLocation.project_id == project_id)
        if source_location_id:
            stmt = stmt.where(SourceLocation.id == source_location_id)
        return list(stmt.order_by(SourceLocation.name.asc()).scalars().all())

    def list_enabled_for_project(self, project_id: str) -> list[SourceLocation]:
        return list(
            self.statement()
            .where(
                SourceLocation.project_id == project_id,
                SourceLocation.enabled.is_(True),
            )
            .scalars()
            .all()
        )

    def count_for_project(self, project_id: str) -> int:
        return self.statement().where(SourceLocation.project_id == project_id).count()

    def get_by_project_and_path(self, project_id: str, path_or_url: str) -> SourceLocation | None:
        return self.first(project_id=project_id, path_or_url=path_or_url)

    def get_for_project(self, location_id: str, project_id: str) -> SourceLocation | None:
        location = self.get_by_id(location_id)
        if location is None or location.project_id != project_id:
            return None
        return location
