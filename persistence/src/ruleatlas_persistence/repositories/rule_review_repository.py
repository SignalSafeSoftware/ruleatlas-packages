"""Additional domain repositories for full sqlPhilosophy query-boundary coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    RuleReview,
)


class RuleReviewRepository(BaseRepository[RuleReview, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(RuleReview, session, factory)

    def list_for_rule(self, rule_id: str) -> list[RuleReview]:
        return list(
            self.statement().where(RuleReview.rule_id == rule_id).order_by(RuleReview.created_at.desc()).scalars().all()
        )
