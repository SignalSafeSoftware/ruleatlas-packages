"""Database models for the rules domain."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._base import (
    FK_PROJECTS_ID,
    FK_SCAN_RUNS_ID,
    FK_SOURCE_FILES_ID,
    FK_USERS_ID,
    JSON,
    STR_ENUM_COLUMN_KW,
    Base,
    ConflictType,
    DateTime,
    Enum,
    EvidenceSourceType,
    ExportType,
    Float,
    ForeignKey,
    ImplementationGapPriority,
    ImplementationGapStatus,
    Index,
    Integer,
    Mapped,
    RelationshipSuggestionStatus,
    RuleCategory,
    RuleConflictStatus,
    RuleDecisionType,
    RuleRelationshipType,
    RuleStatus,
    RuleTraceLinkType,
    SearchEntityType,
    String,
    Text,
    TimestampMixin,
    UniqueConstraint,
    datetime,
    mapped_column,
    now_utc,
    relationship,
    uuid_str,
)

if TYPE_CHECKING:
    from .core import Project


class Rule(Base, TimestampMixin):
    __tablename__ = "rules"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "stable_key",
            "analysis_version_id",
            name="uq_rule_project_stable_key_version",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_versions.id"))
    stable_key: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    current_version_id: Mapped[str | None] = mapped_column(String(36))
    status: Mapped[RuleStatus] = mapped_column(
        Enum(RuleStatus, **STR_ENUM_COLUMN_KW), default=RuleStatus.CANDIDATE, nullable=False
    )
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    identity_key: Mapped[str | None] = mapped_column(String(64))
    evidence_fingerprint: Mapped[str | None] = mapped_column(String(64))
    confidence_explanation_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    rule_category: Mapped[RuleCategory] = mapped_column(
        Enum(RuleCategory, **STR_ENUM_COLUMN_KW), default=RuleCategory.UNKNOWN, nullable=False
    )
    workflow_group: Mapped[str | None] = mapped_column(String(128))
    parent_rule_id: Mapped[str | None] = mapped_column(ForeignKey("rules.id"))
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deprecated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str | None] = mapped_column(Text)
    decision_reason: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by_user_id: Mapped[str | None] = mapped_column(ForeignKey(FK_USERS_ID))

    project: Mapped[Project] = relationship(back_populates="rules")
    versions: Mapped[list[RuleVersion]] = relationship(back_populates="rule")
    evidence: Mapped[list[RuleEvidence]] = relationship(back_populates="rule")


class RuleVersion(Base):
    __tablename__ = "rule_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    rule_id: Mapped[str] = mapped_column(ForeignKey("rules.id"), nullable=False)
    scan_run_id: Mapped[str | None] = mapped_column(ForeignKey(FK_SCAN_RUNS_ID))
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    business_rule: Mapped[str] = mapped_column(Text, nullable=False)
    why_this_rule_exists: Mapped[str | None] = mapped_column(Text)
    conditions_if: Mapped[str | None] = mapped_column(Text)
    actions_then: Mapped[str | None] = mapped_column(Text)
    exceptions_constraints: Mapped[str | None] = mapped_column(Text)
    ui_surface: Mapped[str | None] = mapped_column(Text)
    source_type_breakdown: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

    rule: Mapped[Rule] = relationship(back_populates="versions")


class RuleEvidence(Base):
    __tablename__ = "rule_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    rule_id: Mapped[str] = mapped_column(ForeignKey("rules.id"), nullable=False)
    rule_version_id: Mapped[str | None] = mapped_column(ForeignKey("rule_versions.id"))
    scan_run_id: Mapped[str | None] = mapped_column(ForeignKey(FK_SCAN_RUNS_ID))
    source_file_id: Mapped[str | None] = mapped_column(ForeignKey(FK_SOURCE_FILES_ID))
    source_type: Mapped[EvidenceSourceType] = mapped_column(
        Enum(EvidenceSourceType, **STR_ENUM_COLUMN_KW), nullable=False
    )
    reference_path: Mapped[str] = mapped_column(Text, nullable=False)
    external_ref: Mapped[str | None] = mapped_column(Text)
    start_line: Mapped[int | None] = mapped_column(Integer)
    end_line: Mapped[int | None] = mapped_column(Integer)
    snippet: Mapped[str] = mapped_column(Text, nullable=False, default="")
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    extraction_explanation: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

    rule: Mapped[Rule] = relationship(back_populates="evidence")


class RuleRelationship(Base, TimestampMixin):
    __tablename__ = "rule_relationships"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "from_rule_id",
            "to_rule_id",
            "relationship_type",
            name="uq_rule_relationship_edge",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_versions.id"))
    from_rule_id: Mapped[str] = mapped_column(ForeignKey("rules.id"), nullable=False)
    to_rule_id: Mapped[str] = mapped_column(ForeignKey("rules.id"), nullable=False)
    relationship_type: Mapped[RuleRelationshipType] = mapped_column(
        Enum(RuleRelationshipType, **STR_ENUM_COLUMN_KW), nullable=False
    )
    sequence_order: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text)


class RuleRelationshipSuggestion(Base, TimestampMixin):
    __tablename__ = "rule_relationship_suggestions"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "analysis_version_id",
            "source_rule_id",
            "target_rule_id",
            "suggested_relationship_type",
            name="uq_rule_relationship_suggestion_edge",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_versions.id"))
    source_rule_id: Mapped[str] = mapped_column(ForeignKey("rules.id"), nullable=False)
    target_rule_id: Mapped[str] = mapped_column(ForeignKey("rules.id"), nullable=False)
    suggested_relationship_type: Mapped[RuleRelationshipType] = mapped_column(
        Enum(RuleRelationshipType, **STR_ENUM_COLUMN_KW), nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    signals: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[RelationshipSuggestionStatus] = mapped_column(
        Enum(RelationshipSuggestionStatus, **STR_ENUM_COLUMN_KW),
        default=RelationshipSuggestionStatus.PENDING,
        nullable=False,
    )
    created_by: Mapped[str] = mapped_column(String(64), default="deterministic", nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RuleSourceClaim(Base):
    __tablename__ = "rule_source_claims"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_versions.id"))
    rule_id: Mapped[str | None] = mapped_column(ForeignKey("rules.id"))
    scan_run_id: Mapped[str | None] = mapped_column(ForeignKey(FK_SCAN_RUNS_ID))
    source_type: Mapped[EvidenceSourceType] = mapped_column(
        Enum(EvidenceSourceType, **STR_ENUM_COLUMN_KW), nullable=False
    )
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_claim: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    evidence_id: Mapped[str | None] = mapped_column(ForeignKey("rule_evidence.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class RuleConflict(Base, TimestampMixin):
    __tablename__ = "rule_conflicts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_versions.id"))
    rule_id: Mapped[str | None] = mapped_column(ForeignKey("rules.id"))
    scan_run_id: Mapped[str | None] = mapped_column(ForeignKey(FK_SCAN_RUNS_ID))
    # RA-04-003: legacy column. For structured/semantic conflicts the authoritative kind lives elsewhere,
    # so this is nullable to let future v2 rows omit it instead of faking a sentinel. Today's writers still
    # set a value (incl. a TEST_CODE sentinel for structured conflicts), so reads remain non-null for now.
    conflict_type: Mapped[ConflictType] = mapped_column(Enum(ConflictType, **STR_ENUM_COLUMN_KW), nullable=True)
    area: Mapped[str] = mapped_column(String(255), nullable=False)
    source_a_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_a_claim: Mapped[str] = mapped_column(Text, nullable=False)
    source_b_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_b_claim: Mapped[str] = mapped_column(Text, nullable=False)
    risk: Mapped[str] = mapped_column(String(50), default="medium", nullable=False)
    recommended_fix: Mapped[str | None] = mapped_column(Text)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    suggested_owner: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[RuleConflictStatus] = mapped_column(
        Enum(RuleConflictStatus, **STR_ENUM_COLUMN_KW), default=RuleConflictStatus.OPEN, nullable=False
    )
    resolution_note: Mapped[str | None] = mapped_column(Text)
    decision_reason: Mapped[str | None] = mapped_column(Text)
    conflict_kind: Mapped[str | None] = mapped_column(String(64))
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class RuleDecision(Base):
    __tablename__ = "rule_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    rule_id: Mapped[str] = mapped_column(ForeignKey("rules.id"), nullable=False)
    decided_by_user_id: Mapped[str | None] = mapped_column(ForeignKey(FK_USERS_ID))
    decision_type: Mapped[RuleDecisionType] = mapped_column(
        Enum(RuleDecisionType, **STR_ENUM_COLUMN_KW), nullable=False
    )
    decision_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class RuleReview(Base):
    __tablename__ = "rule_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    rule_id: Mapped[str] = mapped_column(ForeignKey("rules.id"), nullable=False)
    reviewed_by_user_id: Mapped[str | None] = mapped_column(ForeignKey(FK_USERS_ID))
    status_before: Mapped[str] = mapped_column(String(64), nullable=False)
    status_after: Mapped[str] = mapped_column(String(64), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class ImplementationGap(Base, TimestampMixin):
    __tablename__ = "implementation_gaps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_versions.id"))
    rule_id: Mapped[str | None] = mapped_column(ForeignKey("rules.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    current_observed_behavior: Mapped[str | None] = mapped_column(Text)
    expected_product_behavior: Mapped[str] = mapped_column(Text, nullable=False)
    backend_work_needed: Mapped[str | None] = mapped_column(Text)
    frontend_work_needed: Mapped[str | None] = mapped_column(Text)
    tests_needed: Mapped[str | None] = mapped_column(Text)
    acceptance_criteria: Mapped[str | None] = mapped_column(Text)
    risk: Mapped[str] = mapped_column(String(50), default="medium", nullable=False)
    priority: Mapped[ImplementationGapPriority] = mapped_column(
        Enum(ImplementationGapPriority, **STR_ENUM_COLUMN_KW),
        default=ImplementationGapPriority.MEDIUM,
        nullable=False,
    )
    status: Mapped[ImplementationGapStatus] = mapped_column(
        Enum(ImplementationGapStatus, **STR_ENUM_COLUMN_KW),
        default=ImplementationGapStatus.OPEN,
        nullable=False,
    )
    owner: Mapped[str | None] = mapped_column(String(200))
    review_note: Mapped[str | None] = mapped_column(Text)
    linked_conflict_id: Mapped[str | None] = mapped_column(String(36))
    gap_type: Mapped[str | None] = mapped_column(String(64))
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class ExportDocument(Base):
    __tablename__ = "export_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_versions.id"))
    scan_run_id: Mapped[str | None] = mapped_column(ForeignKey(FK_SCAN_RUNS_ID))
    export_type: Mapped[ExportType] = mapped_column(Enum(ExportType, **STR_ENUM_COLUMN_KW), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class SearchIndexRecord(Base, TimestampMixin):
    __tablename__ = "search_index_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_versions.id"))
    entity_type: Mapped[SearchEntityType] = mapped_column(Enum(SearchEntityType, **STR_ENUM_COLUMN_KW), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class RuleTraceLink(Base, TimestampMixin):
    __tablename__ = "rule_trace_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    rule_id: Mapped[str] = mapped_column(ForeignKey("rules.id"), nullable=False)
    source_file_id: Mapped[str | None] = mapped_column(ForeignKey(FK_SOURCE_FILES_ID))
    source_symbol_id: Mapped[str | None] = mapped_column(ForeignKey("source_symbols.id"))
    link_type: Mapped[RuleTraceLinkType] = mapped_column(Enum(RuleTraceLinkType, **STR_ENUM_COLUMN_KW), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class RuleLineage(Base, TimestampMixin):
    __tablename__ = "rule_lineage"
    __table_args__ = (Index("ix_rule_lineage_project", "project_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    from_rule_id: Mapped[str] = mapped_column(ForeignKey("rules.id"), nullable=False)
    to_rule_id: Mapped[str] = mapped_column(ForeignKey("rules.id"), nullable=False)
    relation: Mapped[str] = mapped_column(String(64), nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class SemanticObservation(Base, TimestampMixin):
    """Provider-neutral semantic analysis observation (SCIP/Serena/Roslyn/TS/Python/PHP)."""

    __tablename__ = "semantic_observations"
    __table_args__ = (
        Index("ix_semantic_obs_project_analysis", "project_id", "analysis_version_id"),
        Index("ix_semantic_obs_provider", "provider_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str] = mapped_column(ForeignKey("analysis_versions.id"), nullable=False)
    provider_key: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_version: Mapped[str] = mapped_column(String(64), nullable=False, default="1")
    observation_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    symbol_key: Mapped[str | None] = mapped_column(String(512))
    source_path: Mapped[str | None] = mapped_column(String(1024))
    start_line: Mapped[int | None] = mapped_column(Integer)
    end_line: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="succeeded")
    resolution_type: Mapped[str] = mapped_column(String(32), nullable=False, default="extracted")
    graph_node_id: Mapped[str | None] = mapped_column(ForeignKey("graph_nodes.id"))
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
