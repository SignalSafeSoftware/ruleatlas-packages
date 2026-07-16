"""Additional domain repositories for full sqlPhilosophy query-boundary coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    User,
)


class UserRepository(BaseRepository[User, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(User, session, factory)

    def get_by_email(self, email: str) -> User | None:
        return self.first(email=email)

    def get_active_by_email(self, email: str) -> User | None:
        return self.statement().where(User.email == email, User.is_active.is_(True)).scalars().first()
