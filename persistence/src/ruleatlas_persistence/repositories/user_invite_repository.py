"""Additional domain repositories for full sqlPhilosophy query-boundary coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    UserInvite,
)


class UserInviteRepository(BaseRepository[UserInvite, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(UserInvite, session, factory)

    def get_by_token_hash(self, token_hash: str) -> UserInvite | None:
        return self.first(token_hash=token_hash)

    def list_pending_for_organization(self, organization_id: str) -> list[UserInvite]:
        return list(
            self.statement()
            .where(
                UserInvite.organization_id == organization_id,
                UserInvite.accepted_at.is_(None),
            )
            .order_by(UserInvite.created_at.desc())
            .scalars()
            .all()
        )

    def get_for_organization(self, invite_id: str, organization_id: str) -> UserInvite | None:
        invite = self.get_by_id(invite_id)
        if invite is None or invite.organization_id != organization_id:
            return None
        return invite
