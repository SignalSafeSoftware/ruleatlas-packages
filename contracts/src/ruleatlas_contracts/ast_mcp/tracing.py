"""Trace-safe metadata that excludes source text, prompts, arguments, and credentials."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ruleatlas_contracts.ast_mcp.budgets import AstMcpBudgetConsumption
from ruleatlas_contracts.ast_mcp.common import require_non_blank
from ruleatlas_contracts.ast_mcp.outcomes import AstMcpToolErrorCode

TRACE_SAFE_ATTRIBUTE_KEYS = frozenset(
    {
        "cache_namespace",
        "call_direction",
        "evidence_kind",
        "grammar_key",
        "language_key",
        "node_category",
        "operation",
        "parser_key",
        "transport",
    }
)


@dataclass(frozen=True)
class AstMcpTraceMetadata:
    """Operational facts safe for durable traces; never a payload capture."""

    request_id: str
    tool_name: str
    duration_ms: int
    result_items: int
    result_bytes: int
    truncated: bool
    cache_hit: bool = False
    error_code: AstMcpToolErrorCode | None = None
    consumption_delta: AstMcpBudgetConsumption = field(default_factory=AstMcpBudgetConsumption)
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_non_blank(self.request_id, "request_id")
        require_non_blank(self.tool_name, "tool_name")
        if min(self.duration_ms, self.result_items, self.result_bytes) < 0:
            raise ValueError("trace counters must be non-negative")
        for key in self.attributes:
            require_non_blank(key, "attribute key")
            if key not in TRACE_SAFE_ATTRIBUTE_KEYS:
                raise ValueError(f"trace attribute is not allowlisted: {key}")
        self._validate_attribute_values(self.attributes)

    @classmethod
    def _validate_attribute_values(cls, value: dict[str, Any]) -> None:
        for item in value.values():
            if isinstance(item, list):
                if any(nested is not None and not isinstance(nested, (str, int, float, bool)) for nested in item):
                    raise ValueError("trace attribute lists must contain only JSON scalar values")
            elif item is not None and not isinstance(item, (str, int, float, bool)):
                raise ValueError("trace attributes must contain JSON scalar values")

    def to_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "tool_name": self.tool_name,
            "duration_ms": self.duration_ms,
            "result_items": self.result_items,
            "result_bytes": self.result_bytes,
            "truncated": self.truncated,
            "cache_hit": self.cache_hit,
            "error_code": self.error_code.value if self.error_code else None,
            "consumption_delta": self.consumption_delta.to_dict(),
            "attributes": dict(self.attributes),
        }


__all__ = ["TRACE_SAFE_ATTRIBUTE_KEYS", "AstMcpTraceMetadata"]
