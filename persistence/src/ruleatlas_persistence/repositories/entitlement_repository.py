"""Domain repositories for sqlPhilosophy slices 2-8."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    OrganizationMembership,
)


class EntitlementRepository(BaseRepository[OrganizationMembership, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(OrganizationMembership, session, factory)

    def get_org_membership(self, user_id: str, organization_id: str) -> OrganizationMembership | None:
        return (
            self.statement()
            .where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.user_id == user_id,
            )
            .scalars()
            .first()
        )

    def list_org_memberships_for_user(self, user_id: str) -> list[OrganizationMembership]:
        return list(self.statement().where(OrganizationMembership.user_id == user_id).scalars().all())
