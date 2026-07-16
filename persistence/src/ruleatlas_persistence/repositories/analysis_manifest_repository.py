"""Repositories for immutable analysis manifests and manifest files."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ruleatlas_contracts.enums import ManifestInclusionState
from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import AnalysisManifest, AnalysisManifestFile

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory


class AnalysisManifestRepository(BaseRepository[AnalysisManifest, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(AnalysisManifest, session, factory)

    def get_for_scan_run(self, scan_run_id: str) -> AnalysisManifest | None:
        return (
            self.statement()
            .where(AnalysisManifest.scan_run_id == scan_run_id)
            .scalars()
            .first()
        )


class AnalysisManifestFileRepository(BaseRepository[AnalysisManifestFile, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(AnalysisManifestFile, session, factory)

    def list_for_manifest_page(
        self,
        manifest_id: str,
        *,
        included_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[int, list[AnalysisManifestFile]]:
        stmt = self.statement().where(AnalysisManifestFile.manifest_id == manifest_id)
        if included_only:
            stmt = stmt.where(
                AnalysisManifestFile.inclusion_state == ManifestInclusionState.INCLUDED.value
            )
        total = stmt.count()
        rows = list(
            stmt.order_by(AnalysisManifestFile.path.asc())
            .offset(offset)
            .limit(limit)
            .scalars()
            .all()
        )
        return total, rows

    def list_included_ordered(self, manifest_id: str) -> list[AnalysisManifestFile]:
        return list(
            self.statement()
            .where(
                AnalysisManifestFile.manifest_id == manifest_id,
                AnalysisManifestFile.inclusion_state == ManifestInclusionState.INCLUDED.value,
            )
            .order_by(AnalysisManifestFile.path.asc())
            .scalars()
            .all()
        )
