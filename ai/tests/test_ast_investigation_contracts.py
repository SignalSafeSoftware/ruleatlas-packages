"""Tests for bounded AST investigation step and decision contracts."""

from __future__ import annotations

import pytest
from ruleatlas_contracts.ast import (
    AstCitationScope,
    AstNodeCitation,
    AstPoint,
    AstSourceRange,
    ParserIdentity,
)
from ruleatlas_contracts.ast_mcp import (
    AstMcpBudgetConsumption,
    AstMcpBudgetLimits,
    AstMcpBudgetSnapshot,
    AstMcpOutcomeStatus,
    AstMcpToolError,
    AstMcpToolErrorCode,
    AstMcpTraceMetadata,
)

from ruleatlas_ai.investigation import (
    AstInvestigationDecision,
    AstInvestigationDecisionKind,
    AstInvestigationStopReason,
    AstInvestigationTarget,
    AstInvestigationTargetKind,
    AstInvestigationTool,
    AstModelToolRequest,
    AstNoRuleReason,
    AstNoRuleResult,
    AstOrientationResult,
    AstTargetSelection,
    AstToolResultEnvelope,
)


def _budget() -> AstMcpBudgetSnapshot:
    return AstMcpBudgetSnapshot(
        AstMcpBudgetLimits(),
        AstMcpBudgetConsumption(tool_calls=1),
    )


def _citation() -> AstNodeCitation:
    return AstNodeCitation(
        scope=AstCitationScope("project-1", "analysis-1"),
        document_key="src/auth.py:sha256:content",
        node_key="node-1",
        source_file_id="file-1",
        source_path="src/auth.py",
        content_hash="sha256:content",
        subtree_hash="sha256:subtree",
        source_range=AstSourceRange(
            0,
            10,
            AstPoint(0, 0),
            AstPoint(0, 10),
        ),
        parser=ParserIdentity(
            parser_key="tree_sitter",
            parser_version="0.26.0",
            language_key="python",
            grammar_key="tree-sitter-python",
            grammar_version="0.25.0",
        ),
        raw_node_type="if_statement",
    )


def _request() -> AstModelToolRequest:
    return AstModelToolRequest(
        request_id="request-1",
        tool=AstInvestigationTool.FIND_NODES,
        arguments={"categories": ["condition"], "limit": 25},
        purpose="Find enforced branches in the selected document.",
    )


def _trace(*, error_code: AstMcpToolErrorCode | None = None) -> AstMcpTraceMetadata:
    return AstMcpTraceMetadata(
        request_id="request-1",
        tool_name=AstInvestigationTool.FIND_NODES.value,
        duration_ms=10,
        result_items=2,
        result_bytes=200,
        truncated=False,
        error_code=error_code,
    )


def test_orientation_and_target_selection_are_bounded_and_deterministic() -> None:
    orientation = AstOrientationResult(
        languages=("python",),
        document_count=1,
        candidate_target_ids=("document-1",),
        summary="One Python source document is available.",
        truncated=False,
    )
    target = AstInvestigationTarget(
        target_kind=AstInvestigationTargetKind.DOCUMENT,
        target_id="document-1",
        reason="Contains authorization conditions.",
        priority=90,
        source_path="src/auth.py",
        anchor_citations=(_citation(),),
    )
    selection = AstTargetSelection(selected=(target,))

    assert orientation.to_dict()["languages"] == ["python"]
    assert selection.to_dict() == selection.to_dict()
    with pytest.raises(ValueError, match="both selected and rejected"):
        AstTargetSelection(
            selected=(target,),
            rejected_target_ids=("document-1",),
        )


def test_orientation_cursor_requires_truncation() -> None:
    with pytest.raises(ValueError, match="next_cursor requires"):
        AstOrientationResult(
            languages=("python",),
            document_count=1,
            candidate_target_ids=("document-1",),
            summary="Orientation.",
            truncated=False,
            next_cursor="opaque",
        )


@pytest.mark.parametrize(
    "scope_key",
    ["project_id", "organization_id", "analysis_version_id"],
)
def test_model_tool_requests_cannot_supply_trusted_scope(scope_key: str) -> None:
    with pytest.raises(ValueError, match="trusted scope is forbidden"):
        AstModelToolRequest(
            request_id="request-1",
            tool=AstInvestigationTool.GET_NODE,
            arguments={"filter": {scope_key: "attacker-selected"}},
            purpose="Read a node.",
        )


def test_model_tool_arguments_must_be_json_compatible() -> None:
    with pytest.raises(ValueError, match="JSON-compatible"):
        AstModelToolRequest(
            request_id="request-1",
            tool=AstInvestigationTool.GET_NODE,
            arguments={"node_id": object()},
            purpose="Read a node.",
        )


