"""Dict/JSON serialization for discovery DTOs."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any, cast

from ruleatlas_discovery.models import (
    DirectoryNode,
    DiscoveryFile,
    DiscoveryScope,
    FileTypeMapping,
    FileTypeSummary,
    InventoryMetrics,
    LineCountSummary,
    ResolvedFileType,
)


def _serialize(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _serialize(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}
    return value


def _serialize_mapping(value: Any) -> dict[str, Any]:
    """Serialize a dataclass instance to a dict (top-level DTOs are always dataclasses)."""
    return cast("dict[str, Any]", _serialize(value))


def discovery_file_to_dict(row: DiscoveryFile) -> dict[str, Any]:
    return _serialize_mapping(row)


def file_type_mapping_to_dict(entry: FileTypeMapping) -> dict[str, Any]:
    return _serialize_mapping(entry)


def resolved_file_type_to_dict(resolved: ResolvedFileType) -> dict[str, Any]:
    return _serialize_mapping(resolved)


def file_type_summary_to_dict(row: FileTypeSummary) -> dict[str, Any]:
    return _serialize_mapping(row)


def directory_node_to_dict(node: DirectoryNode) -> dict[str, Any]:
    return _serialize_mapping(node)


def inventory_metrics_to_dict(metrics: InventoryMetrics) -> dict[str, Any]:
    return _serialize_mapping(metrics)


def line_count_summary_to_dict(summary: LineCountSummary) -> dict[str, Any]:
    return _serialize_mapping(summary)


def discovery_scope_to_dict(scope: DiscoveryScope) -> dict[str, Any]:
    return _serialize_mapping(scope)


def discovery_file_from_dict(payload: dict[str, Any]) -> DiscoveryFile:
    allowed = {field.name for field in fields(DiscoveryFile)}
    return DiscoveryFile(**{key: payload[key] for key in payload if key in allowed})
