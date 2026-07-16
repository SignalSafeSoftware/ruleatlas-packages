"""Additional domain repositories for full sqlPhilosophy query-boundary coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    RuleSourceClaim,
)


class RuleSourceClaimRepository(BaseRepository[RuleSourceClaim, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(RuleSourceClaim, session, factory)

    def list_for_project_version(self, project_id: str, analysis_version_id: str) -> list[RuleSourceClaim]:
        return list(
            self.statement()
            .where(
                RuleSourceClaim.project_id == project_id,
                RuleSourceClaim.analysis_version_id == analysis_version_id,
            )
            .scalars()
            .all()
        )

    def list_for_project(self, project_id: str, *, analysis_version_id: str | None = None) -> list[RuleSourceClaim]:
        stmt = self.statement().where(RuleSourceClaim.project_id == project_id)
        if analysis_version_id:
            stmt = stmt.where(RuleSourceClaim.analysis_version_id == analysis_version_id)
        return list(stmt.scalars().all())

    def list_for_rule(self, rule_id: str, project_id: str) -> list[RuleSourceClaim]:
        return list(
            self.statement()
            .where(
                RuleSourceClaim.rule_id == rule_id,
                RuleSourceClaim.project_id == project_id,
            )
            .scalars()
            .all()
        )

    def count_for_scan_run(self, scan_run_id: str) -> int:
        return self.statement().where(RuleSourceClaim.scan_run_id == scan_run_id).count()