def test_tool_result_envelope_correlates_request_tool_trace_and_error() -> None:
    envelope = AstToolResultEnvelope(
        request_id="request-1",
        tool=AstInvestigationTool.FIND_NODES,
        status=AstMcpOutcomeStatus.COMPLETE,
        payload={"nodes": [{"node_id": "node-1"}]},
        trace=_trace(),
        budget=_budget(),
    )

    assert envelope.to_dict()["tool"] == "find_ast_nodes"
    with pytest.raises(ValueError, match="tool must match"):
        AstToolResultEnvelope(
            request_id="request-1",
            tool=AstInvestigationTool.GET_NODE,
            status=AstMcpOutcomeStatus.COMPLETE,
            payload={},
            trace=_trace(),
            budget=_budget(),
        )
    with pytest.raises(ValueError, match="failed tool results require"):
        AstToolResultEnvelope(
            request_id="request-1",
            tool=AstInvestigationTool.FIND_NODES,
            status=AstMcpOutcomeStatus.FAILED,
            payload=None,
            trace=_trace(error_code=AstMcpToolErrorCode.INTERNAL),
            budget=_budget(),
        )


def test_failed_tool_result_carries_structured_error() -> None:
    error = AstMcpToolError.for_code(
        AstMcpToolErrorCode.TIMEOUT,
        "AST query timed out.",
    )
    envelope = AstToolResultEnvelope(
        request_id="request-1",
        tool=AstInvestigationTool.FIND_NODES,
        status=AstMcpOutcomeStatus.FAILED,
        payload=None,
        trace=_trace(error_code=error.code),
        budget=_budget(),
        error=error,
    )

    assert envelope.to_dict()["error"] == error.to_dict()


def test_continue_decision_requires_exactly_one_next_tool_request() -> None:
    decision = AstInvestigationDecision(
        decision=AstInvestigationDecisionKind.CONTINUE,
        explanation="More structural evidence is needed.",
        budget=_budget(),
        next_tool_request=_request(),
    )

    assert decision.to_dict()["next_tool_request"] == _request().to_dict()
    with pytest.raises(ValueError, match="require next_tool_request"):
        AstInvestigationDecision(
            decision=AstInvestigationDecisionKind.CONTINUE,
            explanation="Continue.",
            budget=_budget(),
        )


def test_propose_rule_decision_is_terminal_but_not_yet_a_proposal() -> None:
    decision = AstInvestigationDecision(
        decision=AstInvestigationDecisionKind.PROPOSE_RULE,
        explanation="The evidence supports a candidate rule.",
        budget=_budget(),
        stop_reason=AstInvestigationStopReason.RULE_PROPOSED,
        proposal_summary="A manager must approve high-value invoices.",
    )

    assert decision.to_dict()["decision"] == "propose_rule"
    with pytest.raises(ValueError, match="require proposal_summary"):
        AstInvestigationDecision(
            decision=AstInvestigationDecisionKind.PROPOSE_RULE,
            explanation="Propose.",
            budget=_budget(),
            stop_reason=AstInvestigationStopReason.RULE_PROPOSED,
        )


def test_no_rule_result_distinguishes_conclusion_from_insufficient_evidence() -> None:
    conclusive = AstNoRuleResult(
        reason=AstNoRuleReason.CONFIGURATION_ONLY,
        explanation="The target only declares a provider URL.",
        conclusive=True,
        citations=(_citation(),),
    )
    decision = AstInvestigationDecision(
        decision=AstInvestigationDecisionKind.NO_RULE,
        explanation="No enforced behavior was found.",
        budget=_budget(),
        stop_reason=AstInvestigationStopReason.NO_RULE_FOUND,
        no_rule=conclusive,
    )

    assert decision.to_dict()["no_rule"] == conclusive.to_dict()
    with pytest.raises(ValueError, match="cannot be conclusive"):
        AstNoRuleResult(
            reason=AstNoRuleReason.INSUFFICIENT_EVIDENCE,
            explanation="The investigation ended early.",
            conclusive=True,
            citations=(_citation(),),
        )
    with pytest.raises(ValueError, match="require uncertainty"):
        AstNoRuleResult(
            reason=AstNoRuleReason.INSUFFICIENT_EVIDENCE,
            explanation="The investigation ended early.",
            conclusive=False,
        )


def test_stop_decision_uses_explicit_reason() -> None:
    decision = AstInvestigationDecision(
        decision=AstInvestigationDecisionKind.STOP,
        explanation="The trusted investigation budget is exhausted.",
        budget=_budget(),
        stop_reason=AstInvestigationStopReason.BUDGET_EXHAUSTED,
    )

    assert decision.to_dict()["stop_reason"] == "budget_exhausted"
    with pytest.raises(ValueError, match="terminal decisions require"):
        AstInvestigationDecision(
            decision=AstInvestigationDecisionKind.STOP,
            explanation="Stop.",
            budget=_budget(),
        )
