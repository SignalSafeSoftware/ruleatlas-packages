from __future__ import annotations

from typing import Any

from sqlalchemy import event

from ruleatlas_persistence.models import AuditEvent


class AuditEventImmutableError(RuntimeError):
    pass


@event.listens_for(AuditEvent, "before_update")
def _deny_audit_event_update(_mapper: Any, _connection: Any, _target: Any) -> None:
    raise AuditEventImmutableError("Audit events are append-only")


@event.listens_for(AuditEvent, "before_delete")
def _deny_audit_event_delete(_mapper: Any, _connection: Any, _target: Any) -> None:
    raise AuditEventImmutableError("Audit events are append-only")
