"""Additional domain repositories for full sqlPhilosophy query-boundary coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    FileTypeMapping,
)


class FileTypeMappingRepository(BaseRepository[FileTypeMapping, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(FileTypeMapping, session, factory)

    def list_all_ordered(self) -> list[FileTypeMapping]:
        return list(
            self.statement()
            .order_by(FileTypeMapping.pattern.asc(), FileTypeMapping.match_type.asc())
            .scalars()
            .all()
        )

    def list_by_pattern_and_match_type(self) -> list[FileTypeMapping]:
        return list(
            self.statement()
            .order_by(
                FileTypeMapping.pattern.asc(),
                FileTypeMapping.match_type.asc(),
            )
            .scalars()
            .all()
        )
