"""SQL and in-memory filter helpers for paged discovery inventory queries."""

from __future__ import annotations

from typing import Any

from ruleatlas_contracts.enums import SourceFileClassification
from sqlalchemy import asc, desc, func, or_
from sqlphilosophy.sync.query import StatementQueryBuilder

from ruleatlas_persistence.inventory_keyword import (
    inventory_keyword_sql_clause,
    inventory_manifest_row_matches_keyword,
)
from ruleatlas_persistence.models import SourceFile


def _normalize_extension(extension: str | None) -> str | None:
    if not extension:
        return None
    ext = extension.strip()
    if not ext or ext == "(none)":
        return None
    if not ext.startswith("."):
        return f".{ext}"
    return ext


class DiscoveryInventoryQueryBuilder:
    @staticmethod
    def _apply_extension_filter(
        stmt: StatementQueryBuilder[SourceFile], extension: str | None
    ) -> StatementQueryBuilder[SourceFile]:
        ext = _normalize_extension(extension)
        if not ext:
            return stmt
        return stmt.where(SourceFile.path.like(f"%{ext}"))

    @staticmethod
    def _apply_scope_filter(stmt: StatementQueryBuilder[SourceFile], scope: str) -> StatementQueryBuilder[SourceFile]:
        if scope == "included":
            return stmt.where(SourceFile.classification != SourceFileClassification.GENERATED_VENDOR)
        if scope == "excluded":
            return stmt.where(SourceFile.classification == SourceFileClassification.GENERATED_VENDOR)
        return stmt

    @staticmethod
    def _apply_path_prefix_filter(
        stmt: StatementQueryBuilder[SourceFile], path_prefix: str | None
    ) -> StatementQueryBuilder[SourceFile]:
        if not path_prefix:
            return stmt
        prefix = path_prefix.strip().replace("\\", "/")
        if not prefix:
            return stmt
        return stmt.where(
            or_(
                SourceFile.path.startswith(prefix),
                SourceFile.path.like(f"%/{prefix.lstrip('/')}%"),
            )
        )

    @staticmethod
    def apply_filters(
        stmt: StatementQueryBuilder[SourceFile],
        *,
        classification: str | None,
        language: str | None,
        extension: str | None,
        scope: str,
        path_prefix: str | None,
        q: str | None,
    ) -> StatementQueryBuilder[SourceFile]:
        if classification:
            stmt = stmt.where(SourceFile.classification == classification)
        if language:
            stmt = stmt.where(func.lower(SourceFile.language) == language.strip().lower())
        stmt = DiscoveryInventoryQueryBuilder._apply_extension_filter(stmt, extension)
        stmt = DiscoveryInventoryQueryBuilder._apply_scope_filter(stmt, scope)
        stmt = DiscoveryInventoryQueryBuilder._apply_path_prefix_filter(stmt, path_prefix)
        if q:
            clause = inventory_keyword_sql_clause(q)
            if clause is not None:
                stmt = stmt.where(clause)
        return stmt

    @staticmethod
    def sort_column(sort: str) -> Any:
        if sort in {"path", "display_path"}:
            return SourceFile.path
        if sort == "size_bytes":
            return SourceFile.size_bytes
        if sort == "line_count":
            return SourceFile.line_count
        if sort == "code_line_count":
            return SourceFile.code_line_count
        if sort == "classification":
            return SourceFile.classification
        return SourceFile.language

    @staticmethod
    def order_clause(sort: str, sort_dir: str) -> Any:
        direction = asc if sort_dir == "asc" else desc
        return direction(DiscoveryInventoryQueryBuilder.sort_column(sort))

    @staticmethod
    def _manifest_extension_matches(path: str, extension: str | None) -> bool:
        ext = _normalize_extension(extension)
        if not ext:
            return True
        return path.lower().endswith(ext.lower())

    @staticmethod
    def _manifest_scope_matches(included: bool, scope: str) -> bool:
        if scope == "included":
            return included
        if scope == "excluded":
            return not included
        return True

    @staticmethod
    def _manifest_path_prefix_matches(path: str, path_prefix: str | None) -> bool:
        if not path_prefix:
            return True
        prefix = path_prefix.strip().replace("\\", "/")
        if not prefix:
            return True
        return prefix in path or path.startswith(prefix)

    @staticmethod
    def manifest_row_matches_filters(
        row: dict,
        *,
        classification: str | None,
        language: str | None,
        extension: str | None,
        scope: str,
        path_prefix: str | None,
        q: str | None,
    ) -> bool:
        path = str(row.get("path") or "")
        cls = str(row.get("classification") or "unknown")
        included = cls != SourceFileClassification.GENERATED_VENDOR

        if classification and cls != classification:
            return False
        if language and str(row.get("language") or "").lower() != language.strip().lower():
            return False
        if not DiscoveryInventoryQueryBuilder._manifest_extension_matches(path, extension):
            return False
        if not DiscoveryInventoryQueryBuilder._manifest_scope_matches(included, scope):
            return False
        if not DiscoveryInventoryQueryBuilder._manifest_path_prefix_matches(path, path_prefix):
            return False
        return inventory_manifest_row_matches_keyword(row, q)

    @staticmethod
    def manifest_sort_key(row: dict, sort: str) -> tuple:
        path = str(row.get("path") or "")
        if sort in {"path", "display_path"}:
            return (path, "")
        if sort == "size_bytes":
            return (int(row.get("size_bytes") or 0), path)
        if sort == "line_count":
            return (int(row.get("line_count") or 0), path)
        if sort == "code_line_count":
            return (int(row.get("code_line_count") or 0), path)
        if sort == "classification":
            return (str(row.get("classification") or ""), path)
        return (str(row.get("language") or ""), path)
