"""Tests for MCP investigation budgets, outcomes, errors, and safe tracing."""

from __future__ import annotations

import pytest

from ruleatlas_contracts.ast_mcp import (
    AstMcpBudgetConsumption,
    AstMcpBudgetDimension,
    AstMcpBudgetLimits,
    AstMcpBudgetSnapshot,
    AstMcpInvestigationOutcome,
    AstMcpOutcomeStatus,
    AstMcpStopReason,
    AstMcpToolError,
    AstMcpToolErrorCode,
    AstMcpTraceMetadata,
)


def _limits() -> AstMcpBudgetLimits:
    return AstMcpBudgetLimits(
        max_tool_calls=5,
        max_nodes_returned=100,
        max_source_bytes=1_000,
        max_result_bytes=2_000,
        max_elapsed_ms=10_000,
        max_errors=2,
    )


def test_consumption_addition_remaining_and_exhaustion_are_deterministic() -> None:
    initial = AstMcpBudgetConsumption(
        tool_calls=2,
        nodes_returned=10,
        source_bytes=100,
    )
    combined = initial.add(
        AstMcpBudgetConsumption(
            tool_calls=3,
            nodes_returned=90,
            result_bytes=100,
        )
    )
    snapshot = AstMcpBudgetSnapshot(_limits(), combined)

    assert snapshot.exhausted
    assert not snapshot.exceeded
    assert combined.exhausted_dimensions(_limits()) == (
        AstMcpBudgetDimension.TOOL_CALLS,
        AstMcpBudgetDimension.NODES_RETURNED,
    )
    assert combined.remaining(_limits())["tool_calls"] == 0
    snapshot_payload = snapshot.to_dict()
    assert snapshot_payload["exhausted_dimensions"] == ["tool_calls", "nodes_returned"]
    assert snapshot_payload == snapshot.to_dict()


def test_invalid_limits_and_consumption_are_rejected() -> None:
    with pytest.raises(ValueError, match="max_tool_calls must be positive"):
        AstMcpBudgetLimits(max_tool_calls=0)
    with pytest.raises(ValueError, match="tool_calls must be non-negative"):
        AstMcpBudgetConsumption(tool_calls=-1)


def test_exceeded_dimensions_are_distinct_from_exact_exhaustion() -> None:
    consumption = AstMcpBudgetConsumption(tool_calls=6)

    assert consumption.exceeded_dimensions(_limits()) == (AstMcpBudgetDimension.TOOL_CALLS,)
    assert consumption.exhausted_dimensions(_limits()) == (AstMcpBudgetDimension.TOOL_CALLS,)


@pytest.mark.parametrize(
    ("code", "retryable"),
    [
        (AstMcpToolErrorCode.RATE_LIMITED, True),
        (AstMcpToolErrorCode.TIMEOUT, True),
        (AstMcpToolErrorCode.TEMPORARILY_UNAVAILABLE, True),
        (AstMcpToolErrorCode.INVALID_ARGUMENT, False),
        (AstMcpToolErrorCode.UNAUTHORIZED, False),
        (AstMcpToolErrorCode.INTERNAL, False),
    ],
)
def test_error_factory_applies_stable_retry_policy(code: AstMcpToolErrorCode, retryable: bool) -> None:
    error = AstMcpToolError.for_code(code, "tool failed")

    assert error.retryable is retryable
    assert error.to_dict()["code"] == code.value


def test_retry_policy_cannot_be_misstated() -> None:
    with pytest.raises(ValueError, match="retryable must be True"):
        AstMcpToolError(
            code=AstMcpToolErrorCode.TIMEOUT,
            message="timed out",
            retryable=False,
        )
    with pytest.raises(ValueError, match="retry_after_ms requires"):
        AstMcpToolError(
            code=AstMcpToolErrorCode.NOT_FOUND,
            message="missing",
            retryable=False,
            retry_after_ms=100,
        )


def test_complete_partial_failed_and_cancelled_outcomes_are_consistent() -> None:
    budget = AstMcpBudgetSnapshot(_limits(), AstMcpBudgetConsumption())
    complete = AstMcpInvestigationOutcome(
        status=AstMcpOutcomeStatus.COMPLETE,
        stop_reason=AstMcpStopReason.COMPLETED,
        budget=budget,
    )
    partial = AstMcpInvestigationOutcome(
        status=AstMcpOutcomeStatus.PARTIAL,
        stop_reason=AstMcpStopReason.TOOL_CALL_LIMIT,
        budget=budget,
        resumable=True,
        resume_cursor="opaque",
    )

    assert complete.to_dict()["status"] == "complete"
    assert partial.to_dict()["resumable"] is True
    with pytest.raises(ValueError, match="failed outcomes require"):
        AstMcpInvestigationOutcome(
            status=AstMcpOutcomeStatus.FAILED,
            stop_reason=AstMcpStopReason.INTERNAL_ERROR,
            budget=budget,
        )
    with pytest.raises(ValueError, match="cannot be resumable"):
        AstMcpInvestigationOutcome(
            status=AstMcpOutcomeStatus.CANCELLED,
            stop_reason=AstMcpStopReason.USER_CANCELLED,
            budget=budget,
            resumable=True,
            resume_cursor="opaque",
        )


def test_trace_metadata_accepts_only_allowlisted_operational_attributes() -> None:
    trace = AstMcpTraceMetadata(
        request_id="request-1",
        tool_name="find_ast_nodes",
        duration_ms=12,
        result_items=3,
        result_bytes=400,
        truncated=False,
        attributes={"language_key": "python", "operation": "search"},
    )

    assert trace.to_dict()["attributes"] == {
        "language_key": "python",
        "operation": "search",
    }
    with pytest.raises(ValueError, match="not allowlisted"):
        AstMcpTraceMetadata(
            request_id="request-2",
            tool_name="source_excerpt",
            duration_ms=1,
            result_items=1,
            result_bytes=10,
            truncated=False,
            attributes={"source_text": "secret source"},
        )
    with pytest.raises(ValueError, match="JSON scalar"):
        AstMcpTraceMetadata(
            request_id="request-3",
            tool_name="find_ast_nodes",
            duration_ms=1,
            result_items=1,
            result_bytes=10,
            truncated=False,
            attributes={"operation": object()},
        )
    with pytest.raises(ValueError, match="JSON scalar"):
        AstMcpTraceMetadata(
            request_id="request-4",
            tool_name="find_ast_nodes",
            duration_ms=1,
            result_items=1,
            result_bytes=10,
            truncated=False,
            attributes={"operation": {"source_text": "hidden"}},
        )
