"""Repositories for external OAuth identity links."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import ExternalIdentity

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory


class ExternalIdentityRepository(BaseRepository[ExternalIdentity, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(ExternalIdentity, session, factory)

    def get_by_provider_subject(self, provider: str, provider_user_id: str) -> ExternalIdentity | None:
        return self.first(provider=provider, provider_user_id=provider_user_id)

    def get_for_user(self, provider: str, user_id: str) -> ExternalIdentity | None:
        return self.first(provider=provider, user_id=user_id)
