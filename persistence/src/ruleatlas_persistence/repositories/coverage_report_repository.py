"""Additional domain repositories for full sqlPhilosophy query-boundary coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    CoverageFile,
    CoverageLine,
    CoverageReport,
)
from ruleatlas_persistence.repositories.coverage_file_repository import CoverageFileRepository
from ruleatlas_persistence.repositories.coverage_line_repository import CoverageLineRepository

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory


class CoverageReportRepository(BaseRepository[CoverageReport, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(CoverageReport, session, factory)
        self._files = factory.get_repository(CoverageFileRepository)
        self._lines = factory.get_repository(CoverageLineRepository)

    def list_for_project(self, project_id: str, *, analysis_version_id: str | None = None) -> list[CoverageReport]:
        stmt = self.statement().where(CoverageReport.project_id == project_id)
        if analysis_version_id:
            stmt = stmt.where(CoverageReport.analysis_version_id == analysis_version_id)
        return list(stmt.order_by(CoverageReport.created_at.desc()).scalars().all())

    def get_latest_for_project(self, project_id: str) -> CoverageReport | None:
        return (
            self.statement()
            .where(CoverageReport.project_id == project_id)
            .order_by(CoverageReport.created_at.desc())
            .limit(1)
            .scalars()
            .first()
        )

    def count_for_project(self, project_id: str) -> int:
        return self.statement().where(CoverageReport.project_id == project_id).count()

    def list_for_project_version(self, project_id: str, analysis_version_id: str) -> list[CoverageReport]:
        return list(
            self.statement()
            .where(
                CoverageReport.project_id == project_id,
                CoverageReport.analysis_version_id == analysis_version_id,
            )
            .scalars()
            .all()
        )

    def report_ids_for_project(self, project_id: str) -> list[str]:
        return [
            str(report_id)
            for report_id in (
            self.statement()
            .select_columns(CoverageReport.id)
            .where(CoverageReport.project_id == project_id)
            .scalars()
            .all()
            )
        ]

    def file_ids_for_project(self, project_id: str) -> list[str]:
        report_ids = self.report_ids_for_project(project_id)
        if not report_ids:
            return []
        return [
            str(file_id)
            for file_id in (
            self._files.statement()
            .select_columns(CoverageFile.id)
            .where(CoverageFile.coverage_report_id.in_(report_ids))
            .scalars()
            .all()
            )
        ]

    def line_ids_for_project(self, project_id: str) -> list[str]:
        file_ids = self.file_ids_for_project(project_id)
        if not file_ids:
            return []
        return [
            str(line_id)
            for line_id in (
            self._lines.statement()
            .select_columns(CoverageLine.id)
            .where(CoverageLine.coverage_file_id.in_(file_ids))
            .scalars()
            .all()
            )
        ]

    def list_lines_for_project(self, project_id: str) -> list[CoverageLine]:
        return list(
            self._lines.statement()
            .join(CoverageFile, CoverageLine.coverage_file_id == CoverageFile.id)
            .join(CoverageReport, CoverageFile.coverage_report_id == CoverageReport.id)
            .where(CoverageReport.project_id == project_id)
            .scalars()
            .all()
        )
