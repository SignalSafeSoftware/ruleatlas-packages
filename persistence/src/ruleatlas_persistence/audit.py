"""Audit-recording port (dependency inversion).

Context packages (claims, ai, …) record an audit trail by calling
:func:`record_audit_event` **without importing the app**. The app registers the
concrete recorder at import of ``ruleatlas.application.audit.audit_service`` — the
recorder resolves the request-scoped actor and writes via the service factory.

Registration always precedes use: audit is only ever recorded at *runtime* (inside
request handlers / service methods), and every runtime entry point imports the app
audit module (33 call sites); tests force registration via ``conftest``. If no
recorder is registered, :func:`record_audit_event` raises a clear error rather than
silently dropping the event.
"""

from __future__ import annotations

from typing import Any, Protocol

from ruleatlas_contracts.enums import AuditEntityType, AuditEventType
from sqlalchemy.orm import Session

from ruleatlas_persistence.models import AuditEvent

__all__ = ["AuditRecorder", "record_audit_event", "set_audit_recorder"]


class AuditRecorder(Protocol):
    """Concrete audit writer supplied by the application composition root."""

    def __call__(
        self,
        session: Session,
        *,
        event_type: AuditEventType | str,
        summary: str,
        project_id: str | None = ...,
        organization_id: str | None = ...,
        entity_type: AuditEntityType | str | None = ...,
        entity_id: str | None = ...,
        actor: str | None = ...,
        actor_user_id: str | None = ...,
        metadata: dict[str, Any] | None = ...,
    ) -> AuditEvent: ...


_recorder: AuditRecorder | None = None


def set_audit_recorder(recorder: AuditRecorder) -> None:
    """Register the concrete audit recorder (called by the app on import)."""
    global _recorder
    _recorder = recorder


def record_audit_event(
    session: Session,
    *,
    event_type: AuditEventType | str,
    summary: str,
    project_id: str | None = None,
    organization_id: str | None = None,
    entity_type: AuditEntityType | str | None = None,
    entity_id: str | None = None,
    actor: str | None = None,
    actor_user_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    """Record an audit event via the registered recorder."""
    if _recorder is None:  # pragma: no cover - defensive; app/conftest always registers
        raise RuntimeError(
            "No audit recorder registered. Import ruleatlas.application.audit.audit_service "
            "so the application registers its recorder before recording audit events."
        )
    return _recorder(
        session,
        event_type=event_type,
        summary=summary,
        project_id=project_id,
        organization_id=organization_id,
        entity_type=entity_type,
        entity_id=entity_id,
        actor=actor,
        actor_user_id=actor_user_id,
        metadata=metadata,
    )
