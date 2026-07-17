"""Integration smoke tests for the ORM layer: mixins, schema, and the audit port."""

from __future__ import annotations

from datetime import datetime

import ruleatlas_persistence.models as _models  # noqa: F401  (register every table on Base.metadata)
from ruleatlas_persistence import audit
from ruleatlas_persistence.base import Base
from ruleatlas_persistence.mixins import now_utc, uuid_str
from sqlalchemy import create_engine


def test_now_utc_is_utc_datetime() -> None:
    value = now_utc()
    assert isinstance(value, datetime)
    assert value.tzinfo is not None


def test_uuid_str_is_unique() -> None:
    a, b = uuid_str(), uuid_str()
    assert isinstance(a, str) and len(a) >= 32
    assert a != b


def test_all_tables_create_in_sqlite() -> None:
    # Creating the entire schema in SQLite validates the models are internally consistent.
    assert "organizations" in Base.metadata.tables
    assert len(Base.metadata.tables) >= 80
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    engine.dispose()


def test_audit_port_delegates_to_registered_recorder() -> None:
    original = audit._recorder  # noqa: SLF001 - test saves/restores the module-level recorder
    seen: list[dict] = []

    def fake(session: object, **kwargs: object) -> object:
        seen.append(kwargs)
        return object()

    try:
        audit.set_audit_recorder(fake)
        audit.record_audit_event(None, event_type="test.event", summary="hello")
    finally:
        audit._recorder = original  # noqa: SLF001

    assert seen and seen[0]["summary"] == "hello"
    assert seen[0]["event_type"] == "test.event"
