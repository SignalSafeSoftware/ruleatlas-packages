"""Additional domain repositories for full sqlPhilosophy query-boundary coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    ApiToken,
)


class ApiTokenRepository(BaseRepository[ApiToken, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(ApiToken, session, factory)

    def list_active_for_user(self, user_id: str) -> list[ApiToken]:
        return list(
            self.statement()
            .where(
                ApiToken.user_id == user_id,
                ApiToken.revoked_at.is_(None),
            )
            .order_by(ApiToken.created_at.desc())
            .scalars()
            .all()
        )

    def get_active_for_user_and_id(self, user_id: str, token_id: str) -> ApiToken | None:
        return (
            self.statement()
            .where(
                ApiToken.id == token_id,
                ApiToken.user_id == user_id,
                ApiToken.revoked_at.is_(None),
            )
            .scalars()
            .first()
        )

    def get_active_by_token_hash(self, token_hash: str) -> ApiToken | None:
        return (
            self.statement()
            .where(
                ApiToken.token_hash == token_hash,
                ApiToken.revoked_at.is_(None),
            )
            .scalars()
            .first()
        )

    def get_any(self) -> ApiToken | None:
        return self.statement().limit(1).scalars().first()
