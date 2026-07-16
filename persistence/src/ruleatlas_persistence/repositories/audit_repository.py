"""Domain repositories for sqlPhilosophy slices 2-8."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, cast

from sqlalchemy import Select, func, or_
from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    AuditEvent,
)

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory


class AuditRepository(BaseRepository[AuditEvent, "RepositoryFactory"]):
    """Infrastructure repository; transaction ownership stays with the caller."""

    @staticmethod
    def build_project_statement(
        session: Session,
        project_id: str,
        *,
        event_type: str | None = None,
        actor_user_id: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> Select[tuple[AuditEvent]]:
        from ruleatlas_persistence.repositories.factory import RepositoryFactory

        stmt = RepositoryFactory(session).audit().statement().where(AuditEvent.project_id == project_id)
        if event_type:
            stmt = stmt.where(AuditEvent.event_type == event_type)
        if actor_user_id:
            stmt = stmt.where(AuditEvent.actor_user_id == actor_user_id)
        if from_date is not None:
            stmt = stmt.where(AuditEvent.created_at >= from_date)
        if to_date is not None:
            stmt = stmt.where(AuditEvent.created_at <= to_date)
        return cast(Select[tuple[AuditEvent]], stmt.order_by(AuditEvent.created_at.desc()).build_select())

    @staticmethod
    def build_org_statement(
        session: Session,
        organization_id: str,
        *,
        project_ids: list[str],
        event_type: str | None = None,
        actor_user_id: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> Select[tuple[AuditEvent]]:
        from ruleatlas_persistence.repositories.factory import RepositoryFactory

        filters = [AuditEvent.organization_id == organization_id]
        if project_ids:
            filters.append(AuditEvent.project_id.in_(project_ids))
        stmt = RepositoryFactory(session).audit().statement().where(or_(*filters))
        if event_type:
            stmt = stmt.where(AuditEvent.event_type == event_type)
        if actor_user_id:
            stmt = stmt.where(AuditEvent.actor_user_id == actor_user_id)
        if from_date is not None:
            stmt = stmt.where(AuditEvent.created_at >= from_date)
        if to_date is not None:
            stmt = stmt.where(AuditEvent.created_at <= to_date)
        return cast(Select[tuple[AuditEvent]], stmt.order_by(AuditEvent.created_at.desc()).build_select())

    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(AuditEvent, session, factory)

    def list_by_event_type(self, event_type: str) -> list[AuditEvent]:
        return list(self.statement().where(AuditEvent.event_type == event_type).scalars().all())

    def get_first_for_project(
        self,
        project_id: str,
        *,
        event_type: str | None = None,
        entity_id: str | None = None,
    ) -> AuditEvent | None:
        stmt = self.statement().where(AuditEvent.project_id == project_id)
        if event_type:
            stmt = stmt.where(AuditEvent.event_type == event_type)
        if entity_id:
            stmt = stmt.where(AuditEvent.entity_id == entity_id)
        return stmt.limit(1).scalars().first()

    def one_for_project(
        self,
        project_id: str,
        *,
        event_type: str | None = None,
    ) -> AuditEvent:
        rows = self.list_for_project(project_id, event_type=event_type)
        if len(rows) != 1:
            raise ValueError(f"Expected exactly one audit event, found {len(rows)}")
        return rows[0]

    def get_first_by_event_type_and_actor(self, event_type: str, actor_user_id: str) -> AuditEvent | None:
        return (
            self.statement()
            .where(
                AuditEvent.event_type == event_type,
                AuditEvent.actor_user_id == actor_user_id,
            )
            .limit(1)
            .scalars()
            .first()
        )

    def list_for_project(
        self,
        project_id: str,
        *,
        event_type: str | None = None,
        actor_user_id: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int | None = None,
    ) -> list[AuditEvent]:
        stmt = self.statement().where(AuditEvent.project_id == project_id)
        if event_type:
            stmt = stmt.where(AuditEvent.event_type == event_type)
        if actor_user_id:
            stmt = stmt.where(AuditEvent.actor_user_id == actor_user_id)
        if from_date is not None:
            stmt = stmt.where(AuditEvent.created_at >= from_date)
        if to_date is not None:
            stmt = stmt.where(AuditEvent.created_at <= to_date)
        stmt = stmt.order_by(AuditEvent.created_at.desc())
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(stmt.scalars().all())

    def count_by_event_type_for_project(self, project_id: str) -> list[tuple[str, int]]:
        rows = (
            self.statement()
            .select_columns(AuditEvent.event_type, func.count().label("count"))
            .where(AuditEvent.project_id == project_id)
            .group_by(AuditEvent.event_type)
            .mappings()
            .all()
        )
        counts: list[tuple[str, int]] = []
        for row in rows:
            event_type = row["event_type"]
            count = row["count"]
            if isinstance(event_type, str) and isinstance(count, int | float | str):
                counts.append((event_type, int(count)))
        return counts

    def count_by_event_type_for_org(self, organization_id: str, project_ids: list[str]) -> list[tuple[str, int]]:
        filters = [AuditEvent.organization_id == organization_id]
        if project_ids:
            filters.append(AuditEvent.project_id.in_(project_ids))
        rows = (
            self.statement()
            .select_columns(AuditEvent.event_type, func.count().label("count"))
            .where(or_(*filters))
            .group_by(AuditEvent.event_type)
            .mappings()
            .all()
        )
        counts: list[tuple[str, int]] = []
        for row in rows:
            event_type = row["event_type"]
            count = row["count"]
            if isinstance(event_type, str) and isinstance(count, int | float | str):
                counts.append((event_type, int(count)))
        return counts

    def project_statement(
        self,
        project_id: str,
        *,
        event_type: str | None = None,
        actor_user_id: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> Select[tuple[AuditEvent]]:
        return self.build_project_statement(
            self._session,
            project_id,
            event_type=event_type,
            actor_user_id=actor_user_id,
            from_date=from_date,
            to_date=to_date,
        )

    def list_for_org(
        self,
        organization_id: str,
        *,
        project_ids: list[str],
        event_type: str | None = None,
        actor_user_id: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int | None = None,
    ) -> list[AuditEvent]:
        filters = [AuditEvent.organization_id == organization_id]
        if project_ids:
            filters.append(AuditEvent.project_id.in_(project_ids))
        stmt = self.statement().where(or_(*filters))
        if event_type:
            stmt = stmt.where(AuditEvent.event_type == event_type)
        if actor_user_id:
            stmt = stmt.where(AuditEvent.actor_user_id == actor_user_id)
        if from_date is not None:
            stmt = stmt.where(AuditEvent.created_at >= from_date)
        if to_date is not None:
            stmt = stmt.where(AuditEvent.created_at <= to_date)
        stmt = stmt.order_by(AuditEvent.created_at.desc())
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(stmt.scalars().all())

    def org_statement(
        self,
        organization_id: str,
        *,
        project_ids: list[str],
        event_type: str | None = None,
        actor_user_id: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> Select[tuple[AuditEvent]]:
        return self.build_org_statement(
            self._session,
            organization_id,
            project_ids=project_ids,
            event_type=event_type,
            actor_user_id=actor_user_id,
            from_date=from_date,
            to_date=to_date,
        )

    def record_event(self, event: AuditEvent) -> AuditEvent:
        self.add(event)
        self._session.flush()
        return event

    def delete_older_than_for_projects(self, project_ids: list[str], cutoff: datetime) -> int:
        if not project_ids:
            return 0
        from sqlalchemy import delete

        stmt = delete(AuditEvent).where(
            AuditEvent.project_id.in_(project_ids),
            AuditEvent.created_at < cutoff,
        )
        result = self._session.execute(stmt)
        return int(getattr(result, "rowcount", 0) or 0)
