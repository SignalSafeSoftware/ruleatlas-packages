"""Additional domain repositories for full sqlPhilosophy query-boundary coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    Organization,
    OrganizationMembership,
    User,
)

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory


class OrganizationRepository(BaseRepository[Organization, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(Organization, session, factory)

    def list_all(self) -> list[Organization]:
        return list(self.statement().scalars().all())

    def get_first(self) -> Organization | None:
        return self.statement().limit(1).scalars().first()

    def list_with_role_for_user(self, user_id: str) -> list[tuple[Organization, str]]:
        return cast(
            list[tuple[Organization, str]],
            self._session.execute(
                self.statement()
                .select_columns(Organization, OrganizationMembership.role)
                .join(
                    OrganizationMembership,
                    OrganizationMembership.organization_id == Organization.id,
                )
                .where(OrganizationMembership.user_id == user_id)
                .order_by(Organization.name.asc())
                .build_select()
            ).tuples().all(),
        )

    def list_members_with_role(self, organization_id: str) -> list[tuple[User, str]]:
        return cast(
            list[tuple[User, str]],
            self._session.execute(
                self.factory.users()
                .statement()
                .select_columns(User, OrganizationMembership.role)
                .join(
                    OrganizationMembership,
                    OrganizationMembership.user_id == User.id,
                )
                .where(OrganizationMembership.organization_id == organization_id)
                .order_by(User.display_name.asc())
                .build_select()
            ).tuples().all(),
        )

    def get_by_slug(self, slug: str) -> Organization | None:
        return self.first(slug=slug)

    def get_by_slug_except(self, slug: str, except_org_id: str) -> Organization | None:
        return (
            self.statement()
            .where(
                Organization.slug == slug,
                Organization.id != except_org_id,
            )
            .scalars()
            .first()
        )

    def list_all_ids(self) -> list[str]:
        return cast(list[str], self.statement().select_columns(Organization.id).scalars().all())

    def count_memberships(self, organization_id: str) -> int:
        return (
            self.factory.repository(OrganizationMembership)
            .statement()
            .where(OrganizationMembership.organization_id == organization_id)
            .count()
        )

    def list_users_by_emails(self, emails: set[str]) -> list[User]:
        if not emails:
            return []
        return list(
            self.factory.users()
            .statement()
            .where(User.email.in_(emails))
            .scalars()
            .all()
        )
