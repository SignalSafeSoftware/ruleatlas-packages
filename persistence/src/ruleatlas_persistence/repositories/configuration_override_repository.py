"""Repositories for configuration override history."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import ConfigurationOverride, ConfigurationOverrideHistory

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory


class ConfigurationOverrideRepository(BaseRepository[ConfigurationOverride, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(ConfigurationOverride, session, factory)

    def list_for_key(self, key: str) -> list[ConfigurationOverride]:
        return list(self.statement().where(ConfigurationOverride.key == key).scalars().all())

    def get_for_scope(self, key: str, scope: str, scope_id: str | None) -> ConfigurationOverride | None:
        return (
            self.statement()
            .where(
                ConfigurationOverride.key == key,
                ConfigurationOverride.scope == scope,
                ConfigurationOverride.scope_id == scope_id,
            )
            .scalars()
            .first()
        )

    def count_for_demo_scopes(self, organization_id: str, project_ids: list[str]) -> int:
        scope_predicate = (
            (ConfigurationOverride.scope == "organization")
            & (ConfigurationOverride.scope_id == organization_id)
        ) | (
            (ConfigurationOverride.scope == "project")
            & ConfigurationOverride.scope_id.in_(project_ids)
        )
        return self.statement().where(scope_predicate).count()


class ConfigurationOverrideHistoryRepository(
    BaseRepository[ConfigurationOverrideHistory, "RepositoryFactory"]
):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(ConfigurationOverrideHistory, session, factory)

    def list_recent(
        self,
        *,
        key: str | None = None,
        scope: str | None = None,
        scope_id: str | None = None,
        limit: int = 100,
    ) -> list[ConfigurationOverrideHistory]:
        stmt = self.statement().order_by(ConfigurationOverrideHistory.created_at.desc())
        if key:
            stmt = stmt.where(ConfigurationOverrideHistory.key == key)
        if scope:
            stmt = stmt.where(ConfigurationOverrideHistory.scope == scope)
        if scope_id is not None:
            stmt = stmt.where(ConfigurationOverrideHistory.scope_id == scope_id)
        return list(stmt.limit(limit).scalars().all())

    def count_for_demo_seed(self, organization_id: str, seed_version: str) -> int:
        return (
            self.statement()
            .where(
                ConfigurationOverrideHistory.scope == "organization",
                ConfigurationOverrideHistory.scope_id == organization_id,
                ConfigurationOverrideHistory.reason.ilike(f"%{seed_version}%"),
            )
            .count()
        )

    def count_for_reason(self, reason_pattern: str) -> int:
        return self.statement().where(ConfigurationOverrideHistory.reason.ilike(reason_pattern)).count()
