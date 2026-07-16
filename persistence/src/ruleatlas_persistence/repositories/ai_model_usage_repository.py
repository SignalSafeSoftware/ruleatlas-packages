"""Additional domain repositories for full sqlPhilosophy query-boundary coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from datetime import datetime

from ruleatlas_contracts.enums import (
    AiProviderMode,
)
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    AiModelUsage,
)


class AiModelUsageRepository(BaseRepository[AiModelUsage, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(AiModelUsage, session, factory)

    def sum_remote_spend_for_projects(self, project_ids: list[str], *, since: datetime) -> float:
        if not project_ids:
            return 0.0
        total = (
            self.statement()
            .select_columns(func.coalesce(func.sum(AiModelUsage.total_cost_usd), 0.0))
            .where(
                AiModelUsage.project_id.in_(project_ids),
                AiModelUsage.provider_mode == AiProviderMode.OPENAI_REMOTE.value,
                AiModelUsage.created_at >= since,
            )
            .scalar()
        )
        return float(total or 0.0)

    def list_for_projects(self, project_ids: list[str], *, limit: int = 50) -> list[AiModelUsage]:
        if not project_ids:
            return []
        return list(
            self.statement()
            .where(AiModelUsage.project_id.in_(project_ids))
            .order_by(AiModelUsage.created_at.desc())
            .limit(limit)
            .scalars()
            .all()
        )
