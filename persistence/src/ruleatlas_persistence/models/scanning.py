"""Database models for the scanning domain."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._base import (
    FK_PROJECTS_ID,
    FK_SCAN_RUNS_ID,
    FK_SOURCE_FILES_ID,
    JSON,
    STR_ENUM_COLUMN_KW,
    AnalysisVersionStatus,
    Base,
    Boolean,
    CoverageStatus,
    DateTime,
    Enum,
    EvidenceSourceType,
    Float,
    ForeignKey,
    Index,
    Integer,
    ManifestInclusionState,
    Mapped,
    RuntimeEvidenceConfidence,
    ScanStage,
    ScanStatus,
    ScanType,
    SourceFileClassification,
    SourceLocationType,
    SourceTreeNodeKind,
    SourceType,
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


class ClassificationOverride(Base, TimestampMixin):
    __tablename__ = "classification_overrides"
    __table_args__ = (UniqueConstraint("project_id", "pattern", name="uq_classification_override_project_pattern"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    pattern: Mapped[str] = mapped_column(Text, nullable=False)
    classification: Mapped[SourceFileClassification] = mapped_column(
        Enum(SourceFileClassification, **STR_ENUM_COLUMN_KW), nullable=False
    )
    file_kind: Mapped[str | None] = mapped_column(String(32))
    reason: Mapped[str | None] = mapped_column(Text)

    project: Mapped[Project] = relationship(back_populates="classification_overrides")


class FileTypeMapping(Base, TimestampMixin):
    """Global custom file type mapping overrides (built-ins live in code registry)."""

    __tablename__ = "file_type_mappings"
    __table_args__ = (UniqueConstraint("pattern", "match_type", name="uq_file_type_mapping_pattern_match_type"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    pattern: Mapped[str] = mapped_column(String(255), nullable=False)
    match_type: Mapped[str] = mapped_column(String(32), nullable=False)
    language: Mapped[str] = mapped_column(String(128), nullable=False)
    language_key: Mapped[str] = mapped_column(String(64), nullable=False)
    display_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    default_bucket_hint: Mapped[str] = mapped_column(String(32), nullable=False)
    comment_style: Mapped[str] = mapped_column(String(32), nullable=False)
    is_binary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_generated_hint: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AnalysisVersion(Base, TimestampMixin):
    __tablename__ = "analysis_versions"
    __table_args__ = (UniqueConstraint("project_id", "version_number", name="uq_analysis_version_project_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[AnalysisVersionStatus] = mapped_column(
        Enum(AnalysisVersionStatus, **STR_ENUM_COLUMN_KW),
        default=AnalysisVersionStatus.BUILDING,
        nullable=False,
    )
    scan_run_id: Mapped[str | None] = mapped_column(ForeignKey(FK_SCAN_RUNS_ID))
    scan_config_id: Mapped[str | None] = mapped_column(ForeignKey("scan_configs.id"))
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_note: Mapped[str | None] = mapped_column(Text)

    project: Mapped[Project] = relationship(
        back_populates="analysis_versions", foreign_keys="AnalysisVersion.project_id"
    )


class ScanConfig(Base, TimestampMixin):
    __tablename__ = "scan_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    include_globs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    exclude_globs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    max_file_size_bytes: Mapped[int] = mapped_column(Integer, default=5_000_000, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    proposal_scan_run_id: Mapped[str | None] = mapped_column(ForeignKey(FK_SCAN_RUNS_ID))

    project: Mapped[Project] = relationship(back_populates="scan_configs")


class SourceLocation(Base, TimestampMixin):
    __tablename__ = "source_locations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    scan_config_id: Mapped[str | None] = mapped_column(ForeignKey("scan_configs.id"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType, **STR_ENUM_COLUMN_KW), nullable=False)
    location_type: Mapped[SourceLocationType] = mapped_column(
        Enum(SourceLocationType, **STR_ENUM_COLUMN_KW), nullable=False
    )
    path_or_url: Mapped[str] = mapped_column(Text, nullable=False)
    include_globs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    exclude_globs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    confidence_weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    scan_depth: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    project: Mapped[Project] = relationship(back_populates="source_locations")


class ScanRun(Base, TimestampMixin):
    __tablename__ = "scan_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    scan_config_id: Mapped[str | None] = mapped_column(ForeignKey("scan_configs.id"))
    status: Mapped[ScanStatus] = mapped_column(
        Enum(ScanStatus, **STR_ENUM_COLUMN_KW), default=ScanStatus.QUEUED, nullable=False
    )
    current_stage: Mapped[ScanStage] = mapped_column(
        Enum(ScanStage, **STR_ENUM_COLUMN_KW), default=ScanStage.QUEUED, nullable=False
    )
    scan_type: Mapped[ScanType] = mapped_column(Enum(ScanType, **STR_ENUM_COLUMN_KW), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    worker_id: Mapped[str | None] = mapped_column(String(128))
    job_id: Mapped[str | None] = mapped_column(String(128))

    project: Mapped[Project] = relationship(back_populates="scan_runs")


class SourceFile(Base, TimestampMixin):
    __tablename__ = "source_files"
    __table_args__ = (UniqueConstraint("project_id", "path", name="uq_source_file_project_path"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    scan_run_id: Mapped[str | None] = mapped_column(ForeignKey(FK_SCAN_RUNS_ID))
    source_location_id: Mapped[str | None] = mapped_column(ForeignKey("source_locations.id"))
    path: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType, **STR_ENUM_COLUMN_KW), nullable=False)
    detected_classification: Mapped[SourceFileClassification | None] = mapped_column(
        Enum(SourceFileClassification, **STR_ENUM_COLUMN_KW)
    )
    classification: Mapped[SourceFileClassification] = mapped_column(
        Enum(SourceFileClassification, **STR_ENUM_COLUMN_KW), nullable=False
    )
    classification_override_id: Mapped[str | None] = mapped_column(ForeignKey("classification_overrides.id"))
    file_kind_override: Mapped[str | None] = mapped_column(String(32))
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    line_count: Mapped[int | None] = mapped_column(Integer)
    code_line_count: Mapped[int | None] = mapped_column(Integer)
    comment_line_count: Mapped[int | None] = mapped_column(Integer)
    blank_line_count: Mapped[int | None] = mapped_column(Integer)
    line_count_method: Mapped[str | None] = mapped_column(String(32))
    production_bucket: Mapped[str | None] = mapped_column(String(64))
    language: Mapped[str | None] = mapped_column(String(64))
    scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SourceTreeNode(Base, TimestampMixin):
    __tablename__ = "source_tree_nodes"
    __table_args__ = (
        UniqueConstraint("scan_run_id", "display_path", name="uq_source_tree_scan_display_path"),
        Index("ix_source_tree_nodes_scan_parent", "scan_run_id", "parent_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    scan_run_id: Mapped[str] = mapped_column(ForeignKey(FK_SCAN_RUNS_ID), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("source_tree_nodes.id"))
    node_kind: Mapped[SourceTreeNodeKind] = mapped_column(
        Enum(SourceTreeNodeKind, **STR_ENUM_COLUMN_KW), nullable=False
    )
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    display_path: Mapped[str] = mapped_column(Text, nullable=False)
    raw_path: Mapped[str | None] = mapped_column(Text)
    source_file_id: Mapped[str | None] = mapped_column(ForeignKey(FK_SOURCE_FILES_ID))
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    language: Mapped[str | None] = mapped_column(String(64))
    extension: Mapped[str | None] = mapped_column(String(64))
    file_kind: Mapped[str | None] = mapped_column(String(64))
    classification: Mapped[str | None] = mapped_column(String(64))
    detected_classification: Mapped[str | None] = mapped_column(String(64))
    classification_signal: Mapped[str | None] = mapped_column(String(64))
    classification_explanation: Mapped[str | None] = mapped_column(Text)
    override_pattern: Mapped[str | None] = mapped_column(String(512))
    production_bucket: Mapped[str | None] = mapped_column(String(64))
    subfolders_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    child_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    code_line_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comment_line_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blank_line_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    line_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rule_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    needs_review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class SourceSymbol(Base, TimestampMixin):
    __tablename__ = "source_symbols"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    source_file_id: Mapped[str] = mapped_column(ForeignKey(FK_SOURCE_FILES_ID), nullable=False)
    symbol_type: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_symbol_id: Mapped[str | None] = mapped_column(ForeignKey("source_symbols.id"))


class CoverageReport(Base, TimestampMixin):
    __tablename__ = "coverage_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_versions.id"))
    scan_run_id: Mapped[str | None] = mapped_column(ForeignKey(FK_SCAN_RUNS_ID))
    source_file_id: Mapped[str | None] = mapped_column(ForeignKey(FK_SOURCE_FILES_ID))
    format: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[CoverageStatus] = mapped_column(
        Enum(CoverageStatus, **STR_ENUM_COLUMN_KW), default=CoverageStatus.PENDING, nullable=False
    )
    summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class CoverageFile(Base, TimestampMixin):
    __tablename__ = "coverage_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    coverage_report_id: Mapped[str] = mapped_column(ForeignKey("coverage_reports.id"), nullable=False)
    source_file_id: Mapped[str | None] = mapped_column(ForeignKey(FK_SOURCE_FILES_ID))
    path: Mapped[str] = mapped_column(Text, nullable=False)
    line_rate: Mapped[float | None] = mapped_column(Float)
    branch_rate: Mapped[float | None] = mapped_column(Float)


class CoverageLine(Base):
    __tablename__ = "coverage_lines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    coverage_file_id: Mapped[str] = mapped_column(ForeignKey("coverage_files.id"), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    graph_node_id: Mapped[str | None] = mapped_column(ForeignKey("graph_nodes.id"))
    condition_covered: Mapped[bool | None] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class CoverageBranch(Base):
    __tablename__ = "coverage_branches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    coverage_file_id: Mapped[str] = mapped_column(ForeignKey("coverage_files.id"), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    branch_number: Mapped[int] = mapped_column(Integer, nullable=False)
    taken_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class TestCase(Base, TimestampMixin):
    __tablename__ = "test_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    source_file_id: Mapped[str | None] = mapped_column(ForeignKey(FK_SOURCE_FILES_ID))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    test_type: Mapped[str] = mapped_column(String(64), nullable=False)
    start_line: Mapped[int | None] = mapped_column(Integer)
    end_line: Mapped[int | None] = mapped_column(Integer)


class TestCoverageLink(Base, TimestampMixin):
    __tablename__ = "test_coverage_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    test_case_id: Mapped[str] = mapped_column(ForeignKey("test_cases.id"), nullable=False)
    coverage_line_id: Mapped[str] = mapped_column(ForeignKey("coverage_lines.id"), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class RuleCoverageAssessment(Base, TimestampMixin):
    __tablename__ = "rule_coverage_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    rule_id: Mapped[str] = mapped_column(ForeignKey("rules.id"), nullable=False)
    coverage_report_id: Mapped[str | None] = mapped_column(ForeignKey("coverage_reports.id"))
    assessment_summary: Mapped[str] = mapped_column(Text, nullable=False)
    line_coverage_pct: Mapped[float | None] = mapped_column(Float)
    branch_coverage_pct: Mapped[float | None] = mapped_column(Float)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_candidate_signal: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RuntimeEvidenceImport(Base, TimestampMixin):
    __tablename__ = "runtime_evidence_imports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_versions.id"))
    scan_run_id: Mapped[str | None] = mapped_column(ForeignKey(FK_SCAN_RUNS_ID))
    source_label: Mapped[str] = mapped_column(String(255), nullable=False)
    format: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="pending", nullable=False)
    summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class RuntimeLogEvidence(Base):
    __tablename__ = "runtime_log_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    rule_id: Mapped[str | None] = mapped_column(ForeignKey("rules.id"))
    import_id: Mapped[str | None] = mapped_column(ForeignKey("runtime_evidence_imports.id"))
    source_type: Mapped[EvidenceSourceType] = mapped_column(
        Enum(EvidenceSourceType, **STR_ENUM_COLUMN_KW), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confidence: Mapped[RuntimeEvidenceConfidence] = mapped_column(
        Enum(RuntimeEvidenceConfidence, **STR_ENUM_COLUMN_KW),
        default=RuntimeEvidenceConfidence.MEDIUM,
        nullable=False,
    )
    is_candidate_signal: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class AnalysisManifest(Base, TimestampMixin):
    __tablename__ = "analysis_manifests"
    __table_args__ = (
        UniqueConstraint("scan_run_id", name="uq_analysis_manifest_scan_run"),
        Index("ix_analysis_manifests_project_id", "project_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    scan_run_id: Mapped[str] = mapped_column(ForeignKey(FK_SCAN_RUNS_ID), nullable=False)
    analysis_version_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_versions.id"))
    manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    immutable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    file_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    included_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    excluded_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unsupported_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    policy_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    files: Mapped[list[AnalysisManifestFile]] = relationship(back_populates="manifest")


class AnalysisManifestFile(Base, TimestampMixin):
    __tablename__ = "analysis_manifest_files"
    __table_args__ = (
        UniqueConstraint("manifest_id", "path", name="uq_analysis_manifest_file_path"),
        Index("ix_analysis_manifest_files_manifest_id", "manifest_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    manifest_id: Mapped[str] = mapped_column(ForeignKey("analysis_manifests.id"), nullable=False)
    source_file_id: Mapped[str | None] = mapped_column(ForeignKey("source_files.id"))
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    inclusion_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ManifestInclusionState.INCLUDED.value
    )
    language_key: Mapped[str | None] = mapped_column(String(64))
    source_role: Mapped[str | None] = mapped_column(String(64))
    file_kind: Mapped[str | None] = mapped_column(String(32))
    classification: Mapped[str | None] = mapped_column(String(64))
    classification_origin: Mapped[str | None] = mapped_column(String(64))
    exclusion_reason: Mapped[str | None] = mapped_column(String(255))
    analyzer_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    policy_sources: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    manifest: Mapped[AnalysisManifest] = relationship(back_populates="files")


class ConfigurationOverride(Base, TimestampMixin):
    __tablename__ = "configuration_overrides"
    __table_args__ = (
        UniqueConstraint("scope", "scope_id", "key", name="uq_configuration_override_scope_key"),
        Index("ix_configuration_overrides_key", "key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_id: Mapped[str | None] = mapped_column(String(36))
    value_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    actor: Mapped[str | None] = mapped_column(String(200))
    definition_version: Mapped[str | None] = mapped_column(String(32))


class ConfigurationOverrideHistory(Base, TimestampMixin):
    __tablename__ = "configuration_override_history"
    __table_args__ = (Index("ix_configuration_override_history_key", "key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    override_id: Mapped[str | None] = mapped_column(String(36))
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_id: Mapped[str | None] = mapped_column(String(36))
    old_value_json: Mapped[dict | None] = mapped_column(JSON)
    new_value_json: Mapped[dict | None] = mapped_column(JSON)
    actor: Mapped[str | None] = mapped_column(String(200))
    reason: Mapped[str | None] = mapped_column(Text)
    action: Mapped[str] = mapped_column(String(32), nullable=False, default="set")


class CompositePipelineRun(Base, TimestampMixin):
    __tablename__ = "composite_pipeline_runs"
    __table_args__ = (
        Index("ix_composite_pipeline_project_analysis", "project_id", "analysis_version_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str] = mapped_column(ForeignKey("analysis_versions.id"), nullable=False)
    scan_run_id: Mapped[str | None] = mapped_column(ForeignKey(FK_SCAN_RUNS_ID))
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="full")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    stages_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
