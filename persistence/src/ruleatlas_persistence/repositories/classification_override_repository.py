"""Additional domain repositories for full sqlPhilosophy query-boundary coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    ClassificationOverride,
)


class ClassificationOverrideRepository(BaseRepository[ClassificationOverride, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(ClassificationOverride, session, factory)

    def list_for_project(self, project_id: str) -> list[ClassificationOverride]:
        return list(
            self.statement()
            .where(ClassificationOverride.project_id == project_id)
            .order_by(ClassificationOverride.pattern.asc())
            .scalars()
            .all()
        )

    def max_updated_at_for_project(self, project_id: str) -> datetime | None:
        return (
            self.statement()
            .select_columns(func.max(ClassificationOverride.updated_at))
            .where(ClassificationOverride.project_id == project_id)
            .scalar()
        )

    def get_by_project_and_pattern(self, project_id: str, pattern: str) -> ClassificationOverride | None:
        return self.first(project_id=project_id, pattern=pattern)

    def get_by_project_and_pattern_except(
        self, project_id: str, pattern: str, except_id: str
    ) -> ClassificationOverride | None:
        return (
            self.statement()
            .where(
                ClassificationOverride.project_id == project_id,
                ClassificationOverride.pattern == pattern,
                ClassificationOverride.id != except_id,
            )
            .scalars()
            .first()
        )

    def map_patterns_by_ids(self, override_ids: set[str]) -> dict[str, str]:
        if not override_ids:
            return {}
        rows = list(self.statement().where(ClassificationOverride.id.in_(override_ids)).scalars().all())
        return {row.id: row.pattern for row in rows}
