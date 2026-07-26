"""Immutable limits and consumption snapshots for bounded MCP investigations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AstMcpBudgetDimension(StrEnum):
    TOOL_CALLS = "tool_calls"
    NODES_RETURNED = "nodes_returned"
    SOURCE_BYTES = "source_bytes"
    RESULT_BYTES = "result_bytes"
    ELAPSED_MS = "elapsed_ms"
    ERRORS = "errors"


def _require_positive(value: int, field_name: str) -> None:
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")


def _require_non_negative(value: int, field_name: str) -> None:
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")


@dataclass(frozen=True)
class AstMcpBudgetLimits:
    """Hard ceilings supplied by trusted orchestration, never by the model."""

    max_tool_calls: int = 100
    max_nodes_returned: int = 10_000
    max_source_bytes: int = 500_000
    max_result_bytes: int = 2_000_000
    max_elapsed_ms: int = 300_000
    max_errors: int = 10

    def __post_init__(self) -> None:
        for field_name, value in {
            "max_tool_calls": self.max_tool_calls,
            "max_nodes_returned": self.max_nodes_returned,
            "max_source_bytes": self.max_source_bytes,
            "max_result_bytes": self.max_result_bytes,
            "max_elapsed_ms": self.max_elapsed_ms,
            "max_errors": self.max_errors,
        }.items():
            _require_positive(value, field_name)

    def limit_for(self, dimension: AstMcpBudgetDimension) -> int:
        values = {
            AstMcpBudgetDimension.TOOL_CALLS: self.max_tool_calls,
            AstMcpBudgetDimension.NODES_RETURNED: self.max_nodes_returned,
            AstMcpBudgetDimension.SOURCE_BYTES: self.max_source_bytes,
            AstMcpBudgetDimension.RESULT_BYTES: self.max_result_bytes,
            AstMcpBudgetDimension.ELAPSED_MS: self.max_elapsed_ms,
            AstMcpBudgetDimension.ERRORS: self.max_errors,
        }
        return values[dimension]

    def to_dict(self) -> dict[str, int]:
        return {
            "max_tool_calls": self.max_tool_calls,
            "max_nodes_returned": self.max_nodes_returned,
            "max_source_bytes": self.max_source_bytes,
            "max_result_bytes": self.max_result_bytes,
            "max_elapsed_ms": self.max_elapsed_ms,
            "max_errors": self.max_errors,
        }


@dataclass(frozen=True)
class AstMcpBudgetConsumption:
    """Monotonic cumulative usage at one investigation boundary."""

    tool_calls: int = 0
    nodes_returned: int = 0
    source_bytes: int = 0
    result_bytes: int = 0
    elapsed_ms: int = 0
    errors: int = 0

    def __post_init__(self) -> None:
        for field_name, value in self.to_dict().items():
            _require_non_negative(value, field_name)

    def consumed_for(self, dimension: AstMcpBudgetDimension) -> int:
        values = {
            AstMcpBudgetDimension.TOOL_CALLS: self.tool_calls,
            AstMcpBudgetDimension.NODES_RETURNED: self.nodes_returned,
            AstMcpBudgetDimension.SOURCE_BYTES: self.source_bytes,
            AstMcpBudgetDimension.RESULT_BYTES: self.result_bytes,
            AstMcpBudgetDimension.ELAPSED_MS: self.elapsed_ms,
            AstMcpBudgetDimension.ERRORS: self.errors,
        }
        return values[dimension]

    def exceeded_dimensions(self, limits: AstMcpBudgetLimits) -> tuple[AstMcpBudgetDimension, ...]:
        return tuple(
            dimension
            for dimension in AstMcpBudgetDimension
            if self.consumed_for(dimension) > limits.limit_for(dimension)
        )

    def exhausted_dimensions(self, limits: AstMcpBudgetLimits) -> tuple[AstMcpBudgetDimension, ...]:
        return tuple(
            dimension
            for dimension in AstMcpBudgetDimension
            if self.consumed_for(dimension) >= limits.limit_for(dimension)
        )

    def remaining(self, limits: AstMcpBudgetLimits) -> dict[str, int]:
        return {
            dimension.value: max(
                0,
                limits.limit_for(dimension) - self.consumed_for(dimension),
            )
            for dimension in AstMcpBudgetDimension
        }

    def add(self, delta: AstMcpBudgetConsumption) -> AstMcpBudgetConsumption:
        return AstMcpBudgetConsumption(
            tool_calls=self.tool_calls + delta.tool_calls,
            nodes_returned=self.nodes_returned + delta.nodes_returned,
            source_bytes=self.source_bytes + delta.source_bytes,
            result_bytes=self.result_bytes + delta.result_bytes,
            elapsed_ms=self.elapsed_ms + delta.elapsed_ms,
            errors=self.errors + delta.errors,
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "tool_calls": self.tool_calls,
            "nodes_returned": self.nodes_returned,
            "source_bytes": self.source_bytes,
            "result_bytes": self.result_bytes,
            "elapsed_ms": self.elapsed_ms,
            "errors": self.errors,
        }


@dataclass(frozen=True)
class AstMcpBudgetSnapshot:
    limits: AstMcpBudgetLimits
    consumed: AstMcpBudgetConsumption

    @property
    def exhausted(self) -> bool:
        return bool(self.consumed.exhausted_dimensions(self.limits))

    @property
    def exceeded(self) -> bool:
        return bool(self.consumed.exceeded_dimensions(self.limits))

    def to_dict(self) -> dict[str, object]:
        return {
            "limits": self.limits.to_dict(),
            "consumed": self.consumed.to_dict(),
            "remaining": self.consumed.remaining(self.limits),
            "exhausted_dimensions": [value.value for value in self.consumed.exhausted_dimensions(self.limits)],
            "exceeded_dimensions": [value.value for value in self.consumed.exceeded_dimensions(self.limits)],
        }


__all__ = [
    "AstMcpBudgetConsumption",
    "AstMcpBudgetDimension",
    "AstMcpBudgetLimits",
    "AstMcpBudgetSnapshot",
]
