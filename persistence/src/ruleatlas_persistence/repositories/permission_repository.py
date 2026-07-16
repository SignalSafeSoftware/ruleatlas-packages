"""Domain repositories for sqlPhilosophy slices 2-8."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    ProjectMembership,
    User,
)

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory


class PermissionRepository(BaseRepository[ProjectMembership, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(ProjectMembership, session, factory)

    def get_project_membership(self, user_id: str, project_id: str) -> ProjectMembership | None:
        return (
            self.statement()
            .where(
                ProjectMembership.project_id == project_id,
                ProjectMembership.user_id == user_id,
            )
            .scalars()
            .first()
        )

    def list_project_memberships(self, project_id: str) -> list[ProjectMembership]:
        return list(self.statement().where(ProjectMembership.project_id == project_id).scalars().all())

    def list_members_with_user(self, project_id: str) -> list[tuple[User, str]]:
        factory = cast("RepositoryFactory", self._factory)
        rows = self._session.execute(
            factory.users()
            .statement()
            .select_columns(User, ProjectMembership.role)
            .join(ProjectMembership, ProjectMembership.user_id == User.id)
            .where(ProjectMembership.project_id == project_id)
            .order_by(User.display_name)
            .build_select()
        ).all()
        return [(cast(User, row[0]), cast(str, row[1])) for row in rows]

    def list_project_ids_for_user(self, user_id: str) -> list[str]:
        return [
            str(project_id)
            for project_id in (
            self.statement()
            .select_columns(ProjectMembership.project_id)
            .where(ProjectMembership.user_id == user_id)
            .scalars()
            .all()
            )
        ]
