"""Domain repositories for sqlPhilosophy slices 2-8."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from ruleatlas_contracts.enums import SourceFileClassification
from sqlalchemy import asc, or_
from sqlalchemy.orm import Session
from sqlphilosophy.sync.query import StatementQueryBuilder
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    SourceFile,
)
from ruleatlas_persistence.repositories.discovery_inventory_query_builder import (
    DiscoveryInventoryQueryBuilder,
)


class SourceFileRepository(BaseRepository[SourceFile, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(SourceFile, session, factory)

    def count_for_project(self, project_id: str) -> int:
        return self.statement().where(SourceFile.project_id == project_id).count()

    def count_for_location(self, location_id: str) -> int:
        return self.statement().where(SourceFile.source_location_id == location_id).count()

    def ids_for_project(self, project_id: str) -> list[str]:
        return cast(
            list[str],
            self.statement().select_columns(SourceFile.id).where(SourceFile.project_id == project_id).scalars().all()
        )

    def count_for_scan(self, project_id: str, scan_run_id: str) -> int:
        return (
            self.statement()
            .where(
                SourceFile.project_id == project_id,
                SourceFile.scan_run_id == scan_run_id,
            )
            .count()
        )

    def list_for_scan(self, project_id: str, scan_run_id: str, *, limit: int | None = None) -> list[SourceFile]:
        stmt = self.statement().where(
            SourceFile.project_id == project_id,
            SourceFile.scan_run_id == scan_run_id,
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(stmt.scalars().all())

    def list_for_scan_ordered_by_path(
        self, project_id: str, scan_run_id: str, *, limit: int | None = None
    ) -> list[SourceFile]:
        stmt = (
            self.statement()
            .where(
                SourceFile.project_id == project_id,
                SourceFile.scan_run_id == scan_run_id,
            )
            .order_by(SourceFile.path.asc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(stmt.scalars().all())

    def list_eligible_for_extraction_batch(
        self,
        project_id: str,
        scan_run_id: str,
        *,
        eligible_classifications: list[SourceFileClassification] | frozenset[SourceFileClassification],
        after_path: str | None = None,
        limit: int,
    ) -> list[SourceFile]:
        """Return the next path-ordered batch of extraction-eligible source files.

        Uses keyset pagination on ``path`` so every eligible file is eventually
        attempted — there is no global file-count cap.
        """
        stmt = (
            self.statement()
            .where(
                SourceFile.project_id == project_id,
                SourceFile.scan_run_id == scan_run_id,
                SourceFile.classification.in_(list(eligible_classifications)),
            )
            .order_by(SourceFile.path.asc())
            .limit(limit)
        )
        if after_path is not None:
            stmt = stmt.where(SourceFile.path > after_path)
        return list(stmt.scalars().all())

    def count_eligible_for_extraction(
        self,
        project_id: str,
        scan_run_id: str,
        *,
        eligible_classifications: list[SourceFileClassification] | frozenset[SourceFileClassification],
    ) -> int:
        return (
            self.statement()
            .where(
                SourceFile.project_id == project_id,
                SourceFile.scan_run_id == scan_run_id,
                SourceFile.classification.in_(list(eligible_classifications)),
            )
            .count()
        )

    def list_for_project(self, project_id: str, *, limit: int | None = None) -> list[SourceFile]:
        stmt = self.statement().where(SourceFile.project_id == project_id)
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(stmt.scalars().all())

    def list_matching_language_or_suffix(
        self, *, language_key: str, path_suffix: str, limit: int = 25
    ) -> list[SourceFile]:
        return list(
            self.statement()
            .where(
                or_(
                    SourceFile.language == language_key,
                    SourceFile.path.endswith(path_suffix),
                )
            )
            .limit(limit)
            .scalars()
            .all()
        )

    def clear_override_references(self, project_id: str, override_id: str) -> None:
        from sqlalchemy import update

        self._session.execute(
            update(SourceFile)
            .where(
                SourceFile.project_id == project_id,
                SourceFile.classification_override_id == override_id,
            )
            .values(classification_override_id=None, file_kind_override=None)
        )

    def list_paths_for_project(self, project_id: str) -> list[str]:
        return cast(
            list[str],
            self.statement().select_columns(SourceFile.path).where(SourceFile.project_id == project_id).scalars().all()
        )

    def get_by_project_and_path(self, project_id: str, path: str) -> SourceFile | None:
        return (
            self.statement()
            .where(
                SourceFile.project_id == project_id,
                SourceFile.path == path,
            )
            .scalars()
            .first()
        )

    def get_first_by_path_prefix(self, project_id: str, prefix: str) -> SourceFile | None:
        return (
            self.statement()
            .where(
                SourceFile.project_id == project_id,
                SourceFile.path.like(f"{prefix}%"),
            )
            .limit(1)
            .scalars()
            .first()
        )

    def get_first_by_path_contains(self, project_id: str, substring: str) -> SourceFile | None:
        return (
            self.statement()
            .where(
                SourceFile.project_id == project_id,
                SourceFile.path.like(f"%{substring}%"),
            )
            .limit(1)
            .scalars()
            .first()
        )

    def get_first_by_path_suffix(self, project_id: str, suffix: str) -> SourceFile | None:
        return (
            self.statement()
            .where(
                SourceFile.project_id == project_id,
                SourceFile.path.like(f"%{suffix}"),
            )
            .limit(1)
            .scalars()
            .first()
        )

    def find_by_path_suffix(self, project_id: str, path_suffix: str) -> SourceFile | None:
        return (
            self.statement()
            .where(
                SourceFile.project_id == project_id,
                SourceFile.path.endswith(path_suffix),
            )
            .limit(1)
            .scalars()
            .first()
        )

    def detach_from_location(self, location_id: str) -> int:
        """Clear source_location_id on inventory rows without deleting file lineage."""
        from sqlalchemy import update

        result = self._session.execute(
            update(SourceFile)
            .where(SourceFile.source_location_id == location_id)
            .values(source_location_id=None)
        )
        return cast(int, getattr(result, "rowcount", 0) or 0)

    def delete_for_location(self, location_id: str) -> int:
        """Deprecated hard-delete path — prefer detach_from_location to preserve lineage."""
        return self.detach_from_location(location_id)

    def aggregate_language_and_classification_for_scan(
        self, project_id: str, scan_run_id: str
    ) -> tuple[dict[str, int], dict[str, int]]:
        from ruleatlas_contracts.enum_utils import enum_value

        by_language: dict[str, int] = {}
        by_classification: dict[str, int] = {}
        for row in self.list_for_scan(project_id, scan_run_id):
            lang = row.language or "unknown"
            by_language[lang] = by_language.get(lang, 0) + 1
            cls = enum_value(row.classification, "unknown")
            by_classification[cls] = by_classification.get(cls, 0) + 1
        return by_language, by_classification

    def map_path_to_row_for_project(self, project_id: str) -> dict[str, SourceFile]:
        """Return path -> SourceFile for the project (RA-07-004: batch-load for O(1) upsert lookups)."""
        return {row.path: row for row in self.list_for_project(project_id)}

    def map_path_to_content_hash_for_project(self, project_id: str) -> dict[str, str]:
        rows = (
            self.statement()
            .select_columns(SourceFile.path, SourceFile.content_hash)
            .where(SourceFile.project_id == project_id)
            .mappings()
            .all()
        )
        return {
            str(row["path"]): str(row["content_hash"])
            for row in rows
            if row["path"] and row["content_hash"]
        }

    def path_hash_map_for_scan(self, scan_run_id: str) -> dict[str, str]:
        rows = (
            self.statement()
            .select_columns(SourceFile.path, SourceFile.content_hash)
            .where(SourceFile.scan_run_id == scan_run_id)
            .mappings()
            .all()
        )
        return {
            str(row["path"]): str(row["content_hash"])
            for row in rows
            if row["path"] and row["content_hash"]
        }

    def inventory_statement(
        self, project_id: str, *, scan_run_id: str | None = None
    ) -> StatementQueryBuilder[SourceFile]:
        stmt = self.statement().where(SourceFile.project_id == project_id)
        if scan_run_id is not None:
            stmt = stmt.where(SourceFile.scan_run_id == scan_run_id)
        return stmt

    def list_for_scan_run(self, scan_run_id: str) -> list[SourceFile]:
        return list(self.statement().where(SourceFile.scan_run_id == scan_run_id).scalars().all())

    def count_inventory_filtered(self, stmt: StatementQueryBuilder[SourceFile]) -> int:
        return stmt.count()

    def list_inventory_page(
        self,
        stmt: StatementQueryBuilder[SourceFile],
        *,
        order_by: Any,
        offset: int,
        limit: int,
        order_by_secondary: Any=None,
    ) -> list[SourceFile]:
        ordering = (order_by, order_by_secondary) if order_by_secondary is not None else (order_by,)
        return list(stmt.order_by(*ordering).offset(offset).limit(limit).scalars().all())

    def page_for_discovery(
        self,
        project_id: str,
        *,
        scan_run_id: str | None,
        classification: str | None,
        language: str | None,
        extension: str | None,
        scope: str,
        path_prefix: str | None,
        q: str | None,
        sort: str,
        sort_dir: str,
        page: int,
        page_size: int,
    ) -> tuple[list[SourceFile], int, int]:
        stmt = self.inventory_statement(project_id, scan_run_id=scan_run_id)
        total_inventory_count = stmt.count()
        filtered_stmt = DiscoveryInventoryQueryBuilder.apply_filters(
            stmt,
            classification=classification,
            language=language,
            extension=extension,
            scope=scope,
            path_prefix=path_prefix,
            q=q,
        )
        filtered_count = filtered_stmt.count()
        offset = (page - 1) * page_size
        page_rows = self.list_inventory_page(
            filtered_stmt,
            order_by=DiscoveryInventoryQueryBuilder.order_clause(sort, sort_dir),
            offset=offset,
            limit=page_size,
            order_by_secondary=asc(SourceFile.path),
        )
        return page_rows, total_inventory_count, filtered_count
