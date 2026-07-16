"""Additional domain repositories for full sqlPhilosophy query-boundary coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    UserSession,
)


class UserSessionRepository(BaseRepository[UserSession, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(UserSession, session, factory)

    def get_active_by_token_hash(self, token_hash: str) -> UserSession | None:
        return (
            self.statement()
            .where(
                UserSession.token_hash == token_hash,
                UserSession.revoked_at.is_(None),
            )
            .scalars()
            .first()
        )

    def get_by_token_hash(self, token_hash: str) -> UserSession | None:
        return self.first(token_hash=token_hash)

    def list_active_for_user(self, user_id: str) -> list[UserSession]:
        return list(
            self.statement()
            .where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
            )
            .scalars()
            .all()
        )

    def list_active_for_user_ordered(self, user_id: str) -> list[UserSession]:
        return list(
            self.statement()
            .where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
            )
            .order_by(UserSession.created_at.desc())
            .scalars()
            .all()
        )

    def get_active_for_user_and_id(self, user_id: str, session_id: str) -> UserSession | None:
        return (
            self.statement()
            .where(
                UserSession.id == session_id,
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
            )
            .scalars()
            .first()
        )

    def get_active_by_user_and_token_hash(self, user_id: str, token_hash: str) -> UserSession | None:
        return (
            self.statement()
            .where(
                UserSession.user_id == user_id,
                UserSession.token_hash == token_hash,
                UserSession.revoked_at.is_(None),
            )
            .scalars()
            .first()
        )
