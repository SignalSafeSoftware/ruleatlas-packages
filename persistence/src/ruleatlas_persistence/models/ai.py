"""Database models for the ai domain."""

from __future__ import annotations

from ._base import (
    FK_ORGANIZATIONS_ID,
    FK_PROJECTS_ID,
    FK_SCAN_RUNS_ID,
    FK_USERS_ID,
    JSON,
    STR_ENUM_COLUMN_KW,
    AiProviderMode,
    AiSuggestionStatus,
    AiTaskRunStatus,
    AiTaskType,
    Base,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Mapped,
    String,
    Text,
    TimestampMixin,
    UniqueConstraint,
    datetime,
    mapped_column,
    now_utc,
    uuid_str,
)


class AiTaskRun(Base, TimestampMixin):
    __tablename__ = "ai_task_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    task_type: Mapped[AiTaskType] = mapped_column(Enum(AiTaskType, **STR_ENUM_COLUMN_KW), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="none")
    model: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[AiTaskRunStatus] = mapped_column(
        Enum(AiTaskRunStatus, **STR_ENUM_COLUMN_KW),
        default=AiTaskRunStatus.PENDING,
        nullable=False,
    )
    input_hash: Mapped[str | None] = mapped_column(String(128))
    source_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)


class AiSuggestion(Base, TimestampMixin):
    __tablename__ = "ai_suggestions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    task_run_id: Mapped[str] = mapped_column(ForeignKey("ai_task_runs.id"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    suggestion_type: Mapped[str] = mapped_column(String(64), nullable=False)
    suggested_value: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    source_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[AiSuggestionStatus] = mapped_column(
        Enum(AiSuggestionStatus, **STR_ENUM_COLUMN_KW),
        default=AiSuggestionStatus.PENDING,
        nullable=False,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AiModelUsage(Base):
    __tablename__ = "ai_model_usage"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str | None] = mapped_column(ForeignKey(FK_PROJECTS_ID))
    scan_run_id: Mapped[str | None] = mapped_column(ForeignKey(FK_SCAN_RUNS_ID))
    provider_mode: Mapped[AiProviderMode] = mapped_column(Enum(AiProviderMode, **STR_ENUM_COLUMN_KW), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_cost_usd: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str | None] = mapped_column(ForeignKey(FK_PROJECTS_ID))
    organization_id: Mapped[str | None] = mapped_column(ForeignKey(FK_ORGANIZATIONS_ID))
    actor: Mapped[str] = mapped_column(String(200), default="system", nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey(FK_USERS_ID))
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(36))
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class IntegrationCredential(Base, TimestampMixin):
    __tablename__ = "integration_credentials"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "integration_type",
            "name",
            name="uq_integration_credential_org_type_name",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    organization_id: Mapped[str] = mapped_column(ForeignKey(FK_ORGANIZATIONS_ID), nullable=False)
    integration_type: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    encrypted_secret: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    last_rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AiProviderConfiguration(Base, TimestampMixin):
    __tablename__ = "ai_provider_configurations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    organization_id: Mapped[str] = mapped_column(ForeignKey(FK_ORGANIZATIONS_ID), nullable=False)
    provider_mode: Mapped[AiProviderMode] = mapped_column(Enum(AiProviderMode, **STR_ENUM_COLUMN_KW), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    settings_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class AiProviderConnection(Base, TimestampMixin):
    __tablename__ = "ai_provider_connections"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="ix_ai_provider_connections_org_name"),
        Index("ix_ai_provider_connections_org_provider", "organization_id", "provider_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    organization_id: Mapped[str] = mapped_column(ForeignKey(FK_ORGANIZATIONS_ID), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    provider_type: Mapped[str] = mapped_column(String(64), nullable=False)
    credential_source: Mapped[str] = mapped_column(String(64), nullable=False)
    encrypted_credential_reference: Mapped[str | None] = mapped_column(String(512))
    environment_variable_name: Mapped[str | None] = mapped_column(String(128))
    base_url: Mapped[str | None] = mapped_column(String(1024))
    organization_identifier: Mapped[str | None] = mapped_column(String(255))
    project_identifier: Mapped[str | None] = mapped_column(String(255))
    api_version: Mapped[str | None] = mapped_column(String(64))
    deployment_name: Mapped[str | None] = mapped_column(String(255))
    allow_custom_base_url: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="untested", nullable=False)
    last_health_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_health_check_status: Mapped[str | None] = mapped_column(String(32))
    last_health_check_message: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(String(255))
    updated_by: Mapped[str | None] = mapped_column(String(255))
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class AiModelCatalogEntry(Base, TimestampMixin):
    __tablename__ = "ai_model_catalog_entries"
    __table_args__ = (
        UniqueConstraint("connection_id", "provider_model_id", name="uq_ai_model_catalog_connection_model"),
        Index("ix_ai_model_catalog_connection_availability", "connection_id", "availability_status"),
        Index(
            "ix_ai_model_catalog_org_enabled",
            "organization_id",
            "enabled_for_selection",
            "ruleatlas_compatible",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    connection_id: Mapped[str] = mapped_column(ForeignKey("ai_provider_connections.id"), nullable=False)
    organization_id: Mapped[str] = mapped_column(ForeignKey(FK_ORGANIZATIONS_ID), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    raw_metadata_hash: Mapped[str | None] = mapped_column(String(64))
    raw_metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    availability_status: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    context_window: Mapped[int | None] = mapped_column(Integer)
    maximum_output_tokens: Mapped[int | None] = mapped_column(Integer)
    supports_text_input: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    supports_text_output: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    supports_tool_calling: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_structured_output: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_json_schema: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_reasoning: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_streaming: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_embeddings: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_image_input: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ruleatlas_compatible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    compatibility_status: Mapped[str] = mapped_column(String(32), default="untested", nullable=False)
    compatibility_reason: Mapped[str | None] = mapped_column(Text)
    last_compatibility_test_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    enabled_for_selection: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source: Mapped[str] = mapped_column(String(64), default="discovered", nullable=False)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class AiModelCompatibilityTest(Base, TimestampMixin):
    __tablename__ = "ai_model_compatibility_tests"
    __table_args__ = (Index("ix_ai_model_compat_tests_catalog", "catalog_entry_id", "tested_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    catalog_entry_id: Mapped[str] = mapped_column(ForeignKey("ai_model_catalog_entries.id"), nullable=False)
    connection_id: Mapped[str] = mapped_column(ForeignKey("ai_provider_connections.id"), nullable=False)
    organization_id: Mapped[str] = mapped_column(ForeignKey(FK_ORGANIZATIONS_ID), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    test_version: Mapped[str] = mapped_column(String(32), nullable=False)
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    failure_category: Mapped[str | None] = mapped_column(String(64))
    sanitized_detail: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    token_usage_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    estimated_cost: Mapped[float | None] = mapped_column(Float)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    tested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectAiConfiguration(Base, TimestampMixin):
    __tablename__ = "project_ai_configurations"
    __table_args__ = (
        UniqueConstraint("project_id", name="uq_project_ai_configurations_project"),
        Index("ix_project_ai_configurations_connection", "connection_id"),
        Index("ix_project_ai_configurations_synthesis_model", "synthesis_model_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    connection_id: Mapped[str | None] = mapped_column(ForeignKey("ai_provider_connections.id"))
    synthesis_model_id: Mapped[str | None] = mapped_column(ForeignKey("ai_model_catalog_entries.id"))
    embedding_model_id: Mapped[str | None] = mapped_column(ForeignKey("ai_model_catalog_entries.id"))
    fallback_connection_id: Mapped[str | None] = mapped_column(ForeignKey("ai_provider_connections.id"))
    fallback_model_id: Mapped[str | None] = mapped_column(ForeignKey("ai_model_catalog_entries.id"))
    fallback_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    synthesis_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_deterministic_fallback: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_real_provider: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reasoning_effort: Mapped[str | None] = mapped_column(String(32))
    temperature: Mapped[float | None] = mapped_column(Float)
    maximum_input_tokens: Mapped[int | None] = mapped_column(Integer)
    maximum_output_tokens: Mapped[int | None] = mapped_column(Integer)
    maximum_tool_calls: Mapped[int | None] = mapped_column(Integer)
    maximum_cost_per_rule: Mapped[float | None] = mapped_column(Float)
    maximum_cost_per_scan: Mapped[float | None] = mapped_column(Float)
    require_structured_output: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_tool_calling: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    require_citation_validation: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_approval_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class AiInvestigationTrace(Base, TimestampMixin):
    __tablename__ = "ai_investigation_traces"
    __table_args__ = (
        UniqueConstraint("analysis_version_id", "idempotency_key", name="uq_ai_trace_idempotency"),
        Index("ix_ai_traces_project_analysis", "project_id", "analysis_version_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str] = mapped_column(ForeignKey("analysis_versions.id"), nullable=False)
    claim_cluster_id: Mapped[str | None] = mapped_column(ForeignKey("claim_clusters.id"))
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_key: Mapped[str] = mapped_column(String(64), nullable=False)
    model_key: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False, default="1")
    mcp_version: Mapped[str] = mapped_column(String(64), nullable=False, default="1")
    tool_calls_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    evidence_ids_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    output_hash: Mapped[str | None] = mapped_column(String(64))
    output_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    cost_units: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")
    error_message: Mapped[str | None] = mapped_column(Text)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
