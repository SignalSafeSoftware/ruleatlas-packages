"""Additional domain repositories for full sqlPhilosophy query-boundary coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    TestCase,
)


class TestCaseRepository(BaseRepository[TestCase, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(TestCase, session, factory)

    def ids_for_project(self, project_id: str) -> list[str]:
        return [
            str(test_case_id)
            for test_case_id in (
            self.statement().select_columns(TestCase.id).where(TestCase.project_id == project_id).scalars().all()
            )
        ]
