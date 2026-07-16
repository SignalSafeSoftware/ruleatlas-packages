"""Repositories for AI investigation trace persistence."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import AiInvestigationTrace

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory


class AiInvestigationTraceRepository(BaseRepository[AiInvestigationTrace, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(AiInvestigationTrace, session, factory)

    def count_for_analysis(self, project_id: str, analysis_version_id: str) -> int:
        return (
            self.statement()
            .where(
                AiInvestigationTrace.project_id == project_id,
                AiInvestigationTrace.analysis_version_id == analysis_version_id,
            )
            .count()
        )

    def get_for_analysis_and_idempotency_key(
        self, analysis_version_id: str, idempotency_key: str
    ) -> AiInvestigationTrace | None:
        return self.first(
            analysis_version_id=analysis_version_id,
            idempotency_key=idempotency_key,
        )

    def list_for_project(self, project_id: str) -> list[AiInvestigationTrace]:
        return list(
            self.statement()
            .where(AiInvestigationTrace.project_id == project_id)
            .scalars()
            .all()
        )
