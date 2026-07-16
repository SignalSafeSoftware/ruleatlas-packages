"""Bulk purge queries for demo-project reset (read/delete only — service owns commit)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import delete, update
from sqlalchemy.engine import CursorResult

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy.orm import Session

from ruleatlas_persistence.models import (
    AiInvestigationTrace,
    AiModelUsage,
    AnalysisManifest,
    AnalysisManifestFile,
    AnalysisVersion,
    AuditEvent,
    BddFeature,
    BddScenario,
    BddStep,
    BddStepLink,
    ClaimCluster,
    ClaimClusterMembership,
    ClaimEmbedding,
    CompositePipelineRun,
    CoverageBranch,
    CoverageFile,
    CoverageLine,
    CoverageReport,
    ExportDocument,
    GraphCommunity,
    GraphEdge,
    GraphHyperedge,
    GraphNode,
    GraphObservation,
    GraphProviderRun,
    ImplementationGap,
    Rule,
    RuleConflict,
    RuleCoverageAssessment,
    RuleDecision,
    RuleEvidence,
    RuleReview,
    RuleSourceClaim,
    RuleTraceLink,
    RuleVersion,
    RuntimeEvidenceImport,
    RuntimeLogEvidence,
    ScanConfig,
    ScanRun,
    SearchIndexRecord,
    SemanticObservation,
    SourceClaim,
    SourceClaimEvidence,
    SourceFile,
    SourceLocation,
    SourceSymbol,
    TestAssertion,
    TestCase,
    TestCoverageLink,
    TestEvidenceCase,
    TestExecution,
    TestFixture,
)


class DemoProjectResetRepository:
    """FK-safe demo artifact purge for a project (no commits). Keeps the project row."""

    def __init__(self, factory: RepositoryFactory) -> None:
        self._factory = factory
        self._session: Session = factory.session

    def preview_demo_project_children(self, project_id: str) -> dict[str, int]:
        """Count artifacts that purge_demo_project_children would remove (read-only)."""
        repos = self._factory
        rule_ids = repos.rules().ids_for_project(project_id)
        return {
            "rules": repos.rules().count_for_project(project_id),
            "rule_conflicts": repos.conflicts().count_for_project(project_id),
            "rule_evidence": repos.rule_evidence().count_for_project(project_id),
            "rule_versions": (
                self._session.query(RuleVersion).filter(RuleVersion.rule_id.in_(rule_ids)).count()
                if rule_ids
                else 0
            ),
            "implementation_gaps": repos.gaps().count_for_project(project_id),
            "runtime_log_evidence": repos.runtime_log_evidence().count_for_project(project_id),
            "coverage_reports": (
                self._session.query(CoverageReport)
                .filter(CoverageReport.project_id == project_id)
                .count()
            ),
            "scan_runs": repos.scan_runs().count_for_project(project_id),
            "source_files": repos.source_files().count_for_project(project_id),
            "source_claims": (
                self._session.query(SourceClaim).filter(SourceClaim.project_id == project_id).count()
            ),
            "claim_clusters": (
                self._session.query(ClaimCluster).filter(ClaimCluster.project_id == project_id).count()
            ),
            "export_documents": (
                self._session.query(ExportDocument).filter(ExportDocument.project_id == project_id).count()
            ),
            "search_index_records": repos.search_index().count_for_project(project_id),
            "audit_events": (
                self._session.query(AuditEvent).filter(AuditEvent.project_id == project_id).count()
            ),
            "ai_investigation_traces": (
                self._session.query(AiInvestigationTrace)
                .filter(AiInvestigationTrace.project_id == project_id)
                .count()
            ),
        }

    def purge_demo_project_children(self, project_id: str) -> dict[str, int]:
        repos = self._factory
        counts: dict[str, int] = {}

        rule_ids = repos.rules().ids_for_project(project_id)
        source_file_ids = repos.source_files().ids_for_project(project_id)
        coverage_report_ids = repos.coverage_reports().report_ids_for_project(project_id)
        coverage_file_ids = repos.coverage_reports().file_ids_for_project(project_id)
        coverage_line_ids = repos.coverage_reports().line_ids_for_project(project_id)
        test_case_ids = repos.test_cases().ids_for_project(project_id)

        # --- Composite / AI / claims stack (before analysis_versions) ---
        counts["ai_investigation_traces"] = self._delete(
            delete(AiInvestigationTrace).where(AiInvestigationTrace.project_id == project_id)
        )
        counts["claim_cluster_memberships"] = self._delete(
            delete(ClaimClusterMembership).where(ClaimClusterMembership.project_id == project_id)
        )
        counts["claim_embeddings"] = self._delete(
            delete(ClaimEmbedding).where(ClaimEmbedding.project_id == project_id)
        )
        counts["claim_clusters"] = self._delete(
            delete(ClaimCluster).where(ClaimCluster.project_id == project_id)
        )
        claim_ids = [
            row[0]
            for row in self._session.query(SourceClaim.id)
            .filter(SourceClaim.project_id == project_id)
            .all()
        ]
        counts["source_claim_evidence"] = self._delete(
            delete(SourceClaimEvidence).where(SourceClaimEvidence.source_claim_id.in_(claim_ids))
            if claim_ids
            else None
        )
        counts["source_claims"] = self._delete(
            delete(SourceClaim).where(SourceClaim.project_id == project_id)
        )
        counts["composite_pipeline_runs"] = self._delete(
            delete(CompositePipelineRun).where(CompositePipelineRun.project_id == project_id)
        )

        # BDD / test evidence (graph FKs)
        bdd_feature_ids = [
            row[0]
            for row in self._session.query(BddFeature.id)
            .filter(BddFeature.project_id == project_id)
            .all()
        ]
        bdd_scenario_ids = [
            row[0]
            for row in self._session.query(BddScenario.id)
            .filter(BddScenario.project_id == project_id)
            .all()
        ]
        bdd_step_ids = [
            row[0]
            for row in self._session.query(BddStep.id).filter(BddStep.project_id == project_id).all()
        ]
        counts["bdd_step_links"] = self._delete(
            delete(BddStepLink).where(BddStepLink.project_id == project_id)
        )
        counts["bdd_steps"] = self._delete(
            delete(BddStep).where(BddStep.id.in_(bdd_step_ids)) if bdd_step_ids else None
        )
        counts["bdd_scenarios"] = self._delete(
            delete(BddScenario).where(BddScenario.id.in_(bdd_scenario_ids))
            if bdd_scenario_ids
            else None
        )
        counts["bdd_features"] = self._delete(
            delete(BddFeature).where(BddFeature.id.in_(bdd_feature_ids)) if bdd_feature_ids else None
        )
        test_evidence_ids = [
            row[0]
            for row in self._session.query(TestEvidenceCase.id)
            .filter(TestEvidenceCase.project_id == project_id)
            .all()
        ]
        counts["test_assertions"] = self._delete(
            delete(TestAssertion).where(TestAssertion.test_evidence_case_id.in_(test_evidence_ids))
            if test_evidence_ids
            else None
        )
        counts["test_executions"] = self._delete(
            delete(TestExecution).where(TestExecution.project_id == project_id)
        )
        counts["test_fixtures"] = self._delete(
            delete(TestFixture).where(TestFixture.project_id == project_id)
        )
        counts["test_evidence_cases"] = self._delete(
            delete(TestEvidenceCase).where(TestEvidenceCase.project_id == project_id)
        )

        # Graph stack
        counts["graph_observations"] = self._delete(
            delete(GraphObservation).where(GraphObservation.project_id == project_id)
        )
        counts["graph_edges"] = self._delete(
            delete(GraphEdge).where(GraphEdge.project_id == project_id)
        )
        counts["graph_hyperedges"] = self._delete(
            delete(GraphHyperedge).where(GraphHyperedge.project_id == project_id)
        )
        counts["graph_communities"] = self._delete(
            delete(GraphCommunity).where(GraphCommunity.project_id == project_id)
        )
        counts["graph_nodes"] = self._delete(
            delete(GraphNode).where(GraphNode.project_id == project_id)
        )
        counts["graph_provider_runs"] = self._delete(
            delete(GraphProviderRun).where(GraphProviderRun.project_id == project_id)
        )
        counts["semantic_observations"] = self._delete(
            delete(SemanticObservation).where(SemanticObservation.project_id == project_id)
        )

        # Manifests
        manifest_ids = [
            row[0]
            for row in self._session.query(AnalysisManifest.id)
            .filter(AnalysisManifest.project_id == project_id)
            .all()
        ]
        counts["analysis_manifest_files"] = self._delete(
            delete(AnalysisManifestFile).where(AnalysisManifestFile.manifest_id.in_(manifest_ids))
            if manifest_ids
            else None
        )
        counts["analysis_manifests"] = self._delete(
            delete(AnalysisManifest).where(AnalysisManifest.project_id == project_id)
        )

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

        if source_file_ids:
            self._session.execute(
                update(SourceSymbol)
                .where(SourceSymbol.source_file_id.in_(source_file_ids))
                .values(parent_symbol_id=None)
            )
        counts["source_symbols"] = self._delete(
            delete(SourceSymbol).where(SourceSymbol.source_file_id.in_(source_file_ids))
            if source_file_ids
            else None
        )
        counts["test_cases"] = self._delete(delete(TestCase).where(TestCase.project_id == project_id))
        counts["source_files"] = self._delete(delete(SourceFile).where(SourceFile.project_id == project_id))

        counts["export_documents"] = self._delete(
            delete(ExportDocument).where(ExportDocument.project_id == project_id)
        )
        counts["search_index_records"] = self._delete(
            delete(SearchIndexRecord).where(SearchIndexRecord.project_id == project_id)
        )
        counts["audit_events"] = self._delete(delete(AuditEvent).where(AuditEvent.project_id == project_id))
        counts["ai_model_usage"] = self._delete(
            delete(AiModelUsage).where(AiModelUsage.project_id == project_id)
        )

        self._session.execute(
            update(ScanConfig).where(ScanConfig.project_id == project_id).values(proposal_scan_run_id=None)
        )
        self._session.execute(
            update(SourceLocation).where(SourceLocation.project_id == project_id).values(scan_config_id=None)
        )

        counts["rule_versions"] = self._delete(
            delete(RuleVersion).where(RuleVersion.rule_id.in_(rule_ids)) if rule_ids else None
        )
        counts["rules"] = self._delete(delete(Rule).where(Rule.project_id == project_id))
        counts["analysis_versions"] = self._delete(
            delete(AnalysisVersion).where(AnalysisVersion.project_id == project_id)
        )
        counts["scan_runs"] = self._delete(delete(ScanRun).where(ScanRun.project_id == project_id))
        counts["scan_configs"] = self._delete(delete(ScanConfig).where(ScanConfig.project_id == project_id))

        return counts

    def _delete(self, statement: Any) -> int:
        if statement is None:
            return 0
        result = self._session.execute(statement)
        return result.rowcount if isinstance(result, CursorResult) else 0
