"""Repositories for runtime evidence events and rule links."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import RuntimeEvent, RuntimeEventLink

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory


class RuntimeEventRepository(BaseRepository[RuntimeEvent, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(RuntimeEvent, session, factory)

    def list_for_project(
        self,
        project_id: str,
        *,
        analysis_version_id: str | None = None,
        limit: int = 100,
    ) -> list[RuntimeEvent]:
        stmt = self.statement().where(RuntimeEvent.project_id == project_id)
        if analysis_version_id:
            stmt = stmt.where(
                or_(
                    RuntimeEvent.analysis_version_id == analysis_version_id,
                    RuntimeEvent.analysis_version_id.is_(None),
                )
            )
        return list(
            stmt.order_by(RuntimeEvent.created_at.desc())
            .limit(min(limit, 500))
            .scalars()
            .all()
        )

    def get_by_project_and_content_hash(self, project_id: str, content_hash: str) -> RuntimeEvent | None:
        return (
            self.statement()
            .where(
                RuntimeEvent.project_id == project_id,
                RuntimeEvent.content_hash == content_hash,
            )
            .scalars()
            .first()
        )

    def list_for_linking(
        self,
        project_id: str,
        *,
        analysis_version_id: str | None = None,
        limit: int = 500,
    ) -> list[RuntimeEvent]:
        stmt = self.statement().where(RuntimeEvent.project_id == project_id)
        if analysis_version_id:
            stmt = stmt.where(
                or_(
                    RuntimeEvent.analysis_version_id == analysis_version_id,
                    RuntimeEvent.analysis_version_id.is_(None),
                )
            )
        return list(stmt.limit(limit).scalars().all())

    def count_for_project(self, project_id: str) -> int:
        return self.statement().where(RuntimeEvent.project_id == project_id).count()

    def get_for_project(self, event_id: str, project_id: str) -> RuntimeEvent | None:
        return (
            self.statement()
            .where(RuntimeEvent.id == event_id, RuntimeEvent.project_id == project_id)
            .scalars()
            .first()
        )


class RuntimeEventLinkRepository(BaseRepository[RuntimeEventLink, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(RuntimeEventLink, session, factory)

    def list_for_rule_limited(self, rule_id: str, *, limit: int) -> list[RuntimeEventLink]:
        return list(
            self.statement()
            .where(RuntimeEventLink.rule_id == rule_id)
            .limit(limit)
            .scalars()
            .all()
        )

    def list_for_event(self, runtime_event_id: str) -> list[RuntimeEventLink]:
        return list(
            self.statement()
            .where(RuntimeEventLink.runtime_event_id == runtime_event_id)
            .scalars()
            .all()
        )
