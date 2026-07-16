from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from ruleatlas_contracts.enums import ScanStatus, ScanType
from sqlalchemy.orm import Session
from sqlphilosophy.sorting import ListQuery
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    ScanRun,
)

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory


class ScanRunRepository(BaseRepository[ScanRun, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(ScanRun, session, factory)

    def get_for_project(self, scan_run_id: str, project_id: str) -> ScanRun | None:
        scan_run = self.get_by_id(scan_run_id)
        if scan_run is None or scan_run.project_id != project_id:
            return None
        return scan_run

    def list_for_project(self, project_id: str, query: ListQuery | None = None) -> list[ScanRun]:
        stmt = self.statement().where(ScanRun.project_id == project_id)
        if query is None:
            return list(stmt.order_by(ScanRun.created_at.desc()).scalars().all())
        return list(
            stmt.order_by(ScanRun.created_at.desc())
            .offset(query.offset)
            .limit(query.limit)
            .scalars()
            .all()
        )

    def get_queued_or_running_for_project(self, project_id: str) -> ScanRun | None:
        return (
            self.statement()
            .where(
                ScanRun.project_id == project_id,
                ScanRun.status.in_([ScanStatus.QUEUED, ScanStatus.RUNNING]),
            )
            .limit(1)
            .scalars()
            .first()
        )

    def get_active_for_project(self, project_id: str) -> ScanRun | None:
        """Return a queued or running scan blocking version lifecycle operations."""
        return self.get_queued_or_running_for_project(project_id)

    def get_latest_queued_or_running_for_project(self, project_id: str) -> ScanRun | None:
        return (
            self.statement()
            .where(
                ScanRun.project_id == project_id,
                ScanRun.status.in_([ScanStatus.QUEUED, ScanStatus.RUNNING]),
            )
            .order_by(ScanRun.created_at.desc())
            .limit(1)
            .scalars()
            .first()
        )

    def list_failed_for_project(self, project_id: str) -> list[ScanRun]:
        return list(
            self.statement()
            .where(
                ScanRun.project_id == project_id,
                ScanRun.status == ScanStatus.FAILED,
            )
            .scalars()
            .all()
        )

    def list_queued_or_running_for_project(self, project_id: str) -> list[ScanRun]:
        return list(
            self.statement()
            .where(
                ScanRun.project_id == project_id,
                ScanRun.status.in_([ScanStatus.QUEUED, ScanStatus.RUNNING]),
            )
            .order_by(ScanRun.created_at.desc())
            .scalars()
            .all()
        )

    def list_queued_or_running(self, project_id: str | None = None, *, order_asc: bool = False) -> list[ScanRun]:
        stmt = self.statement().where(ScanRun.status.in_([ScanStatus.QUEUED, ScanStatus.RUNNING]))
        if project_id:
            stmt = stmt.where(ScanRun.project_id == project_id)
        order = ScanRun.created_at.asc() if order_asc else ScanRun.created_at.desc()
        return list(stmt.order_by(order).scalars().all())

    def latest_with_completed_at_except(self, project_id: str, except_scan_run_id: str) -> ScanRun | None:
        return (
            self.statement()
            .where(
                ScanRun.project_id == project_id,
                ScanRun.id != except_scan_run_id,
                ScanRun.completed_at.is_not(None),
            )
            .order_by(ScanRun.completed_at.desc())
            .limit(1)
            .scalars()
            .first()
        )

    def latest_completed_for_project_except(self, project_id: str, except_scan_run_id: str) -> ScanRun | None:
        return (
            self.statement()
            .where(
                ScanRun.project_id == project_id,
                ScanRun.status == ScanStatus.COMPLETED,
                ScanRun.id != except_scan_run_id,
            )
            .order_by(ScanRun.completed_at.desc())
            .limit(1)
            .scalars()
            .first()
        )

    def get_prior_completed_for_project_excluding(self, project_id: str, scan_run_id: str) -> ScanRun | None:
        scan = self.get_for_project(scan_run_id, project_id)
        if scan is None:
            return None
        stmt = self.statement().where(
            ScanRun.project_id == project_id,
            ScanRun.status == ScanStatus.COMPLETED,
            ScanRun.id != scan_run_id,
        )
        if scan.completed_at is not None:
            stmt = stmt.where(ScanRun.completed_at < scan.completed_at)
        return (
            stmt
            .order_by(ScanRun.completed_at.desc())
            .limit(1)
            .scalars()
            .first()
        )

    def count_for_projects_since(self, project_ids: list[str], since: datetime) -> int:
        if not project_ids:
            return 0
        return (
            self.statement()
            .where(
                ScanRun.project_id.in_(project_ids),
                ScanRun.created_at >= since,
            )
            .count()
        )

    def count_for_project(self, project_id: str) -> int:
        return self.statement().where(ScanRun.project_id == project_id).count()

    def set_summary_analysis_version_id(self, scan_run: ScanRun, analysis_version_id: str) -> ScanRun:
        summary = dict(scan_run.summary or {})
        scan_run.summary = {**summary, "analysis_version_id": analysis_version_id}
        self.add(scan_run)
        return scan_run

    def latest_completed_for_project(self, project_id: str, *, scan_type: ScanType | None = None) -> ScanRun | None:
        stmt = self.statement().where(
            ScanRun.project_id == project_id,
            ScanRun.status == ScanStatus.COMPLETED,
        )
        if scan_type is not None:
            stmt = stmt.where(ScanRun.scan_type == scan_type)
        return stmt.order_by(ScanRun.completed_at.desc()).limit(1).scalars().first()
