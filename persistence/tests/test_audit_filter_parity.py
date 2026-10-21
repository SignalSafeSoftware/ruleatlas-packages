"""Audit scope predicates stay separate from their shared filters."""

from collections.abc import Iterable
from datetime import datetime
from typing import TypedDict

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ruleatlas_persistence.base import Base
from ruleatlas_persistence.models import AuditEvent
from ruleatlas_persistence.repositories.factory import RepositoryFactory


class AuditFilters(TypedDict):
    event_type: str
    actor_user_id: str
    from_date: datetime
    to_date: datetime


def audit_ids(rows: Iterable[object]) -> list[str]:
    result: list[str] = []
    for row in rows:
        assert isinstance(row, AuditEvent)
        result.append(row.id)
    return result


def test_audit_filters_preserve_scope_or_dates_order_and_limit() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for identity, project, organization, actor, kind, day in [
            ("a", "p1", "o1", "u1", "view", 1),
            ("b", "p1", "o2", "u1", "edit", 3),
            ("c", "p2", "o1", "u2", "view", 2),
            ("d", "p3", "o3", "u1", "view", 4),
            ("e", "p1", "o1", "u1", "view", 5),
        ]:
            session.add(
                AuditEvent(
                    id=identity,
                    project_id=project,
                    organization_id=organization,
                    actor_user_id=actor,
                    event_type=kind,
                    summary=identity,
                    created_at=datetime(2026, 1, day),
                )
            )
        session.flush()
        repository = RepositoryFactory(session).audit()
        assert [row.id for row in repository.list_for_project("p1")] == ["e", "b", "a"]
        assert [row.id for row in repository.list_for_org("o1", project_ids=["p1"])] == ["e", "b", "c", "a"]
        assert [row.id for row in repository.list_for_org("o1", project_ids=[])] == ["e", "c", "a"]
        filters: AuditFilters = {
            "event_type": "view",
            "actor_user_id": "u1",
            "from_date": datetime(2026, 1, 1),
            "to_date": datetime(2026, 1, 5),
        }
        expected = repository.list_for_project("p1", **filters)
        assert [row.id for row in expected] == ["e", "a"]
        assert audit_ids(session.scalars(repository.project_statement("p1", **filters))) == audit_ids(expected)
        expected_org = repository.list_for_org("o1", project_ids=["p1"], **filters)
        assert audit_ids(session.scalars(repository.org_statement("o1", project_ids=["p1"], **filters))) == audit_ids(
            expected_org
        )
        assert [row.id for row in repository.list_for_project("p1", limit=1)] == ["e"]
        assert repository.list_for_org("o1", project_ids=["p1"], limit=0) == []
        assert [row.id for row in repository.list_for_project("p1", event_type="", actor_user_id="")] == ["e", "b", "a"]
    engine.dispose()
