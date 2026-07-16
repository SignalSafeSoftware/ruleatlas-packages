"""Bulk purge queries for reset-analysis (read/delete only — service owns commit)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import delete, update

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy.orm import Session

from ruleatlas_persistence.models import (
    AiSuggestion,
    AiTaskRun,
    AnalysisVersion,
    CoverageBranch,
    CoverageFile,
    CoverageLine,
    CoverageReport,
    ExportDocument,
    ImplementationGap,
    Rule,
    RuleConflict,
    RuleCoverageAssessment,
    RuleDecision,
    RuleEvidence,
    RuleRelationship,
    RuleRelationshipSuggestion,
    RuleReview,
    RuleSourceClaim,
    RuleTraceLink,
    RuleVersion,
    RuntimeEvidenceImport,
    RuntimeLogEvidence,
    SearchIndexRecord,
    TestCoverageLink,
)


class ProjectAnalysisResetRepository:
    """FK-safe analysis output purge for a project (no commits)."""

    def __init__(self, factory: RepositoryFactory) -> None:
        self._factory = factory
        self._session: Session = factory.session

    def purge_analysis_outputs(self, project_id: str) -> dict[str, int]:
        repos = self._factory
        counts: dict[str, int] = {}
        rule_ids = repos.rules().ids_for_project(project_id)
        coverage_report_ids = repos.coverage_reports().report_ids_for_project(project_id)
        coverage_file_ids = repos.coverage_reports().file_ids_for_project(project_id)
        coverage_line_ids = repos.coverage_reports().line_ids_for_project(project_id)
        test_case_ids = repos.test_cases().ids_for_project(project_id)

        counts["rule_source_claims"] = self._delete(
            delete(RuleSourceClaim).where(RuleSourceClaim.project_id == project_id)
        )
        counts["rule_evidence"] = self._delete(
            delete(RuleEvidence).where(RuleEvidence.rule_id.in_(rule_ids)) if rule_ids else None
        )
        counts["rule_coverage_assessments"] = self._delete(
            delete(RuleCoverageAssessment).where(RuleCoverageAssessment.rule_id.in_(rule_ids))
            if rule_ids
            else None
        )
        counts["rule_trace_links"] = self._delete(
            delete(RuleTraceLink).where(RuleTraceLink.rule_id.in_(rule_ids)) if rule_ids else None
        )
        counts["rule_decisions"] = self._delete(
            delete(RuleDecision).where(RuleDecision.rule_id.in_(rule_ids)) if rule_ids else None
        )
        counts["rule_reviews"] = self._delete(
            delete(RuleReview).where(RuleReview.rule_id.in_(rule_ids)) if rule_ids else None
        )
        counts["rule_conflicts"] = self._delete(
            delete(RuleConflict).where(RuleConflict.project_id == project_id)
        )
        counts["implementation_gaps"] = self._delete(
            delete(ImplementationGap).where(ImplementationGap.project_id == project_id)
        )
        counts["runtime_log_evidence"] = self._delete(
            delete(RuntimeLogEvidence).where(RuntimeLogEvidence.project_id == project_id)
        )
        counts["test_coverage_links"] = self._delete(
            delete(TestCoverageLink).where(
                (TestCoverageLink.test_case_id.in_(test_case_ids))
                | (TestCoverageLink.coverage_line_id.in_(coverage_line_ids))
            )
            if test_case_ids or coverage_line_ids
            else None
        )
        counts["coverage_lines"] = self._delete(
            delete(CoverageLine).where(CoverageLine.coverage_file_id.in_(coverage_file_ids))
            if coverage_file_ids
            else None
        )
        counts["coverage_branches"] = self._delete(
            delete(CoverageBranch).where(CoverageBranch.coverage_file_id.in_(coverage_file_ids))
            if coverage_file_ids
            else None
        )
        counts["coverage_files"] = self._delete(
            delete(CoverageFile).where(CoverageFile.coverage_report_id.in_(coverage_report_ids))
            if coverage_report_ids
            else None
        )
        counts["coverage_reports"] = self._delete(
            delete(CoverageReport).where(CoverageReport.project_id == project_id)
        )
        counts["runtime_evidence_imports"] = self._delete(
            delete(RuntimeEvidenceImport).where(RuntimeEvidenceImport.project_id == project_id)
        )
        counts["export_documents"] = self._delete(
            delete(ExportDocument).where(ExportDocument.project_id == project_id)
        )
        counts["search_index_records"] = self._delete(
            delete(SearchIndexRecord).where(SearchIndexRecord.project_id == project_id)
        )

        self._session.execute(
            update(Rule).where(Rule.project_id == project_id).values(current_version_id=None)
        )
        counts["rule_versions"] = self._delete(
            delete(RuleVersion).where(RuleVersion.rule_id.in_(rule_ids)) if rule_ids else None
        )
        counts["rule_relationships"] = self._delete(
            delete(RuleRelationship).where(RuleRelationship.project_id == project_id)
        )
        counts["rule_relationship_suggestions"] = self._delete(
            delete(RuleRelationshipSuggestion).where(RuleRelationshipSuggestion.project_id == project_id)
        )
        counts["ai_suggestions"] = self._delete(
            delete(AiSuggestion).where(AiSuggestion.project_id == project_id)
        )
        counts["ai_task_runs"] = self._delete(
            delete(AiTaskRun).where(AiTaskRun.project_id == project_id)
        )
        counts["analysis_versions"] = self._delete(
            delete(AnalysisVersion).where(AnalysisVersion.project_id == project_id)
        )
        counts["rules"] = self._delete(delete(Rule).where(Rule.project_id == project_id))
        return counts

    def _delete(self, statement: Any) -> int:
        if statement is None:
            return 0
        result = self._session.execute(statement)
        return getattr(result, "rowcount", 0) or 0
