"""Additional domain repositories for full sqlPhilosophy query-boundary coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    SourceSymbol,
)


class SourceSymbolRepository(BaseRepository[SourceSymbol, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(SourceSymbol, session, factory)

    def list_containing_line(self, source_file_id: str, line_number: int) -> list[SourceSymbol]:
        return list(
            self.statement()
            .where(
                SourceSymbol.source_file_id == source_file_id,
                SourceSymbol.start_line <= line_number,
                SourceSymbol.end_line >= line_number,
            )
            .scalars()
            .all()
        )
