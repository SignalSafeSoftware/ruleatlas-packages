from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar, cast

from sqlalchemy.orm import DeclarativeBase, Session
from sqlphilosophy.sync.protocols import (
    BaseRepositoryProtocol,
)
from sqlphilosophy.sync.protocols import (
    RepositoryFactory as SqlPhilosophyRepositoryFactory,
)
from sqlphilosophy.sync.query import SqlAlchemyStatementBuilder, StatementQueryBuilder
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.repositories.ai_investigation_trace_repository import (
    AiInvestigationTraceRepository,
)
from ruleatlas_persistence.repositories.ai_model_usage_repository import AiModelUsageRepository
from ruleatlas_persistence.repositories.ai_provider_repository import (
    AiModelCatalogEntryRepository,
    AiModelCompatibilityTestRepository,
    AiProviderConnectionRepository,
    ProjectAiConfigurationRepository,
)
from ruleatlas_persistence.repositories.ai_suggestion_repository import AiSuggestionRepository
from ruleatlas_persistence.repositories.ai_task_run_repository import AiTaskRunRepository
from ruleatlas_persistence.repositories.analysis_manifest_repository import (
    AnalysisManifestFileRepository,
    AnalysisManifestRepository,
)
from ruleatlas_persistence.repositories.analysis_version_repository import (
    AnalysisVersionRepository,
)
from ruleatlas_persistence.repositories.api_token_repository import ApiTokenRepository
from ruleatlas_persistence.repositories.audit_repository import AuditRepository
from ruleatlas_persistence.repositories.bdd_repository import (
    BddFeatureRepository,
    BddScenarioRepository,
    BddStepLinkRepository,
    BddStepRepository,
)
from ruleatlas_persistence.repositories.claim_cluster_repository import (
    ClaimClusterMembershipRepository,
    ClaimClusterRepository,
    CompositePipelineRunRepository,
)
from ruleatlas_persistence.repositories.classification_override_repository import (
    ClassificationOverrideRepository,
)
from ruleatlas_persistence.repositories.configuration_override_repository import (
    ConfigurationOverrideHistoryRepository,
    ConfigurationOverrideRepository,
)
from ruleatlas_persistence.repositories.conflict_repository import ConflictRepository
from ruleatlas_persistence.repositories.coverage_line_repository import CoverageLineRepository
from ruleatlas_persistence.repositories.coverage_report_repository import (
    CoverageReportRepository,
)
from ruleatlas_persistence.repositories.demo_project_reset_repository import (
    DemoProjectResetRepository,
)
from ruleatlas_persistence.repositories.demo_query_repository import DemoQueryRepository
from ruleatlas_persistence.repositories.entitlement_repository import EntitlementRepository
from ruleatlas_persistence.repositories.export_report_query_builder import (
    ExportReportQueryBuilder,
)
from ruleatlas_persistence.repositories.external_identity_repository import ExternalIdentityRepository
from ruleatlas_persistence.repositories.file_type_mapping_repository import (
    FileTypeMappingRepository,
)
from ruleatlas_persistence.repositories.gap_repository import GapRepository
from ruleatlas_persistence.repositories.graph_repository import (
    GraphCommunityRepository,
    GraphEdgeRepository,
    GraphHyperedgeRepository,
    GraphNodeRepository,
    GraphObservationRepository,
    GraphProviderRunRepository,
)
from ruleatlas_persistence.repositories.integration_credential_repository import (
    IntegrationCredentialRepository,
)
from ruleatlas_persistence.repositories.organization_repository import OrganizationRepository
from ruleatlas_persistence.repositories.pagination_repository import PaginationRepository
from ruleatlas_persistence.repositories.password_reset_token_repository import (
    PasswordResetTokenRepository,
)
from ruleatlas_persistence.repositories.permission_repository import PermissionRepository
from ruleatlas_persistence.repositories.project_analysis_reset_repository import (
    ProjectAnalysisResetRepository,
)
from ruleatlas_persistence.repositories.project_repository import ProjectRepository
from ruleatlas_persistence.repositories.project_summary_repository import (
    ProjectSummaryRepository,
)
from ruleatlas_persistence.repositories.rule_coverage_assessment_repository import (
    RuleCoverageAssessmentRepository,
)
from ruleatlas_persistence.repositories.rule_evidence_repository import RuleEvidenceRepository
from ruleatlas_persistence.repositories.rule_relationship_repository import (
    RuleRelationshipRepository,
)
from ruleatlas_persistence.repositories.rule_relationship_suggestion_repository import (
    RuleRelationshipSuggestionRepository,
)
from ruleatlas_persistence.repositories.rule_repository import RuleRepository
from ruleatlas_persistence.repositories.rule_review_repository import RuleReviewRepository
from ruleatlas_persistence.repositories.rule_source_claim_repository import (
    RuleSourceClaimRepository,
)
from ruleatlas_persistence.repositories.rule_version_repository import RuleVersionRepository
from ruleatlas_persistence.repositories.runtime_event_repository import (
    RuntimeEventLinkRepository,
    RuntimeEventRepository,
)
from ruleatlas_persistence.repositories.runtime_evidence_import_repository import (
    RuntimeEvidenceImportRepository,
)
from ruleatlas_persistence.repositories.runtime_log_evidence_repository import (
    RuntimeLogEvidenceRepository,
)
from ruleatlas_persistence.repositories.scan_config_repository import ScanConfigRepository
from ruleatlas_persistence.repositories.scan_run_repository import ScanRunRepository
from ruleatlas_persistence.repositories.search_index_repository import SearchIndexRepository
from ruleatlas_persistence.repositories.semantic_observation_repository import (
    SemanticObservationRepository,
)
from ruleatlas_persistence.repositories.source_claim_structured_repository import (
    SourceClaimEvidenceRepository,
    SourceClaimStructuredRepository,
)
from ruleatlas_persistence.repositories.source_file_repository import SourceFileRepository
from ruleatlas_persistence.repositories.source_location_repository import (
    SourceLocationRepository,
)
from ruleatlas_persistence.repositories.source_symbol_repository import SourceSymbolRepository
from ruleatlas_persistence.repositories.source_tree_node_repository import (
    SourceTreeNodeRepository,
)
from ruleatlas_persistence.repositories.test_case_repository import TestCaseRepository
from ruleatlas_persistence.repositories.test_evidence_repository import (
    TestAssertionRepository,
    TestEvidenceCaseRepository,
    TestFixtureRepository,
)
from ruleatlas_persistence.repositories.ticket_repository import (
    ExternalTicketRepository,
    TicketConnectionRepository,
    TicketRevisionRepository,
    TicketSyncCursorRepository,
    TicketWebhookDeliveryRepository,
)
from ruleatlas_persistence.repositories.user_invite_repository import UserInviteRepository
from ruleatlas_persistence.repositories.user_repository import UserRepository
from ruleatlas_persistence.repositories.user_session_repository import UserSessionRepository

