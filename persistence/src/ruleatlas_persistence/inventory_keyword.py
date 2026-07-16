"""Shared inventory keyword matching for discovery paged query."""

from __future__ import annotations

from typing import Any

from sqlalchemy import String, cast, func, or_

from ruleatlas_persistence.models import SourceFile

INVENTORY_KEYWORD_FIELD_LABEL = "path, classification, language, source_type"


def inventory_keyword_sql_clause(keyword: str) -> Any:
    trimmed = keyword.strip()
    if not trimmed:
        return None
    pattern = f"%{trimmed}%"
    return or_(
        SourceFile.path.ilike(pattern),
        cast(SourceFile.classification, String).ilike(pattern),
        func.coalesce(SourceFile.language, "").ilike(pattern),
        cast(SourceFile.source_type, String).ilike(pattern),
    )


def inventory_manifest_row_matches_keyword(row: dict, keyword: str | None) -> bool:
    if not keyword or not keyword.strip():
        return True
    query = keyword.strip().lower()
    haystack = [
        str(row.get("path") or ""),
        str(row.get("classification") or ""),
        str(row.get("language") or ""),
        str(row.get("source_type") or ""),
    ]
    return any(query in value.lower() for value in haystack if value)
