"""Additional domain repositories for full sqlPhilosophy query-boundary coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    RuntimeEvidenceImport,
)


class RuntimeEvidenceImportRepository(BaseRepository[RuntimeEvidenceImport, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(RuntimeEvidenceImport, session, factory)

    def list_ids_for_project_version(self, project_id: str, analysis_version_id: str) -> list[str]:
        return [
            str(import_id)
            for import_id in (
            self.statement()
            .select_columns(RuntimeEvidenceImport.id)
            .where(
                RuntimeEvidenceImport.project_id == project_id,
                RuntimeEvidenceImport.analysis_version_id == analysis_version_id,
            )
            .scalars()
            .all()
            )
        ]

    def list_for_project_version(self, project_id: str, analysis_version_id: str) -> list[RuntimeEvidenceImport]:
        return list(
            self.statement()
            .where(
                RuntimeEvidenceImport.project_id == project_id,
                RuntimeEvidenceImport.analysis_version_id == analysis_version_id,
            )
            .scalars()
            .all()
        )

    def list_for_project(
        self, project_id: str, *, analysis_version_id: str | None = None
    ) -> list[RuntimeEvidenceImport]:
        stmt = self.statement().where(RuntimeEvidenceImport.project_id == project_id)
        if analysis_version_id:
            stmt = stmt.where(RuntimeEvidenceImport.analysis_version_id == analysis_version_id)
        return list(stmt.order_by(RuntimeEvidenceImport.created_at.desc()).scalars().all())