T = TypeVar("T", bound=DeclarativeBase)
R = TypeVar("R")


class RepositoryFactory(SqlPhilosophyRepositoryFactory):
    """Session-scoped typed repositories with sqlphilosophy factory protocol support."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._typed_repos: dict[type[object], object] = {}
        self._model_repos: dict[type[DeclarativeBase], BaseRepository[DeclarativeBase, RepositoryFactory]] = {}
        self._root: object | None = None

    def attach(self, root: object) -> None:
        """Link the composition-root service factory for cross-namespace access."""
        self._root = root

    @property
    def session(self) -> Session:
        return self._session

    def create_statement(self, model: type[T]) -> StatementQueryBuilder[T]:
        return SqlAlchemyStatementBuilder(self._session, model)

    def get_repository(self, repo_class: type[R]) -> R:
        cached = self._typed_repos.get(repo_class)
        if cached is not None:
            return cast(R, cached)
        constructor = cast(Callable[[Session, RepositoryFactory], R], repo_class)
        created = constructor(self._session, self)
        self._typed_repos[repo_class] = created
        return created

    def repository(self, model: type[T]) -> BaseRepositoryProtocol[T, SqlPhilosophyRepositoryFactory]:
        cached = self._model_repos.get(model)
        if cached is not None:
            return cast(BaseRepositoryProtocol[T, SqlPhilosophyRepositoryFactory], cached)
        created: BaseRepository[DeclarativeBase, RepositoryFactory] = BaseRepository(model, self._session, factory=self)
        self._model_repos[model] = created
        return cast(BaseRepositoryProtocol[T, SqlPhilosophyRepositoryFactory], created)

    def projects(self) -> ProjectRepository:
        return self.get_repository(ProjectRepository)

    def scan_runs(self) -> ScanRunRepository:
        return self.get_repository(ScanRunRepository)

    def analysis_versions(self) -> AnalysisVersionRepository:
        return self.get_repository(AnalysisVersionRepository)

    def analysis_manifests(self) -> AnalysisManifestRepository:
        return self.get_repository(AnalysisManifestRepository)

    def analysis_manifest_files(self) -> AnalysisManifestFileRepository:
        return self.get_repository(AnalysisManifestFileRepository)

    def claim_clusters(self) -> ClaimClusterRepository:
        return self.get_repository(ClaimClusterRepository)

    def claim_cluster_memberships(self) -> ClaimClusterMembershipRepository:
        return self.get_repository(ClaimClusterMembershipRepository)

    def composite_pipeline_runs(self) -> CompositePipelineRunRepository:
        return self.get_repository(CompositePipelineRunRepository)

    def rules(self) -> RuleRepository:
        return self.get_repository(RuleRepository)

    def source_files(self) -> SourceFileRepository:
        return self.get_repository(SourceFileRepository)

    def scan_configs(self) -> ScanConfigRepository:
        return self.get_repository(ScanConfigRepository)

    def conflicts(self) -> ConflictRepository:
        return self.get_repository(ConflictRepository)

    def gaps(self) -> GapRepository:
        return self.get_repository(GapRepository)

    def rule_versions(self) -> RuleVersionRepository:
        return self.get_repository(RuleVersionRepository)

    def permissions(self) -> PermissionRepository:
        return self.get_repository(PermissionRepository)

    def entitlements(self) -> EntitlementRepository:
        return self.get_repository(EntitlementRepository)

    def audit(self) -> AuditRepository:
        return self.get_repository(AuditRepository)

    def bdd_steps(self) -> BddStepRepository:
        return self.get_repository(BddStepRepository)

    def bdd_features(self) -> BddFeatureRepository:
        return self.get_repository(BddFeatureRepository)

    def bdd_scenarios(self) -> BddScenarioRepository:
        return self.get_repository(BddScenarioRepository)

    def bdd_step_links(self) -> BddStepLinkRepository:
        return self.get_repository(BddStepLinkRepository)

    def configuration_override_history(self) -> ConfigurationOverrideHistoryRepository:
        return self.get_repository(ConfigurationOverrideHistoryRepository)

    def configuration_overrides(self) -> ConfigurationOverrideRepository:
        return self.get_repository(ConfigurationOverrideRepository)

    def search_index(self) -> SearchIndexRepository:
        return self.get_repository(SearchIndexRepository)

    def source_tree_nodes(self) -> SourceTreeNodeRepository:
        return self.get_repository(SourceTreeNodeRepository)

    def users(self) -> UserRepository:
        return self.get_repository(UserRepository)

    def external_identities(self) -> ExternalIdentityRepository:
        return self.get_repository(ExternalIdentityRepository)

    def user_sessions(self) -> UserSessionRepository:
        return self.get_repository(UserSessionRepository)

    def api_tokens(self) -> ApiTokenRepository:
        return self.get_repository(ApiTokenRepository)

    def password_reset_tokens(self) -> PasswordResetTokenRepository:
        return self.get_repository(PasswordResetTokenRepository)

    def user_invites(self) -> UserInviteRepository:
        return self.get_repository(UserInviteRepository)

    def organizations(self) -> OrganizationRepository:
        return self.get_repository(OrganizationRepository)

    def source_locations(self) -> SourceLocationRepository:
        return self.get_repository(SourceLocationRepository)

    def source_symbols(self) -> SourceSymbolRepository:
        return self.get_repository(SourceSymbolRepository)

    def rule_evidence(self) -> RuleEvidenceRepository:
        return self.get_repository(RuleEvidenceRepository)

    def rule_relationships(self) -> RuleRelationshipRepository:
        return self.get_repository(RuleRelationshipRepository)

    def rule_source_claims(self) -> RuleSourceClaimRepository:
        return self.get_repository(RuleSourceClaimRepository)

    def graph_provider_runs(self) -> GraphProviderRunRepository:
        return self.get_repository(GraphProviderRunRepository)

    def graph_nodes(self) -> GraphNodeRepository:
        return self.get_repository(GraphNodeRepository)

    def graph_edges(self) -> GraphEdgeRepository:
        return self.get_repository(GraphEdgeRepository)

    def graph_observations(self) -> GraphObservationRepository:
        return self.get_repository(GraphObservationRepository)

    def graph_communities(self) -> GraphCommunityRepository:
        return self.get_repository(GraphCommunityRepository)

    def graph_hyperedges(self) -> GraphHyperedgeRepository:
        return self.get_repository(GraphHyperedgeRepository)

    def source_claims_structured(self) -> SourceClaimStructuredRepository:
        return self.get_repository(SourceClaimStructuredRepository)

    def source_claim_evidence(self) -> SourceClaimEvidenceRepository:
        return self.get_repository(SourceClaimEvidenceRepository)

    def classification_overrides(self) -> ClassificationOverrideRepository:
        return self.get_repository(ClassificationOverrideRepository)

    def file_type_mappings(self) -> FileTypeMappingRepository:
        return self.get_repository(FileTypeMappingRepository)

    def coverage_assessments(self) -> RuleCoverageAssessmentRepository:
        return self.get_repository(RuleCoverageAssessmentRepository)

    def runtime_log_evidence(self) -> RuntimeLogEvidenceRepository:
        return self.get_repository(RuntimeLogEvidenceRepository)

    def runtime_events(self) -> RuntimeEventRepository:
        return self.get_repository(RuntimeEventRepository)

    def runtime_event_links(self) -> RuntimeEventLinkRepository:
        return self.get_repository(RuntimeEventLinkRepository)

    def runtime_evidence_imports(self) -> RuntimeEvidenceImportRepository:
        return self.get_repository(RuntimeEvidenceImportRepository)

    def semantic_observations(self) -> SemanticObservationRepository:
        return self.get_repository(SemanticObservationRepository)

    def coverage_reports(self) -> CoverageReportRepository:
        return self.get_repository(CoverageReportRepository)

    def coverage_lines(self) -> CoverageLineRepository:
        return self.get_repository(CoverageLineRepository)

    def test_cases(self) -> TestCaseRepository:
        return self.get_repository(TestCaseRepository)

    def test_evidence_cases(self) -> TestEvidenceCaseRepository:
        return self.get_repository(TestEvidenceCaseRepository)

    def test_assertions(self) -> TestAssertionRepository:
        return self.get_repository(TestAssertionRepository)

    def test_fixtures(self) -> TestFixtureRepository:
        return self.get_repository(TestFixtureRepository)

    def ai_investigation_traces(self) -> AiInvestigationTraceRepository:
        return self.get_repository(AiInvestigationTraceRepository)

    def ticket_connections(self) -> TicketConnectionRepository:
        return self.get_repository(TicketConnectionRepository)

    def ticket_webhook_deliveries(self) -> TicketWebhookDeliveryRepository:
        return self.get_repository(TicketWebhookDeliveryRepository)

    def ticket_revisions(self) -> TicketRevisionRepository:
        return self.get_repository(TicketRevisionRepository)

    def external_tickets(self) -> ExternalTicketRepository:
        return self.get_repository(ExternalTicketRepository)

    def ticket_sync_cursors(self) -> TicketSyncCursorRepository:
        return self.get_repository(TicketSyncCursorRepository)

    def integration_credentials(self) -> IntegrationCredentialRepository:
        return self.get_repository(IntegrationCredentialRepository)

    def ai_suggestions(self) -> AiSuggestionRepository:
        return self.get_repository(AiSuggestionRepository)

    def ai_task_runs(self) -> AiTaskRunRepository:
        return self.get_repository(AiTaskRunRepository)

    def pagination(self) -> PaginationRepository:
        return self.get_repository(PaginationRepository)

    def project_summary(self) -> ProjectSummaryRepository:
        return self.get_repository(ProjectSummaryRepository)

    def rule_reviews(self) -> RuleReviewRepository:
        return self.get_repository(RuleReviewRepository)

    def rule_relationship_suggestions(self) -> RuleRelationshipSuggestionRepository:
        return self.get_repository(RuleRelationshipSuggestionRepository)

    def ai_model_usage(self) -> AiModelUsageRepository:
        return self.get_repository(AiModelUsageRepository)

    def ai_provider_connections(self) -> AiProviderConnectionRepository:
        return self.get_repository(AiProviderConnectionRepository)

    def ai_model_catalog_entries(self) -> AiModelCatalogEntryRepository:
        return self.get_repository(AiModelCatalogEntryRepository)

    def ai_model_compatibility_tests(self) -> AiModelCompatibilityTestRepository:
        return self.get_repository(AiModelCompatibilityTestRepository)

    def project_ai_configurations(self) -> ProjectAiConfigurationRepository:
        return self.get_repository(ProjectAiConfigurationRepository)

    def export_reports(self) -> ExportReportQueryBuilder:
        return ExportReportQueryBuilder(self)

    def project_analysis_reset(self) -> ProjectAnalysisResetRepository:
        return ProjectAnalysisResetRepository(self)

    def demo_project_reset(self) -> DemoProjectResetRepository:
        return DemoProjectResetRepository(self)

    def demo_queries(self) -> DemoQueryRepository:
        return self.get_repository(DemoQueryRepository)
