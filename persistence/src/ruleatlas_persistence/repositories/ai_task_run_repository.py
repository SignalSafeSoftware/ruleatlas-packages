"""Typed repository for AI enrichment task runs."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import AiTaskRun


class AiTaskRunRepository(BaseRepository[AiTaskRun, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(AiTaskRun, session, factory)

    def get_for_project(self, task_run_id: str, project_id: str) -> AiTaskRun | None:
        """Fetch a task run scoped to a project (IDOR-safe: returns None on cross-project access)."""
        run = self.get_by_id(task_run_id)
        return run if run is not None and run.project_id == project_id else None
