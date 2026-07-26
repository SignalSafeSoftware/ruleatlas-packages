"""Contracts for orientation, target selection, and model tool interaction."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ruleatlas_contracts.ast import AstNodeCitation, ExactSourceCitation
from ruleatlas_contracts.ast_mcp import (
    AstMcpBudgetSnapshot,
    AstMcpOutcomeStatus,
    AstMcpToolError,
    AstMcpTraceMetadata,
)

from ruleatlas_ai.investigation.primitives import (
    AstInvestigationTargetKind,
    AstInvestigationTool,
    require_non_blank,
    require_optional_non_blank,
    validate_model_tool_arguments,
)

MAX_ORIENTATION_TARGETS = 200
MAX_TOOL_RESULT_BYTES = 2_000_000


@dataclass(frozen=True)
class AstOrientationResult:
    """Bounded repository orientation facts available before target selection."""

    languages: tuple[str, ...]
    document_count: int
    candidate_target_ids: tuple[str, ...]
    summary: str
    truncated: bool
    next_cursor: str | None = None

    def __post_init__(self) -> None:
        if any(not item.strip() for item in self.languages):
            raise ValueError("languages must not contain blank values")
        if len(set(self.languages)) != len(self.languages):
            raise ValueError("languages must not contain duplicates")
        if self.document_count < 0:
            raise ValueError("document_count must be non-negative")
        if not self.candidate_target_ids and self.document_count > 0 and not self.truncated:
            raise ValueError("non-empty orientation requires candidate targets or truncation")
        if len(self.candidate_target_ids) > MAX_ORIENTATION_TARGETS:
            raise ValueError(f"candidate_target_ids must not exceed {MAX_ORIENTATION_TARGETS}")
        if any(not item.strip() for item in self.candidate_target_ids):
            raise ValueError("candidate_target_ids must not contain blank values")
        require_non_blank(self.summary, "summary")
        require_optional_non_blank(self.next_cursor, "next_cursor")
        if self.next_cursor is not None and not self.truncated:
            raise ValueError("next_cursor requires truncated=True")

    def to_dict(self) -> dict[str, object]:
        return {
            "languages": list(self.languages),
            "document_count": self.document_count,
            "candidate_target_ids": list(self.candidate_target_ids),
            "summary": self.summary,
            "truncated": self.truncated,
            "next_cursor": self.next_cursor,
        }


@dataclass(frozen=True)
class AstInvestigationTarget:
    target_kind: AstInvestigationTargetKind
    target_id: str
    reason: str
    priority: int
    source_path: str | None = None
    anchor_citations: tuple[AstNodeCitation | ExactSourceCitation, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        require_non_blank(self.target_id, "target_id")
        require_non_blank(self.reason, "reason")
        require_optional_non_blank(self.source_path, "source_path")
        if not 0 <= self.priority <= 100:
            raise ValueError("priority must be between 0 and 100")

    def to_dict(self) -> dict[str, object]:
        return {
            "target_kind": self.target_kind.value,
            "target_id": self.target_id,
            "reason": self.reason,
            "priority": self.priority,
            "source_path": self.source_path,
            "anchor_citations": [citation.to_dict() for citation in self.anchor_citations],
        }


@dataclass(frozen=True)
class AstTargetSelection:
    selected: tuple[AstInvestigationTarget, ...]
    rejected_target_ids: tuple[str, ...] = field(default_factory=tuple)
    truncated: bool = False
    next_cursor: str | None = None

    def __post_init__(self) -> None:
        selected_ids = [item.target_id for item in self.selected]
        if len(set(selected_ids)) != len(selected_ids):
            raise ValueError("selected targets must not contain duplicates")
        if any(not item.strip() for item in self.rejected_target_ids):
            raise ValueError("rejected_target_ids must not contain blank values")
        if set(selected_ids) & set(self.rejected_target_ids):
            raise ValueError("a target cannot be both selected and rejected")
        require_optional_non_blank(self.next_cursor, "next_cursor")
        if self.next_cursor is not None and not self.truncated:
            raise ValueError("next_cursor requires truncated=True")

    def to_dict(self) -> dict[str, object]:
        return {
            "selected": [item.to_dict() for item in self.selected],
            "rejected_target_ids": list(self.rejected_target_ids),
            "truncated": self.truncated,
            "next_cursor": self.next_cursor,
        }


@dataclass(frozen=True)
class AstModelToolRequest:
    request_id: str
    tool: AstInvestigationTool
    arguments: dict[str, Any]
    purpose: str

    def __post_init__(self) -> None:
        require_non_blank(self.request_id, "request_id")
        require_non_blank(self.purpose, "purpose")
        validate_model_tool_arguments(self.arguments)

    def to_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "tool": self.tool.value,
            "arguments": dict(self.arguments),
            "purpose": self.purpose,
        }


@dataclass(frozen=True)
class AstToolResultEnvelope:
    request_id: str
    tool: AstInvestigationTool
    status: AstMcpOutcomeStatus
    payload: dict[str, Any] | None
    trace: AstMcpTraceMetadata
    budget: AstMcpBudgetSnapshot
    error: AstMcpToolError | None = None

    def __post_init__(self) -> None:
        require_non_blank(self.request_id, "request_id")
        if self.request_id != self.trace.request_id:
            raise ValueError("request_id must match trace.request_id")
        if self.tool.value != self.trace.tool_name:
            raise ValueError("tool must match trace.tool_name")
        if self.status == AstMcpOutcomeStatus.FAILED and self.error is None:
            raise ValueError("failed tool results require an error")
        if self.status == AstMcpOutcomeStatus.COMPLETE and self.error is not None:
            raise ValueError("complete tool results must not contain an error")
        if self.payload is not None:
            validate_model_tool_arguments(self.payload)
            encoded_size = len(
                json.dumps(
                    self.payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
            )
            if encoded_size > MAX_TOOL_RESULT_BYTES:
                raise ValueError(f"payload must not exceed {MAX_TOOL_RESULT_BYTES} bytes")

    def to_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "tool": self.tool.value,
            "status": self.status.value,
            "payload": dict(self.payload) if self.payload is not None else None,
            "trace": self.trace.to_dict(),
            "budget": self.budget.to_dict(),
            "error": self.error.to_dict() if self.error else None,
        }


__all__ = [
    "MAX_ORIENTATION_TARGETS",
    "MAX_TOOL_RESULT_BYTES",
    "AstInvestigationTarget",
    "AstModelToolRequest",
    "AstOrientationResult",
    "AstTargetSelection",
    "AstToolResultEnvelope",
]
