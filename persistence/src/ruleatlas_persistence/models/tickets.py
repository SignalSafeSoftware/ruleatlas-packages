"""Database models for the tickets domain."""

from __future__ import annotations

from ._base import (
    FK_ORGANIZATIONS_ID,
    FK_PROJECTS_ID,
    JSON,
    Base,
    Boolean,
    DateTime,
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


class TicketConnection(Base, TimestampMixin):
    """Org-scoped ticket provider connection (Jira/Trello share schema)."""

    __tablename__ = "ticket_connections"
    __table_args__ = (
        UniqueConstraint("organization_id", "provider_key", "name", name="uq_ticket_connection_org_provider_name"),
        Index("ix_ticket_connections_org", "organization_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    organization_id: Mapped[str] = mapped_column(ForeignKey(FK_ORGANIZATIONS_ID), nullable=False)
    project_id: Mapped[str | None] = mapped_column(ForeignKey(FK_PROJECTS_ID))
    provider_key: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False, default="default")
    site_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    selected_projects_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    filter_expression: Mapped[str | None] = mapped_column(Text)
    credential_name: Mapped[str] = mapped_column(String(128), nullable=False, default="api_token")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="idle")
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    health_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class TicketSyncCursor(Base, TimestampMixin):
    __tablename__ = "ticket_sync_cursors"
    __table_args__ = (
        UniqueConstraint("connection_id", name="uq_ticket_sync_cursor_connection"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    connection_id: Mapped[str] = mapped_column(ForeignKey("ticket_connections.id"), nullable=False)
    cursor_value: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class ExternalTicket(Base, TimestampMixin):
    __tablename__ = "external_tickets"
    __table_args__ = (
        UniqueConstraint("connection_id", "external_id", name="uq_external_ticket_connection_external"),
        Index("ix_external_tickets_project", "project_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    organization_id: Mapped[str] = mapped_column(ForeignKey(FK_ORGANIZATIONS_ID), nullable=False)
    project_id: Mapped[str | None] = mapped_column(ForeignKey(FK_PROJECTS_ID))
    connection_id: Mapped[str] = mapped_column(ForeignKey("ticket_connections.id"), nullable=False)
    provider_key: Mapped[str] = mapped_column(String(32), nullable=False)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str | None] = mapped_column(String(64))
    source_url: Mapped[str | None] = mapped_column(String(2048))
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    current_revision_id: Mapped[str | None] = mapped_column(String(36))
    labels_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class TicketRevision(Base, TimestampMixin):
    """Immutable ticket revision — never updated in place."""

    __tablename__ = "ticket_revisions"
    __table_args__ = (
        UniqueConstraint("external_ticket_id", "revision_hash", name="uq_ticket_revision_hash"),
        Index("ix_ticket_revisions_ticket", "external_ticket_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    external_ticket_id: Mapped[str] = mapped_column(ForeignKey("external_tickets.id"), nullable=False)
    revision_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    acceptance_criteria: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(64))
    comments_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    links_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    labels_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    change_summary: Mapped[str | None] = mapped_column(Text)
    untrusted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class TicketWebhookDelivery(Base, TimestampMixin):
    __tablename__ = "ticket_webhook_deliveries"
    __table_args__ = (Index("ix_ticket_webhook_connection_status", "connection_id", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    connection_id: Mapped[str] = mapped_column(ForeignKey("ticket_connections.id"), nullable=False)
    provider_key: Mapped[str] = mapped_column(String(32), nullable=False)
    delivery_id: Mapped[str | None] = mapped_column(String(128))
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RuntimeEvent(Base, TimestampMixin):
    """Provider-neutral runtime observation — never a rule definition by itself."""

    __tablename__ = "runtime_events"
    __table_args__ = (
        UniqueConstraint("project_id", "content_hash", name="uq_runtime_event_project_hash"),
        Index("ix_runtime_events_project_analysis", "project_id", "analysis_version_id"),
        Index("ix_runtime_events_provider", "provider_key"),
        Index("ix_runtime_events_trace", "trace_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False)
    analysis_version_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_versions.id"))
    import_id: Mapped[str | None] = mapped_column(ForeignKey("runtime_evidence_imports.id"))
    provider_key: Mapped[str] = mapped_column(String(64), nullable=False)
    event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trace_id: Mapped[str | None] = mapped_column(String(128))
    span_id: Mapped[str | None] = mapped_column(String(128))
    actor: Mapped[str | None] = mapped_column(String(255))
    tenant: Mapped[str | None] = mapped_column(String(255))
    operation: Mapped[str | None] = mapped_column(String(512))
    endpoint: Mapped[str | None] = mapped_column(String(1024))
    state_before: Mapped[str | None] = mapped_column(Text)
    state_after: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    exception_text: Mapped[str | None] = mapped_column(Text)
    message: Mapped[str | None] = mapped_column(Text)
    service_name: Mapped[str | None] = mapped_column(String(255))
    privacy_class: Mapped[str] = mapped_column(String(32), nullable=False, default="internal")
    retention_class: Mapped[str] = mapped_column(String(32), nullable=False, default="standard")
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    graph_node_key: Mapped[str | None] = mapped_column(String(512))
    graph_node_id: Mapped[str | None] = mapped_column(ForeignKey("graph_nodes.id"))
    redacted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    raw_payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_rule_definition: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class RuntimeEventLink(Base, TimestampMixin):
    """Links a runtime event to a rule and/or source claim."""

    __tablename__ = "runtime_event_links"
    __table_args__ = (
        Index("ix_runtime_event_links_event", "runtime_event_id"),
        Index("ix_runtime_event_links_rule", "rule_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    runtime_event_id: Mapped[str] = mapped_column(ForeignKey("runtime_events.id"), nullable=False)
    rule_id: Mapped[str | None] = mapped_column(ForeignKey("rules.id"))
    source_claim_id: Mapped[str | None] = mapped_column(ForeignKey("source_claims.id"))
    link_kind: Mapped[str] = mapped_column(String(64), nullable=False, default="observes")
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
