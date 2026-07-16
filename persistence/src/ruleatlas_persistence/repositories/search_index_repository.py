"""Domain repositories for sqlPhilosophy slices 2-8."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    SearchIndexRecord,
)


class SearchIndexRepository(BaseRepository[SearchIndexRecord, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(SearchIndexRecord, session, factory)

    def count_for_version(self, project_id: str, analysis_version_id: str) -> int:
        return (
            self.statement()
            .where(
                SearchIndexRecord.project_id == project_id,
                SearchIndexRecord.analysis_version_id == analysis_version_id,
            )
            .count()
        )

    def count_for_project(self, project_id: str) -> int:
        return self.statement().where(SearchIndexRecord.project_id == project_id).count()

    def get_first_for_project(self, project_id: str) -> SearchIndexRecord | None:
        return self.statement().where(SearchIndexRecord.project_id == project_id).limit(1).scalars().first()

    def list_ids_for_project_version(self, project_id: str, analysis_version_id: str) -> list[str]:
        return cast(
            list[str],
            self.statement()
            .select_columns(SearchIndexRecord.id)
            .where(
                SearchIndexRecord.project_id == project_id,
                SearchIndexRecord.analysis_version_id == analysis_version_id,
            )
            .scalars()
            .all(),
        )

    def list_entity_ids_for_project_version(self, project_id: str, analysis_version_id: str) -> list[str]:
        return cast(
            list[str],
            self.statement()
            .select_columns(SearchIndexRecord.entity_id)
            .where(
                SearchIndexRecord.project_id == project_id,
                SearchIndexRecord.analysis_version_id == analysis_version_id,
            )
            .scalars()
            .all(),
        )

    def get_by_entity(
        self,
        project_id: str,
        entity_type: str,
        entity_id: str,
        *,
        analysis_version_id: str | None = None,
    ) -> SearchIndexRecord | None:
        stmt = self.statement().where(
            SearchIndexRecord.project_id == project_id,
            SearchIndexRecord.entity_type == entity_type,
            SearchIndexRecord.entity_id == entity_id,
        )
        if analysis_version_id:
            stmt = stmt.where(SearchIndexRecord.analysis_version_id == analysis_version_id)
        return stmt.scalars().first()

    def list_for_project(
        self,
        project_id: str,
        *,
        analysis_version_id: str | None = None,
        entity_types: list[str] | None = None,
    ) -> list[SearchIndexRecord]:
        stmt = self.statement().where(SearchIndexRecord.project_id == project_id)
        if analysis_version_id:
            stmt = stmt.where(SearchIndexRecord.analysis_version_id == analysis_version_id)
        if entity_types:
            stmt = stmt.where(SearchIndexRecord.entity_type.in_(entity_types))
        return list(stmt.scalars().all())

    def upsert_record(
        self,
        *,
        project_id: str,
        analysis_version_id: str | None,
        entity_type: Any,
        entity_id: str,
        text: str,
        metadata: dict,
    ) -> None:
        entity_type_value = entity_type.value if hasattr(entity_type, "value") else str(entity_type)
        existing = self.get_by_entity(
            project_id,
            entity_type_value,
            entity_id,
            analysis_version_id=analysis_version_id,
        )
        if existing is None:
            self._session.add(
                SearchIndexRecord(
                    project_id=project_id,
                    analysis_version_id=analysis_version_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    text=text,
                    metadata_json=metadata,
                )
            )
        else:
            existing.text = text
            existing.metadata_json = metadata
            self._session.add(existing)

    def delete_for_project(self, project_id: str, *, analysis_version_id: str | None = None) -> None:
        from sqlalchemy import delete

        stmt = delete(SearchIndexRecord).where(SearchIndexRecord.project_id == project_id)
        if analysis_version_id:
            stmt = stmt.where(SearchIndexRecord.analysis_version_id == analysis_version_id)
        self._session.execute(stmt)
