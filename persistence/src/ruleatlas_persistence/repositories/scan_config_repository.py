"""Domain repositories for sqlPhilosophy slices 2-8."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    ScanConfig,
)


class ScanConfigRepository(BaseRepository[ScanConfig, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(ScanConfig, session, factory)

    def get_for_project(self, config_id: str, project_id: str) -> ScanConfig | None:
        config = self.get_by_id(config_id)
        if config is None or config.project_id != project_id:
            return None
        return config

    def get_approved_default_for_project(self, project_id: str) -> ScanConfig | None:
        return (
            self.statement()
            .where(
                ScanConfig.project_id == project_id,
                ScanConfig.is_default.is_(True),
                ScanConfig.approved_at.isnot(None),
            )
            .order_by(ScanConfig.approved_at.desc())
            .limit(1)
            .scalars()
            .first()
        )

    def get_approved_default_id_for_project(self, project_id: str) -> str | None:
        config = self.get_approved_default_for_project(project_id)
        return config.id if config is not None else None

    def get_by_proposal_scan_run(self, project_id: str, scan_run_id: str) -> ScanConfig | None:
        return (
            self.statement()
            .where(
                ScanConfig.project_id == project_id,
                ScanConfig.proposal_scan_run_id == scan_run_id,
            )
            .scalars()
            .first()
        )

    def list_for_project(self, project_id: str) -> list[ScanConfig]:
        return list(self.statement().where(ScanConfig.project_id == project_id).scalars().all())

    def get_first_for_project(self, project_id: str) -> ScanConfig | None:
        return self.statement().where(ScanConfig.project_id == project_id).scalars().first()

    def list_for_project_except(self, project_id: str, except_config_id: str) -> list[ScanConfig]:
        return list(
            self.statement()
            .where(
                ScanConfig.project_id == project_id,
                ScanConfig.id != except_config_id,
            )
            .scalars()
            .all()
        )
