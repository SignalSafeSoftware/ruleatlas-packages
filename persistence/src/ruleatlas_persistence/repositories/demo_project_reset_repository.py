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

        counts.update(self._purge_claims_and_composite(project_id))
        counts.update(self._purge_bdd_and_test_evidence(project_id))
        counts.update(self._purge_graph_stack(project_id))
        counts.update(self._purge_manifests(project_id))
        counts.update(
            self._purge_rules_coverage_and_sources(
                project_id,
                rule_ids=rule_ids,
                source_file_ids=source_file_ids,
                coverage_report_ids=coverage_report_ids,
                coverage_file_ids=coverage_file_ids,
                coverage_line_ids=coverage_line_ids,
                test_case_ids=test_case_ids,
            )
        )
        return counts

    def _purge_claims_and_composite(self, project_id: str) -> dict[str, int]:
        claim_ids = self._ids_for_project(SourceClaim, project_id)
        return {
            "ai_investigation_traces": self._delete_for_project(AiInvestigationTrace, project_id),
            "claim_cluster_memberships": self._delete_for_project(ClaimClusterMembership, project_id),
            "claim_embeddings": self._delete_for_project(ClaimEmbedding, project_id),
            "claim_clusters": self._delete_for_project(ClaimCluster, project_id),
            "source_claim_evidence": self._delete_in(
                SourceClaimEvidence, SourceClaimEvidence.source_claim_id, claim_ids
            ),
            "source_claims": self._delete_for_project(SourceClaim, project_id),
            "composite_pipeline_runs": self._delete_for_project(CompositePipelineRun, project_id),
        }

    def _purge_bdd_and_test_evidence(self, project_id: str) -> dict[str, int]:
        bdd_feature_ids = self._ids_for_project(BddFeature, project_id)
        bdd_scenario_ids = self._ids_for_project(BddScenario, project_id)
        bdd_step_ids = self._ids_for_project(BddStep, project_id)
        test_evidence_ids = self._ids_for_project(TestEvidenceCase, project_id)
        return {
            "bdd_step_links": self._delete_for_project(BddStepLink, project_id),
            "bdd_steps": self._delete_in(BddStep, BddStep.id, bdd_step_ids),
            "bdd_scenarios": self._delete_in(BddScenario, BddScenario.id, bdd_scenario_ids),
            "bdd_features": self._delete_in(BddFeature, BddFeature.id, bdd_feature_ids),
            "test_assertions": self._delete_in(
                TestAssertion, TestAssertion.test_evidence_case_id, test_evidence_ids
            ),
            "test_executions": self._delete_for_project(TestExecution, project_id),
            "test_fixtures": self._delete_for_project(TestFixture, project_id),
            "test_evidence_cases": self._delete_for_project(TestEvidenceCase, project_id),
        }

    def _purge_graph_stack(self, project_id: str) -> dict[str, int]:
        return {
            "graph_observations": self._delete_for_project(GraphObservation, project_id),
            "graph_edges": self._delete_for_project(GraphEdge, project_id),
            "graph_hyperedges": self._delete_for_project(GraphHyperedge, project_id),
            "graph_communities": self._delete_for_project(GraphCommunity, project_id),
            "graph_nodes": self._delete_for_project(GraphNode, project_id),
            "graph_provider_runs": self._delete_for_project(GraphProviderRun, project_id),
            "semantic_observations": self._delete_for_project(SemanticObservation, project_id),
        }

    def _purge_manifests(self, project_id: str) -> dict[str, int]:
        manifest_ids = self._ids_for_project(AnalysisManifest, project_id)
        return {
            "analysis_manifest_files": self._delete_in(
                AnalysisManifestFile, AnalysisManifestFile.manifest_id, manifest_ids
            ),
            "analysis_manifests": self._delete_for_project(AnalysisManifest, project_id),
        }

    def _purge_rules_coverage_and_sources(
        self,
        project_id: str,
        *,
        rule_ids: list[str],
        source_file_ids: list[str],
        coverage_report_ids: list[str],
        coverage_file_ids: list[str],
        coverage_line_ids: list[str],
        test_case_ids: list[str],
    ) -> dict[str, int]:
        counts = {
            "rule_source_claims": self._delete_for_project(RuleSourceClaim, project_id),
            "rule_evidence": self._delete_in(RuleEvidence, RuleEvidence.rule_id, rule_ids),
            "rule_coverage_assessments": self._delete_in(
                RuleCoverageAssessment, RuleCoverageAssessment.rule_id, rule_ids
            ),
            "rule_trace_links": self._delete_in(RuleTraceLink, RuleTraceLink.rule_id, rule_ids),
            "rule_decisions": self._delete_in(RuleDecision, RuleDecision.rule_id, rule_ids),
            "rule_reviews": self._delete_in(RuleReview, RuleReview.rule_id, rule_ids),
            "rule_conflicts": self._delete_for_project(RuleConflict, project_id),
            "implementation_gaps": self._delete_for_project(ImplementationGap, project_id),
            "runtime_log_evidence": self._delete_for_project(RuntimeLogEvidence, project_id),
            "test_coverage_links": self._delete_test_coverage_links(test_case_ids, coverage_line_ids),
            "coverage_lines": self._delete_in(CoverageLine, CoverageLine.coverage_file_id, coverage_file_ids),
            "coverage_branches": self._delete_in(
                CoverageBranch, CoverageBranch.coverage_file_id, coverage_file_ids
            ),
            "coverage_files": self._delete_in(
                CoverageFile, CoverageFile.coverage_report_id, coverage_report_ids
            ),
            "coverage_reports": self._delete_for_project(CoverageReport, project_id),
            "runtime_evidence_imports": self._delete_for_project(RuntimeEvidenceImport, project_id),
        }
        if source_file_ids:
            self._session.execute(
                update(SourceSymbol)
                .where(SourceSymbol.source_file_id.in_(source_file_ids))
                .values(parent_symbol_id=None)
            )
        counts["source_symbols"] = self._delete_in(
            SourceSymbol, SourceSymbol.source_file_id, source_file_ids
        )
        counts["test_cases"] = self._delete_for_project(TestCase, project_id)
        counts["source_files"] = self._delete_for_project(SourceFile, project_id)
        counts["export_documents"] = self._delete_for_project(ExportDocument, project_id)
        counts["search_index_records"] = self._delete_for_project(SearchIndexRecord, project_id)
        counts["audit_events"] = self._delete_for_project(AuditEvent, project_id)
        counts["ai_model_usage"] = self._delete_for_project(AiModelUsage, project_id)

        self._session.execute(
            update(ScanConfig).where(ScanConfig.project_id == project_id).values(proposal_scan_run_id=None)
        )
        self._session.execute(
            update(SourceLocation).where(SourceLocation.project_id == project_id).values(scan_config_id=None)
        )

        counts["rule_versions"] = self._delete_in(RuleVersion, RuleVersion.rule_id, rule_ids)
        counts["rules"] = self._delete_for_project(Rule, project_id)
        counts["analysis_versions"] = self._delete_for_project(AnalysisVersion, project_id)
        counts["scan_runs"] = self._delete_for_project(ScanRun, project_id)
        counts["scan_configs"] = self._delete_for_project(ScanConfig, project_id)
        return counts

    def _delete_test_coverage_links(self, test_case_ids: list[str], coverage_line_ids: list[str]) -> int:
        if not test_case_ids and not coverage_line_ids:
            return 0
        return self._delete(
            delete(TestCoverageLink).where(
                (TestCoverageLink.test_case_id.in_(test_case_ids))
                | (TestCoverageLink.coverage_line_id.in_(coverage_line_ids))
            )
        )

    def _ids_for_project(self, model: type[Any], project_id: str) -> list[str]:
        return [
            row[0]
            for row in self._session.query(model.id).filter(model.project_id == project_id).all()
        ]

    def _delete_for_project(self, model: type[Any], project_id: str) -> int:
        return self._delete(delete(model).where(model.project_id == project_id))

    def _delete_in(self, model: type[Any], column: Any, ids: list[str]) -> int:
        if not ids:
            return 0
        return self._delete(delete(model).where(column.in_(ids)))

    def _delete(self, statement: Any) -> int:
        if statement is None:
            return 0
        result = self._session.execute(statement)
        return result.rowcount if isinstance(result, CursorResult) else 0
