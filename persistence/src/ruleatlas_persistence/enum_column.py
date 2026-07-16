"""SQLAlchemy Enum column helpers for lowercase StrEnum persistence."""

from __future__ import annotations

from collections.abc import Iterable
from enum import Enum
from typing import Any, cast

from sqlalchemy import inspect, text


def _iter_enum_members[E: Enum](enum_cls: type[E]) -> Iterable[E]:
    return cast(Iterable[E], iter(cast(Any, enum_cls)))


def str_enum_values_callable[E: Enum](enum_cls: type[E]) -> list[str]:
    """Return enum member values for SQLAlchemy Enum (not member names)."""
    return [member.value for member in _iter_enum_members(enum_cls)]


STR_ENUM_COLUMN_KW = {
    "native_enum": False,
    "length": 64,
    "values_callable": str_enum_values_callable,
    # RA-01-002: a DB-level CHECK constraint is desirable but cannot be enabled here without breaking the
    # legacy uppercase->lowercase backfill (which must temporarily hold out-of-vocab values). Enum-value
    # integrity is guarded by application code + test_enum_column_membership.py until a data-migration +
    # Alembic CHECK migration is scheduled against the DB-backed suites.
}

LEGACY_ENUM_VALUE_MAP: dict[tuple[str, str], dict[str, str]] = {
    ("source_locations", "source_type"): {
        "TEST": "tests",
        "BDD": "bdd_specs",
        "DOCUMENTATION": "docs",
        "DESIGN_DOC": "design_docs",
        "TICKET": "tickets",
        "DATABASE_MIGRATION": "unknown",
        "CONFIGURATION": "unknown",
        "INFRASTRUCTURE": "unknown",
        "GENERATED": "unknown",
        "VENDOR": "unknown",
        "STATIC_ASSET": "unknown",
        "OTHER": "unknown",
    },
    ("source_files", "source_type"): {
        "TEST": "tests",
        "BDD": "bdd_specs",
        "DOCUMENTATION": "docs",
        "DESIGN_DOC": "design_docs",
        "TICKET": "tickets",
        "DATABASE_MIGRATION": "unknown",
        "CONFIGURATION": "unknown",
        "INFRASTRUCTURE": "unknown",
        "GENERATED": "unknown",
        "VENDOR": "unknown",
        "STATIC_ASSET": "unknown",
        "OTHER": "unknown",
    },
}


def load_enum_backfill_targets() -> list[tuple[str, str, type[Enum]]]:
    from ruleatlas_contracts import enums as shared_enums

    return [
        ("analysis_versions", "status", shared_enums.AnalysisVersionStatus),
        ("classification_overrides", "classification", shared_enums.SourceFileClassification),
        ("source_locations", "source_type", shared_enums.SourceType),
        ("source_locations", "location_type", shared_enums.SourceLocationType),
        ("scan_runs", "status", shared_enums.ScanStatus),
        ("scan_runs", "current_stage", shared_enums.ScanStage),
        ("scan_runs", "scan_type", shared_enums.ScanType),
        ("source_files", "source_type", shared_enums.SourceType),
        ("source_files", "detected_classification", shared_enums.SourceFileClassification),
        ("source_files", "classification", shared_enums.SourceFileClassification),
        ("rules", "status", shared_enums.RuleStatus),
        ("rules", "rule_category", shared_enums.RuleCategory),
        ("rule_evidence", "source_type", shared_enums.EvidenceSourceType),
        ("rule_relationships", "relationship_type", shared_enums.RuleRelationshipType),
        (
            "rule_relationship_suggestions",
            "suggested_relationship_type",
            shared_enums.RuleRelationshipType,
        ),
        ("rule_relationship_suggestions", "status", shared_enums.RelationshipSuggestionStatus),
        ("ai_task_runs", "task_type", shared_enums.AiTaskType),
        ("ai_task_runs", "status", shared_enums.AiTaskRunStatus),
        ("ai_suggestions", "status", shared_enums.AiSuggestionStatus),
        ("rule_source_claims", "source_type", shared_enums.EvidenceSourceType),
        ("rule_conflicts", "conflict_type", shared_enums.ConflictType),
        ("rule_conflicts", "status", shared_enums.RuleConflictStatus),
        ("rule_decisions", "decision_type", shared_enums.RuleDecisionType),
        ("implementation_gaps", "priority", shared_enums.ImplementationGapPriority),
        ("implementation_gaps", "status", shared_enums.ImplementationGapStatus),
        ("export_documents", "export_type", shared_enums.ExportType),
        ("search_index_records", "entity_type", shared_enums.SearchEntityType),
        ("rule_trace_links", "link_type", shared_enums.RuleTraceLinkType),
        ("coverage_reports", "status", shared_enums.CoverageStatus),
        ("runtime_log_evidence", "source_type", shared_enums.EvidenceSourceType),
        ("runtime_log_evidence", "confidence", shared_enums.RuntimeEvidenceConfidence),
        ("ai_provider_configurations", "provider_mode", shared_enums.AiProviderMode),
        ("ai_model_usage", "provider_mode", shared_enums.AiProviderMode),
    ]


def backfill_enum_column(
    bind: Any,
    table: str,
    column: str,
    enum_cls: type[Enum],
    *,
    extra_mappings: Iterable[tuple[str, str]] = (),
) -> None:
    inspector = inspect(bind)
    if table not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns(table)}
    if column not in columns:
        return

    mappings: dict[str, str] = {}
    for member in _iter_enum_members(enum_cls):
        if member.name != member.value:
            mappings[member.name] = str(member.value)
    for legacy_from, legacy_to in extra_mappings:
        mappings[legacy_from] = legacy_to

    for upper, lower in mappings.items():
        bind.execute(
            text(f"UPDATE {table} SET {column} = :lower WHERE {column} = :upper"),
            {"upper": upper, "lower": lower},
        )


def backfill_lowercase_enum_values(bind: Any) -> None:
    for table, column, enum_cls in load_enum_backfill_targets():
        legacy = LEGACY_ENUM_VALUE_MAP.get((table, column), {})
        backfill_enum_column(
            bind,
            table,
            column,
            enum_cls,
            extra_mappings=legacy.items(),
        )
