"""Additional domain repositories for full sqlPhilosophy query-boundary coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import Select, asc, desc, func
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory


class PaginationRepository:
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        self._session = session

    def count_from_statement(self, stmt: Select) -> int:
        count_stmt = stmt.with_only_columns(func.count(), maintain_column_froms=True).order_by(None)
        return int(self._session.scalar(count_stmt) or 0)

    def paginate_scalars(
        self,
        stmt: Select,
        *,
        page: int = 1,
        page_size: int = 50,
        sort_column: Any=None,
        sort_dir: str = "desc",
    ) -> tuple[list, int]:
        if sort_column is not None:
            order = desc(sort_column) if sort_dir == "desc" else asc(sort_column)
            stmt = stmt.order_by(order)
        total = self.count_from_statement(stmt)
        offset = max(0, (page - 1) * page_size)
        rows = list(self._session.scalars(stmt.offset(offset).limit(page_size)).all())
        return rows, total
