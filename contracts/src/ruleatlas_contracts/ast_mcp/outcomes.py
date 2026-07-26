"""Stable outcomes and errors for AST MCP tool execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ruleatlas_contracts.ast_mcp.budgets import AstMcpBudgetSnapshot
from ruleatlas_contracts.ast_mcp.common import (
    require_non_blank,
    require_optional_non_blank,
)


class AstMcpOutcomeStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    TRUNCATED = "truncated"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    FAILED = "failed"


class AstMcpStopReason(StrEnum):
    COMPLETED = "completed"
    PAGE_LIMIT = "page_limit"
    DEPTH_LIMIT = "depth_limit"
    NODE_LIMIT = "node_limit"
    SOURCE_BYTE_LIMIT = "source_byte_limit"
    RESULT_BYTE_LIMIT = "result_byte_limit"
    TOOL_CALL_LIMIT = "tool_call_limit"
    TIME_LIMIT = "time_limit"
    ERROR_LIMIT = "error_limit"
    AUTHORIZATION_DENIED = "authorization_denied"
    DATA_UNAVAILABLE = "data_unavailable"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    USER_CANCELLED = "user_cancelled"
    ORCHESTRATOR_CANCELLED = "orchestrator_cancelled"
    INTERNAL_ERROR = "internal_error"


class AstMcpToolErrorCode(StrEnum):
    INVALID_ARGUMENT = "invalid_argument"
    INVALID_CURSOR = "invalid_cursor"
    UNAUTHORIZED = "unauthorized"
    NOT_FOUND = "not_found"
    VERSION_UNAVAILABLE = "version_unavailable"
    BUDGET_EXHAUSTED = "budget_exhausted"
    CANCELLED = "cancelled"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
    DATA_INTEGRITY = "data_integrity"
    INTERNAL = "internal"


RETRYABLE_ERROR_CODES = frozenset(
    {
        AstMcpToolErrorCode.RATE_LIMITED,
        AstMcpToolErrorCode.TIMEOUT,
        AstMcpToolErrorCode.TEMPORARILY_UNAVAILABLE,
    }
)


@dataclass(frozen=True)
class AstMcpToolError:
    code: AstMcpToolErrorCode
    message: str
    retryable: bool
    retry_after_ms: int | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_non_blank(self.message, "message")
        if self.retry_after_ms is not None and self.retry_after_ms < 0:
            raise ValueError("retry_after_ms must be non-negative")
        if self.retry_after_ms is not None and not self.retryable:
            raise ValueError("retry_after_ms requires retryable=True")
        expected_retryable = self.code in RETRYABLE_ERROR_CODES
        if self.retryable != expected_retryable:
            raise ValueError(f"retryable must be {expected_retryable} for {self.code.value}")

    @classmethod
    def for_code(
        cls,
        code: AstMcpToolErrorCode,
        message: str,
        *,
        retry_after_ms: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> AstMcpToolError:
        return cls(
            code=code,
            message=message,
            retryable=code in RETRYABLE_ERROR_CODES,
            retry_after_ms=retry_after_ms,
            details=details or {},
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code.value,
            "message": self.message,
            "retryable": self.retryable,
            "retry_after_ms": self.retry_after_ms,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class AstMcpInvestigationOutcome:
    status: AstMcpOutcomeStatus
    stop_reason: AstMcpStopReason
    budget: AstMcpBudgetSnapshot
    message: str | None = None
    error: AstMcpToolError | None = None
    resumable: bool = False
    resume_cursor: str | None = None

    def __post_init__(self) -> None:
        require_optional_non_blank(self.message, "message")
        require_optional_non_blank(self.resume_cursor, "resume_cursor")
        if self.status == AstMcpOutcomeStatus.COMPLETE:
            if self.stop_reason != AstMcpStopReason.COMPLETED:
                raise ValueError("complete outcomes require stop_reason=completed")
            if self.error is not None:
                raise ValueError("complete outcomes must not contain an error")
        if self.status == AstMcpOutcomeStatus.FAILED and self.error is None:
            raise ValueError("failed outcomes require an error")
        if self.resume_cursor is not None and not self.resumable:
            raise ValueError("resume_cursor requires resumable=True")
        if self.resumable and self.resume_cursor is None:
            raise ValueError("resumable outcomes require resume_cursor")
        if (
            self.status
            in {
                AstMcpOutcomeStatus.COMPLETE,
                AstMcpOutcomeStatus.CANCELLED,
                AstMcpOutcomeStatus.FAILED,
            }
            and self.resumable
        ):
            raise ValueError(f"{self.status.value} outcomes cannot be resumable")

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "stop_reason": self.stop_reason.value,
            "budget": self.budget.to_dict(),
            "message": self.message,
            "error": self.error.to_dict() if self.error else None,
            "resumable": self.resumable,
            "resume_cursor": self.resume_cursor,
        }


__all__ = [
    "RETRYABLE_ERROR_CODES",
    "AstMcpInvestigationOutcome",
    "AstMcpOutcomeStatus",
    "AstMcpStopReason",
    "AstMcpToolError",
    "AstMcpToolErrorCode",
]
