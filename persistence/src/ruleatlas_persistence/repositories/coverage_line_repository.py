"""Additional domain repositories for full sqlPhilosophy query-boundary coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    CoverageLine,
)


class CoverageLineRepository(BaseRepository[CoverageLine, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(CoverageLine, session, factory)

    def list_for_coverage_file(self, coverage_file_id: str) -> list[CoverageLine]:
        return list(
            self.statement()
            .where(CoverageLine.coverage_file_id == coverage_file_id)
            .scalars()
            .all()
        )
