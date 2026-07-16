from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from ruleatlas_contracts.enums import AnalysisVersionStatus
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    AnalysisVersion,
    ImplementationGap,
    Rule,
    RuleConflict,
    RuleSourceClaim,
)

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

_ACTIVE_ANALYSIS_VERSION_SETTINGS_KEY = "active_analysis_version_id"


class AnalysisVersionRepository(BaseRepository[AnalysisVersion, "RepositoryFactory"]):
    """Project-scoped analysis version reads and active-pointer resolution."""

    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(AnalysisVersion, session, factory)
        self._rules = factory.rules()
        self._projects = factory.projects()
        self._scan_runs = factory.scan_runs()
        self._conflicts = factory.conflicts()
        self._gaps = factory.gaps()
        self._claims = factory.rule_source_claims()

    def get_for_project(self, version_id: str, project_id: str) -> AnalysisVersion | None:
        version = self.get_by_id(version_id)
        if version is None or version.project_id != project_id:
            return None
        return version

    def get_active_id_for_project(self, project_id: str) -> str | None:
        # RA-01-006: read the typed FK column; fall back to the legacy settings_json key for any rows not
        # yet migrated (defensive — the backfill migration covers existing data).
        project = self._projects.get_by_id(project_id)
        if project is None:
            return None
        if project.active_analysis_version_id:
            return project.active_analysis_version_id
        raw = (project.settings_json or {}).get(_ACTIVE_ANALYSIS_VERSION_SETTINGS_KEY)
        return str(raw) if raw else None

    def matches_active_pointer(self, project_id: str, analysis_version_id: str | None) -> bool | None:
        """Return None when no active pointer is configured (guard does not apply)."""
        active_id = self.get_active_id_for_project(project_id)
        if active_id is None:
            return None
        return analysis_version_id == active_id

    def get_active_for_project(self, project_id: str) -> AnalysisVersion | None:
        version_id = self.get_active_id_for_project(project_id)
        if version_id is None:
            return None
        return self.get_for_project(version_id, project_id)

    def resolve_for_project(
        self,
        project_id: str,
        *,
        explicit_version_id: str | None = None,
    ) -> str | None:
        if explicit_version_id:
            version = self.get_for_project(explicit_version_id, project_id)
            if version is None:
                return None
            return version.id
        return self.get_active_id_for_project(project_id)

    def list_for_project(self, project_id: str) -> list[AnalysisVersion]:
        return list(
            self.statement()
            .where(AnalysisVersion.project_id == project_id)
            .order_by(AnalysisVersion.version_number.desc())
            .scalars()
            .all()
        )

    def get_latest_for_project(self, project_id: str) -> AnalysisVersion | None:
        return (
            self.statement()
            .where(AnalysisVersion.project_id == project_id)
            .order_by(AnalysisVersion.version_number.desc())
            .limit(1)
            .scalars()
            .first()
        )

    def resolve_for_scan_run(self, project_id: str, scan_run_id: str) -> AnalysisVersion | None:
        scan_run = self._scan_runs.get_for_project(scan_run_id, project_id)
        if scan_run is None:
            return None
        summary = dict(scan_run.summary or {})
        version_id = summary.get("analysis_version_id")
        if version_id:
            version = self.get_for_project(str(version_id), project_id)
            if version is not None:
                return version
        return (
            self.statement()
            .where(
                AnalysisVersion.project_id == project_id,
                AnalysisVersion.scan_run_id == scan_run_id,
            )
            .order_by(AnalysisVersion.version_number.desc())
            .limit(1)
            .scalars()
            .first()
        )

    def next_version_number(self, project_id: str) -> int:
        current = (
            self.statement()
            .select_columns(func.max(AnalysisVersion.version_number))
            .where(AnalysisVersion.project_id == project_id)
            .scalar()
        )
        return int(current or 0) + 1

    def summarize(self, version_id: str) -> dict[str, int]:
        rules_count = self._rules.statement().where(Rule.analysis_version_id == version_id).count()
        conflicts_count = self._conflicts.statement().where(RuleConflict.analysis_version_id == version_id).count()
        gaps_count = self._gaps.statement().where(ImplementationGap.analysis_version_id == version_id).count()
        claims_count = self._claims.statement().where(RuleSourceClaim.analysis_version_id == version_id).count()
        return {
            "rules": int(rules_count or 0),
            "conflicts": int(conflicts_count or 0),
            "gaps": int(gaps_count or 0),
            "claims": int(claims_count or 0),
        }

    def list_ready_except(self, project_id: str, except_version_id: str) -> list[AnalysisVersion]:
        return list(
            self.statement()
            .where(
                AnalysisVersion.project_id == project_id,
                AnalysisVersion.id != except_version_id,
                AnalysisVersion.status == AnalysisVersionStatus.READY,
            )
            .scalars()
            .all()
        )

    def create_building(
        self,
        project_id: str,
        *,
        scan_run_id: str | None = None,
        scan_config_id: str | None = None,
        label: str | None = None,
        created_by_note: str | None = None,
    ) -> AnalysisVersion:
        return self.create(
            project_id=project_id,
            version_number=self.next_version_number(project_id),
            label=label,
            status=AnalysisVersionStatus.BUILDING,
            scan_run_id=scan_run_id,
            scan_config_id=scan_config_id,
            created_by_note=created_by_note,
            summary_json={},
        )

    def ensure_scan_linkage(
        self,
        version: AnalysisVersion,
        *,
        scan_run_id: str,
        scan_config_id: str | None,
    ) -> AnalysisVersion:
        if version.scan_run_id is None:
            version.scan_run_id = scan_run_id
        if version.scan_config_id is None:
            version.scan_config_id = scan_config_id
        self.add(version)
        return version

    def supersede_active_versions(self, project_id: str, *, except_version_id: str) -> None:
        now = datetime.now(UTC)
        active_id = self.get_active_id_for_project(project_id)
        for version in self.list_ready_except(project_id, except_version_id):
            version.status = AnalysisVersionStatus.SUPERSEDED
            version.superseded_at = now
            self.add(version)
        if active_id and active_id != except_version_id:
            prior = self.get_by_id(active_id)
            if prior is not None and prior.status == AnalysisVersionStatus.READY:
                prior.status = AnalysisVersionStatus.SUPERSEDED
                prior.superseded_at = now
                self.add(prior)

    def mark_ready_for_activation(self, version: AnalysisVersion) -> AnalysisVersion:
        version.status = AnalysisVersionStatus.READY
        version.superseded_at = None
        self.add(version)
        return version

    def finalize(self, version: AnalysisVersion, summary: dict[str, int]) -> AnalysisVersion:
        version.summary_json = {**dict(version.summary_json or {}), **summary}
        version.status = AnalysisVersionStatus.READY
        version.completed_at = datetime.now(UTC)
        self.add(version)
        return version

    def mark_failed(self, version_id: str) -> None:
        version = self.get_by_id(version_id)
        if version is None:
            return
        version.status = AnalysisVersionStatus.FAILED
        self.add(version)
