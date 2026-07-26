"""Contracts for continuing or stopping an AST-backed rule investigation."""

from __future__ import annotations

from dataclasses import dataclass, field

from ruleatlas_contracts.ast import AstNodeCitation, ExactSourceCitation
from ruleatlas_contracts.ast_mcp import AstMcpBudgetSnapshot

from ruleatlas_ai.investigation.primitives import (
    AstInvestigationDecisionKind,
    AstInvestigationStopReason,
    AstNoRuleReason,
    require_non_blank,
    require_optional_non_blank,
)
from ruleatlas_ai.investigation.steps import AstModelToolRequest


@dataclass(frozen=True)
class AstNoRuleResult:
    """Explicit result that never overstates an incomplete investigation."""

    reason: AstNoRuleReason
    explanation: str
    conclusive: bool
    citations: tuple[AstNodeCitation | ExactSourceCitation, ...] = field(default_factory=tuple)
    uncertainty: str | None = None

    def __post_init__(self) -> None:
        require_non_blank(self.explanation, "explanation")
        require_optional_non_blank(self.uncertainty, "uncertainty")
        if self.conclusive and not self.citations:
            raise ValueError("conclusive no-rule results require citations")
        if self.reason == AstNoRuleReason.INSUFFICIENT_EVIDENCE and self.conclusive:
            raise ValueError("insufficient evidence cannot be conclusive")
        if not self.conclusive and self.uncertainty is None:
            raise ValueError("non-conclusive no-rule results require uncertainty")

    def to_dict(self) -> dict[str, object]:
        return {
            "reason": self.reason.value,
            "explanation": self.explanation,
            "conclusive": self.conclusive,
            "citations": [citation.to_dict() for citation in self.citations],
            "uncertainty": self.uncertainty,
        }


@dataclass(frozen=True)
class AstInvestigationDecision:
    decision: AstInvestigationDecisionKind
    explanation: str
    budget: AstMcpBudgetSnapshot
    next_tool_request: AstModelToolRequest | None = None
    stop_reason: AstInvestigationStopReason | None = None
    no_rule: AstNoRuleResult | None = None
    proposal_summary: str | None = None

    def __post_init__(self) -> None:
        require_non_blank(self.explanation, "explanation")
        require_optional_non_blank(self.proposal_summary, "proposal_summary")
        if self.decision == AstInvestigationDecisionKind.CONTINUE:
            if self.next_tool_request is None:
                raise ValueError("continue decisions require next_tool_request")
            if any(value is not None for value in (self.stop_reason, self.no_rule, self.proposal_summary)):
                raise ValueError("continue decisions cannot contain terminal fields")
        else:
            if self.next_tool_request is not None:
                raise ValueError("terminal decisions cannot contain next_tool_request")
            if self.stop_reason is None:
                raise ValueError("terminal decisions require stop_reason")
        if self.decision == AstInvestigationDecisionKind.NO_RULE:
            if self.no_rule is None:
                raise ValueError("no_rule decisions require no_rule result")
            if self.stop_reason not in {
                AstInvestigationStopReason.NO_RULE_FOUND,
                AstInvestigationStopReason.INSUFFICIENT_EVIDENCE,
            }:
                raise ValueError("no_rule decision has incompatible stop_reason")
        elif self.no_rule is not None:
            raise ValueError("no_rule result requires decision=no_rule")
        if self.decision == AstInvestigationDecisionKind.PROPOSE_RULE:
            if self.stop_reason != AstInvestigationStopReason.RULE_PROPOSED:
                raise ValueError("propose_rule decisions require stop_reason=rule_proposed")
            if self.proposal_summary is None:
                raise ValueError("propose_rule decisions require proposal_summary")
        elif self.proposal_summary is not None:
            raise ValueError("proposal_summary requires decision=propose_rule")

    def to_dict(self) -> dict[str, object]:
        return {
            "decision": self.decision.value,
            "explanation": self.explanation,
            "budget": self.budget.to_dict(),
            "next_tool_request": (self.next_tool_request.to_dict() if self.next_tool_request else None),
            "stop_reason": self.stop_reason.value if self.stop_reason else None,
            "no_rule": self.no_rule.to_dict() if self.no_rule else None,
            "proposal_summary": self.proposal_summary,
        }


__all__ = ["AstInvestigationDecision", "AstNoRuleResult"]
