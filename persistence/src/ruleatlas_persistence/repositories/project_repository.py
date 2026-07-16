from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlphilosophy.sorting import ListQuery
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    Project,
)

_ACTIVE_ANALYSIS_VERSION_SETTINGS_KEY = "active_analysis_version_id"


class ProjectRepository(BaseRepository[Project, "RepositoryFactory"]):
    """Infrastructure repository; transaction ownership stays with the caller."""

    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(Project, session, factory)

    def list_for_organization(self, organization_id: str, query: ListQuery | None = None) -> list[Project]:
        stmt = self.statement().where(Project.organization_id == organization_id).where(Project.archived_at.is_(None))
        if query is None:
            return list(stmt.order_by(Project.created_at.desc()).scalars().all())
        return list(
            stmt.order_by(Project.created_at.desc())
            .offset(query.offset)
            .limit(query.limit)
            .scalars()
            .all()
        )

    def list_active_for_org_by_slug(self, organization_id: str) -> list[Project]:
        return list(
            self.statement()
            .where(Project.organization_id == organization_id, Project.archived_at.is_(None))
            .order_by(Project.slug.asc())
            .scalars()
            .all()
        )

    def list_active_unarchived(self) -> list[Project]:
        return list(
            self.statement().where(Project.archived_at.is_(None)).order_by(Project.created_at.desc()).scalars().all()
        )

    def list_active_for_ids(self, project_ids: list[str]) -> list[Project]:
        if not project_ids:
            return []
        return list(
            self.statement()
            .where(Project.id.in_(project_ids), Project.archived_at.is_(None))
            .order_by(Project.created_at.desc())
            .scalars()
            .all()
        )

    def list_by_ids(self, project_ids: list[str]) -> list[Project]:
        if not project_ids:
            return []
        return list(self.statement().where(Project.id.in_(project_ids)).scalars().all())

    def list_ids_for_organization(self, organization_id: str) -> list[str]:
        return cast(
            list[str],
            self.statement()
            .select_columns(Project.id)
            .where(Project.organization_id == organization_id)
            .scalars()
            .all(),
        )

    def get_active_by_org_and_slug(self, organization_id: str, slug: str) -> Project | None:
        return (
            self.statement()
            .where(
                Project.organization_id == organization_id,
                Project.slug == slug,
                Project.archived_at.is_(None),
            )
            .scalars()
            .first()
        )

    def list_all(self) -> list[Project]:
        return list(self.statement().scalars().all())

    def get_by_slug(self, slug: str) -> Project | None:
        return self.first(slug=slug)

    def get_unarchived_by_id(self, project_id: str) -> Project | None:
        project = self.get_by_id(project_id)
        if project is None or project.archived_at is not None:
            return None
        return project

    def find_active_by_repository_name(self, repo_full_name: str) -> list[Project]:
        needle = repo_full_name.lower()
        return list(
            self.statement()
            .where(
                Project.archived_at.is_(None),
                or_(
                    Project.repository_url.ilike(f"%/{needle}%"),
                    Project.repository_url.ilike(f"%{needle}%"),
                ),
            )
            .scalars()
            .all()
        )

    def set_active_analysis_version_id(self, project_id: str, version_id: str) -> None:
        # RA-01-006: the active-version pointer is a typed FK column (was settings_json). Clear the legacy
        # settings key on write so stale JSON values don't linger.
        project = self.get_by_id(project_id)
        if project is None:
            return
        project.active_analysis_version_id = version_id
        if project.settings_json and _ACTIVE_ANALYSIS_VERSION_SETTINGS_KEY in project.settings_json:
            settings = dict(project.settings_json)
            settings.pop(_ACTIVE_ANALYSIS_VERSION_SETTINGS_KEY, None)
            project.settings_json = settings
        self.add(project)
