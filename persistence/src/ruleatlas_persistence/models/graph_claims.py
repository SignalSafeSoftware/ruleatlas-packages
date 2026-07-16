"""Database models for the graph claims domain."""

from __future__ import annotations

from ._base import (
    FK_PROJECTS_ID,
    FK_SCAN_RUNS_ID,
    JSON,
    Base,
    BddStepLinkStatus,
    Boolean,
    ClaimClusterRole,
    ClaimClusterStatus,
    DateTime,
    Float,
    ForeignKey,
    GraphProviderStatus,
    GraphResolutionType,
    Index,
    Integer,
    Mapped,
    SourceClaimRole,
    SourceClaimStatus,
    String,
    TestAssertionKind,
    TestExecutionStatus,
    TestFramework,
    Text,
    TimestampMixin,
    UniqueConstraint,
    datetime,
    mapped_column,
    uuid_str,
)


class GraphProviderRun(Base, TimestampMixin):
    __tablename__ = "graph_provider_runs"
    __table_args__ = (
        Index("ix_graph_provider_runs_project_analysis", "project_id", "analysis_version_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_versions.id"))
    scan_run_id: Mapped[str | None] = mapped_column(ForeignKey(FK_SCAN_RUNS_ID))
    provider_key: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_version: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=GraphProviderStatus.PENDING.value)
    files_attempted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_succeeded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_unsupported: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    nodes_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    edges_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    extracted_edges: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    inferred_edges: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ambiguous_edges: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    raw_payload_hash: Mapped[str | None] = mapped_column(String(64))


