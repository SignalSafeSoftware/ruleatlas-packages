"""Additional domain repositories for full sqlPhilosophy query-boundary coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    PasswordResetToken,
)


class PasswordResetTokenRepository(BaseRepository[PasswordResetToken, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(PasswordResetToken, session, factory)

    def get_unused_by_token_hash(self, token_hash: str) -> PasswordResetToken | None:
        return (
            self.statement()
            .where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used_at.is_(None),
            )
            .scalars()
            .first()
        )
