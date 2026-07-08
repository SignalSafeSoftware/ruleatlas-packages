"""Inventory metrics aggregation."""

from __future__ import annotations

from ruleatlas_discovery.line_counts import aggregate_line_counts, aggregate_line_counts_by_file_type
from ruleatlas_discovery.models import DiscoveryFile, InventoryMetrics


def build_inventory_metrics(
    files: list[DiscoveryFile],
    *,
    resolver=None,
) -> InventoryMetrics:
    line_totals = aggregate_line_counts(files)
    by_file_type = aggregate_line_counts_by_file_type(files, resolver=resolver)
    return InventoryMetrics(
        total_files=len(files),
        total_lines=line_totals.total_lines,
        code_lines=line_totals.code_lines,
        comment_lines=line_totals.comment_lines,
        blank_lines=line_totals.blank_lines,
        by_file_type=by_file_type,
    )