class GraphNode(Base, TimestampMixin):
    __tablename__ = "graph_nodes"
    __table_args__ = (
        UniqueConstraint("analysis_version_id", "canonical_key", name="uq_graph_node_analysis_canonical"),
        Index("ix_graph_nodes_project_analysis", "project_id", "analysis_version_id"),
        Index("ix_graph_nodes_type", "node_type"),
        Index("ix_graph_nodes_source_path", "source_path"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str] = mapped_column(ForeignKey("analysis_versions.id"), nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(512), nullable=False)
    node_type: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(512), nullable=False)
    language_key: Mapped[str | None] = mapped_column(String(64))
    source_path: Mapped[str | None] = mapped_column(String(1024))
    start_line: Mapped[int | None] = mapped_column(Integer)
    end_line: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str | None] = mapped_column(String(128))
    symbol_kind: Mapped[str | None] = mapped_column(String(64))
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class GraphEdge(Base, TimestampMixin):
    __tablename__ = "graph_edges"
    __table_args__ = (
        UniqueConstraint(
            "analysis_version_id", "canonical_key", name="uq_graph_edge_analysis_canonical"
        ),
        Index("ix_graph_edges_project_analysis", "project_id", "analysis_version_id"),
        Index("ix_graph_edges_type", "edge_type"),
        Index("ix_graph_edges_from_to", "from_node_id", "to_node_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str] = mapped_column(ForeignKey("analysis_versions.id"), nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(768), nullable=False)
    edge_type: Mapped[str] = mapped_column(String(64), nullable=False)
    from_node_id: Mapped[str] = mapped_column(ForeignKey("graph_nodes.id"), nullable=False)
    to_node_id: Mapped[str] = mapped_column(ForeignKey("graph_nodes.id"), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    resolution_type: Mapped[str] = mapped_column(
        String(32), default=GraphResolutionType.EXTRACTED.value, nullable=False
    )
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class GraphObservation(Base, TimestampMixin):
    __tablename__ = "graph_observations"
    __table_args__ = (
        UniqueConstraint(
            "provider_run_id", "provider_object_id", "observation_kind",
            name="uq_graph_observation_provider_object",
        ),
        Index("ix_graph_observations_provider_run", "provider_run_id"),
        Index("ix_graph_observations_node", "node_id"),
        Index("ix_graph_observations_edge", "edge_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str] = mapped_column(ForeignKey("analysis_versions.id"), nullable=False)
    provider_run_id: Mapped[str] = mapped_column(ForeignKey("graph_provider_runs.id"), nullable=False)
    observation_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_object_id: Mapped[str] = mapped_column(String(255), nullable=False)
    node_id: Mapped[str | None] = mapped_column(ForeignKey("graph_nodes.id"))
    edge_id: Mapped[str | None] = mapped_column(ForeignKey("graph_edges.id"))
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    resolution_type: Mapped[str] = mapped_column(
        String(32), default=GraphResolutionType.EXTRACTED.value, nullable=False
    )
    raw_payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class GraphCommunity(Base, TimestampMixin):
    __tablename__ = "graph_communities"
    __table_args__ = (
        UniqueConstraint("analysis_version_id", "canonical_key", name="uq_graph_community_canonical"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str] = mapped_column(ForeignKey("analysis_versions.id"), nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(512), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    node_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class GraphHyperedge(Base, TimestampMixin):
    """N-ary relationship among nodes (provider-neutral; not a binary edge)."""

    __tablename__ = "graph_hyperedges"
    __table_args__ = (
        UniqueConstraint("analysis_version_id", "canonical_key", name="uq_graph_hyperedge_canonical"),
        Index("ix_graph_hyperedges_project_analysis", "project_id", "analysis_version_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str] = mapped_column(ForeignKey("analysis_versions.id"), nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(512), nullable=False)
    hyperedge_type: Mapped[str] = mapped_column(String(64), nullable=False)
    node_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class SourceClaim(Base, TimestampMixin):
    __tablename__ = "source_claims"
    __table_args__ = (
        UniqueConstraint("analysis_version_id", "canonical_key", name="uq_source_claim_canonical"),
        Index("ix_source_claims_project_analysis", "project_id", "analysis_version_id"),
        Index("ix_source_claims_provider", "provider_key"),
        Index("ix_source_claims_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str] = mapped_column(ForeignKey("analysis_versions.id"), nullable=False)
    scan_run_id: Mapped[str | None] = mapped_column(ForeignKey(FK_SCAN_RUNS_ID))
    canonical_key: Mapped[str] = mapped_column(String(512), nullable=False)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str | None] = mapped_column(String(255))
    condition_text: Mapped[str | None] = mapped_column(Text)
    action_text: Mapped[str | None] = mapped_column(Text)
    result_text: Mapped[str | None] = mapped_column(Text)
    exception_text: Mapped[str | None] = mapped_column(Text)
    subject_text: Mapped[str | None] = mapped_column(String(255))
    state_transition: Mapped[str | None] = mapped_column(String(255))
    claim_role: Mapped[str] = mapped_column(String(64), nullable=False, default=SourceClaimRole.IMPLEMENTATION.value)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=SourceClaimStatus.CANDIDATE.value)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    provider_key: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_version: Mapped[str | None] = mapped_column(String(64))
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    source_path: Mapped[str | None] = mapped_column(String(1024))
    start_line: Mapped[int | None] = mapped_column(Integer)
    end_line: Mapped[int | None] = mapped_column(Integer)
    graph_node_id: Mapped[str | None] = mapped_column(ForeignKey("graph_nodes.id"))
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_canonical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class SourceClaimEvidence(Base, TimestampMixin):
    __tablename__ = "source_claim_evidence"
    __table_args__ = (Index("ix_source_claim_evidence_claim", "source_claim_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    source_claim_id: Mapped[str] = mapped_column(ForeignKey("source_claims.id"), nullable=False)
    evidence_kind: Mapped[str] = mapped_column(String(64), nullable=False, default="source_span")
    reference_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    start_line: Mapped[int | None] = mapped_column(Integer)
    end_line: Mapped[int | None] = mapped_column(Integer)
    excerpt: Mapped[str | None] = mapped_column(Text)
    graph_node_id: Mapped[str | None] = mapped_column(ForeignKey("graph_nodes.id"))
    graph_edge_id: Mapped[str | None] = mapped_column(ForeignKey("graph_edges.id"))
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class TestEvidenceCase(Base, TimestampMixin):
    """Provider-neutral normalized test case (distinct from legacy coverage TestCase)."""

    __tablename__ = "test_evidence_cases"
    __table_args__ = (
        UniqueConstraint("analysis_version_id", "canonical_key", name="uq_test_evidence_canonical"),
        Index("ix_test_evidence_project_analysis", "project_id", "analysis_version_id"),
        Index("ix_test_evidence_framework", "framework"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str] = mapped_column(ForeignKey("analysis_versions.id"), nullable=False)
    scan_run_id: Mapped[str | None] = mapped_column(ForeignKey(FK_SCAN_RUNS_ID))
    canonical_key: Mapped[str] = mapped_column(String(512), nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    framework: Mapped[str] = mapped_column(String(64), nullable=False, default=TestFramework.UNKNOWN.value)
    provider_key: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_version: Mapped[str | None] = mapped_column(String(64))
    source_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    start_line: Mapped[int | None] = mapped_column(Integer)
    end_line: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str | None] = mapped_column(String(128))
    given_text: Mapped[str | None] = mapped_column(Text)
    when_text: Mapped[str | None] = mapped_column(Text)
    then_text: Mapped[str | None] = mapped_column(Text)
    graph_node_id: Mapped[str | None] = mapped_column(ForeignKey("graph_nodes.id"))
    production_symbol_key: Mapped[str | None] = mapped_column(String(512))
    production_link_status: Mapped[str] = mapped_column(String(32), default="unresolved", nullable=False)
    production_link_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_parametrized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_frontend: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class TestAssertion(Base, TimestampMixin):
    __tablename__ = "test_assertions"
    __table_args__ = (Index("ix_test_assertions_case", "test_evidence_case_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    test_evidence_case_id: Mapped[str] = mapped_column(ForeignKey("test_evidence_cases.id"), nullable=False)
    assertion_kind: Mapped[str] = mapped_column(String(64), nullable=False, default=TestAssertionKind.ASSERT.value)
    expression: Mapped[str] = mapped_column(Text, nullable=False)
    expected_exception: Mapped[str | None] = mapped_column(String(255))
    start_line: Mapped[int | None] = mapped_column(Integer)
    end_line: Mapped[int | None] = mapped_column(Integer)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class TestFixture(Base, TimestampMixin):
    __tablename__ = "test_fixtures"
    __table_args__ = (
        UniqueConstraint("analysis_version_id", "canonical_key", name="uq_test_fixture_canonical"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str] = mapped_column(ForeignKey("analysis_versions.id"), nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(512), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    framework: Mapped[str] = mapped_column(String(64), nullable=False)
    source_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    start_line: Mapped[int | None] = mapped_column(Integer)
    end_line: Mapped[int | None] = mapped_column(Integer)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class TestExecution(Base, TimestampMixin):
    __tablename__ = "test_executions"
    __table_args__ = (
        Index("ix_test_executions_case", "test_evidence_case_id"),
        Index("ix_test_executions_analysis", "analysis_version_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str] = mapped_column(ForeignKey("analysis_versions.id"), nullable=False)
    test_evidence_case_id: Mapped[str] = mapped_column(ForeignKey("test_evidence_cases.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=TestExecutionStatus.UNKNOWN.value)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    message: Mapped[str | None] = mapped_column(Text)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class BddFeature(Base, TimestampMixin):
    __tablename__ = "bdd_features"
    __table_args__ = (
        UniqueConstraint("analysis_version_id", "canonical_key", name="uq_bdd_feature_canonical"),
        Index("ix_bdd_features_project_analysis", "project_id", "analysis_version_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str] = mapped_column(ForeignKey("analysis_versions.id"), nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(512), nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    language: Mapped[str] = mapped_column(String(16), default="en", nullable=False)
    source_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    start_line: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str | None] = mapped_column(String(128))
    tags_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    parse_error: Mapped[str | None] = mapped_column(Text)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class BddScenario(Base, TimestampMixin):
    __tablename__ = "bdd_scenarios"
    __table_args__ = (
        UniqueConstraint("analysis_version_id", "canonical_key", name="uq_bdd_scenario_canonical"),
        Index("ix_bdd_scenarios_feature", "bdd_feature_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str] = mapped_column(ForeignKey("analysis_versions.id"), nullable=False)
    bdd_feature_id: Mapped[str] = mapped_column(ForeignKey("bdd_features.id"), nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(512), nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    keyword: Mapped[str] = mapped_column(String(64), default="Scenario", nullable=False)
    is_outline: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    start_line: Mapped[int | None] = mapped_column(Integer)
    tags_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    examples_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    graph_node_id: Mapped[str | None] = mapped_column(ForeignKey("graph_nodes.id"))
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class BddStep(Base, TimestampMixin):
    __tablename__ = "bdd_steps"
    __table_args__ = (Index("ix_bdd_steps_scenario", "bdd_scenario_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str] = mapped_column(ForeignKey("analysis_versions.id"), nullable=False)
    bdd_scenario_id: Mapped[str] = mapped_column(ForeignKey("bdd_scenarios.id"), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    keyword: Mapped[str] = mapped_column(String(32), nullable=False)
    keyword_type: Mapped[str | None] = mapped_column(String(32))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    start_line: Mapped[int | None] = mapped_column(Integer)
    argument_json: Mapped[dict | None] = mapped_column(JSON)
    link_status: Mapped[str] = mapped_column(String(32), default=BddStepLinkStatus.UNDEFINED.value, nullable=False)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class BddStepLink(Base, TimestampMixin):
    __tablename__ = "bdd_step_links"
    __table_args__ = (Index("ix_bdd_step_links_step", "bdd_step_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str] = mapped_column(ForeignKey("analysis_versions.id"), nullable=False)
    bdd_step_id: Mapped[str] = mapped_column(ForeignKey("bdd_steps.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=BddStepLinkStatus.UNDEFINED.value)
    definition_path: Mapped[str | None] = mapped_column(String(1024))
    definition_name: Mapped[str | None] = mapped_column(String(512))
    definition_start_line: Mapped[int | None] = mapped_column(Integer)
    graph_node_id: Mapped[str | None] = mapped_column(ForeignKey("graph_nodes.id"))
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    provider_key: Mapped[str] = mapped_column(String(64), default="step_linker", nullable=False)
    candidates_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class ClaimCluster(Base, TimestampMixin):
    __tablename__ = "claim_clusters"
    __table_args__ = (
        UniqueConstraint("analysis_version_id", "canonical_key", name="uq_claim_cluster_canonical"),
        Index("ix_claim_clusters_project_analysis", "project_id", "analysis_version_id"),
        Index("ix_claim_clusters_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str] = mapped_column(ForeignKey("analysis_versions.id"), nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(512), nullable=False)
    label: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=ClaimClusterStatus.CANDIDATE.value)
    cluster_role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ClaimClusterRole.REVIEW_REQUIRED.value,
        index=True,
    )
    algorithm_key: Mapped[str] = mapped_column(String(64), nullable=False, default="deterministic_v1")
    algorithm_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    explanation: Mapped[str | None] = mapped_column(Text)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(String(200))
    parent_cluster_id: Mapped[str | None] = mapped_column(ForeignKey("claim_clusters.id"))
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class ClaimClusterMembership(Base, TimestampMixin):
    __tablename__ = "claim_cluster_memberships"
    __table_args__ = (
        UniqueConstraint("claim_cluster_id", "source_claim_id", name="uq_cluster_membership"),
        Index("ix_cluster_memberships_claim", "source_claim_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str] = mapped_column(ForeignKey("analysis_versions.id"), nullable=False)
    claim_cluster_id: Mapped[str] = mapped_column(ForeignKey("claim_clusters.id"), nullable=False)
    source_claim_id: Mapped[str] = mapped_column(ForeignKey("source_claims.id"), nullable=False)
    join_reason: Mapped[str] = mapped_column(Text, nullable=False)
    join_signals_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    join_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class ClaimEmbedding(Base, TimestampMixin):
    __tablename__ = "claim_embeddings"
    __table_args__ = (
        UniqueConstraint(
            "analysis_version_id", "content_hash", "model_key", "model_version",
            name="uq_claim_embedding_content_model",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str] = mapped_column(ForeignKey("analysis_versions.id"), nullable=False)
    source_claim_id: Mapped[str | None] = mapped_column(ForeignKey("source_claims.id"))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    model_key: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    vector_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
