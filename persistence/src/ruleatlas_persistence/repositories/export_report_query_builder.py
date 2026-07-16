"""Version- and scan-scoped loaders for markdown export reports (read-only)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ruleatlas_persistence.models import AnalysisVersion

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory


class ExportReportQueryBuilder:
    """Resolve export scope and load entity rows via typed repositories (no commits)."""

    def __init__(self, factory: RepositoryFactory) -> None:
        self._factory = factory

    def resolve_version(
        self, project_id: str, *, analysis_version_id: str | None
    ) -> tuple[str | None, AnalysisVersion | None, bool]:
        active_id = self._factory.analysis_versions().get_active_id_for_project(project_id)
        version_id = analysis_version_id or active_id
        if version_id is None:
            return None, None, False
        version = self._factory.analysis_versions().get_for_project(version_id, project_id)
        if version is None:
            return version_id, None, False
        return version_id, version, version_id == active_id if active_id else False

    def latest_completed_scan_line(self, project_id: str) -> str | None:
        scan = self._factory.scan_runs().latest_completed_for_project(project_id)
        if scan is None:
            return None
        completed = scan.completed_at.isoformat() if scan.completed_at else "unknown"
        return f"{scan.id} ({scan.status.value}, completed {completed})"

    def rules_for_export(self, project_id: str, analysis_version_id: str | None) -> Any:
        return self._factory.rules().list_for_project_by_name(
            project_id, analysis_version_id=analysis_version_id
        )

    def evidence_for_export(self, project_id: str, analysis_version_id: str | None) -> Any:
        return self._factory.rule_evidence().list_for_project(
            project_id, analysis_version_id=analysis_version_id
        )

    def conflicts_for_export(self, project_id: str, analysis_version_id: str | None) -> Any:
        return self._factory.conflicts().list_for_project(
            project_id, analysis_version_id=analysis_version_id, order_by_area=True
        )

    def gaps_for_export(self, project_id: str, analysis_version_id: str | None) -> Any:
        return self._factory.gaps().list_for_project(
            project_id, analysis_version_id=analysis_version_id, order_by_title=True
        )

    def coverage_assessments_for_export(self, project_id: str, analysis_version_id: str | None) -> Any:
        return self._factory.coverage_assessments().list_for_project_joined_rules(
            project_id, analysis_version_id=analysis_version_id
        )

    def runtime_findings_for_export(self, project_id: str, analysis_version_id: str | None) -> Any:
        return self._factory.runtime_log_evidence().list_for_project(
            project_id, analysis_version_id=analysis_version_id, order_asc=True
        )

    def scan_runs_for_export(self, project_id: str) -> Any:
        return self._factory.scan_runs().list_for_project(project_id)
