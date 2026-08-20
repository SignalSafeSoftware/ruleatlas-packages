from __future__ import annotations

from datetime import datetime

from ruleatlas_contracts.enums import (
    AiProviderMode,
    AiSuggestionStatus,
    AiTaskRunStatus,
    AiTaskType,
    AnalysisVersionStatus,
    BddStepLinkStatus,
    ClaimClusterRole,
    ClaimClusterStatus,
    ConflictType,
    CoverageStatus,
    EvidenceSourceType,
    ExportType,
    GraphProviderStatus,
    GraphResolutionType,
    ImplementationGapPriority,
    ImplementationGapStatus,
    ManifestInclusionState,
    RelationshipSuggestionStatus,
    RuleCategory,
    RuleConflictStatus,
    RuleDecisionType,
    RuleRelationshipType,
    RuleStatus,
    RuleTraceLinkType,
    RuntimeEvidenceConfidence,
    ScanStage,
    ScanStatus,
    ScanType,
    SearchEntityType,
    SourceClaimRole,
    SourceClaimStatus,
    SourceFileClassification,
    SourceLocationType,
    SourceTreeNodeKind,
    SourceType,
    TestAssertionKind,
    TestExecutionStatus,
    TestFramework,
)
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ruleatlas_persistence.base import Base
from ruleatlas_persistence.enum_column import STR_ENUM_COLUMN_KW
from ruleatlas_persistence.mixins import TimestampMixin, now_utc, uuid_str

FK_ORGANIZATIONS_ID = "organizations.id"
FK_USERS_ID = "users.id"
FK_PROJECTS_ID = "projects.id"
FK_SCAN_RUNS_ID = "scan_runs.id"
FK_SOURCE_FILES_ID = "source_files.id"
FK_ANALYSIS_VERSIONS_ID = "analysis_versions.id"
FK_GRAPH_NODES_ID = "graph_nodes.id"
FK_SOURCE_CLAIMS_ID = "source_claims.id"
FK_AI_PROVIDER_CONNECTIONS_ID = "ai_provider_connections.id"
FK_AI_MODEL_CATALOG_ENTRIES_ID = "ai_model_catalog_entries.id"
FK_SCAN_CONFIGS_ID = "scan_configs.id"
FK_RULES_ID = "rules.id"
FK_TICKET_CONNECTIONS_ID = "ticket_connections.id"

# Explicit __all__ so `from ._base import *` is visible to mypy.
__all__ = [
    "FK_AI_MODEL_CATALOG_ENTRIES_ID",
    "FK_AI_PROVIDER_CONNECTIONS_ID",
    "FK_ANALYSIS_VERSIONS_ID",
    "FK_GRAPH_NODES_ID",
    "FK_ORGANIZATIONS_ID",
    "FK_PROJECTS_ID",
    "FK_RULES_ID",
    "FK_SCAN_CONFIGS_ID",
    "FK_SCAN_RUNS_ID",
    "FK_SOURCE_CLAIMS_ID",
    "FK_SOURCE_FILES_ID",
    "FK_TICKET_CONNECTIONS_ID",
    "FK_USERS_ID",
    "JSON",
    "STR_ENUM_COLUMN_KW",
    "AiProviderMode",
    "AiSuggestionStatus",
    "AiTaskRunStatus",
    "AiTaskType",
    "AnalysisVersionStatus",
    "Base",
    "BddStepLinkStatus",
    "Boolean",
    "ClaimClusterRole",
    "ClaimClusterStatus",
    "ConflictType",
    "CoverageStatus",
    "DateTime",
    "Enum",
    "EvidenceSourceType",
    "ExportType",
    "Float",
    "ForeignKey",
    "GraphProviderStatus",
    "GraphResolutionType",
    "ImplementationGapPriority",
    "ImplementationGapStatus",
    "Index",
    "Integer",
    "ManifestInclusionState",
    "Mapped",
    "RelationshipSuggestionStatus",
    "RuleCategory",
    "RuleConflictStatus",
    "RuleDecisionType",
    "RuleRelationshipType",
    "RuleStatus",
    "RuleTraceLinkType",
    "RuntimeEvidenceConfidence",
    "ScanStage",
    "ScanStatus",
    "ScanType",
    "SearchEntityType",
    "SourceClaimRole",
    "SourceClaimStatus",
    "SourceFileClassification",
    "SourceLocationType",
    "SourceTreeNodeKind",
    "SourceType",
    "String",
    "TestAssertionKind",
    "TestExecutionStatus",
    "TestFramework",
    "Text",
    "TimestampMixin",
    "UniqueConstraint",
    "datetime",
    "mapped_column",
    "now_utc",
    "relationship",
    "uuid_str",
]
