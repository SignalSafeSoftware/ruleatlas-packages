"""Contracts for bounded AI investigation of persisted ASTs through MCP tools."""

from ruleatlas_ai.investigation.decisions import (
    AstInvestigationDecision,
    AstNoRuleResult,
)
from ruleatlas_ai.investigation.primitives import (
    AstInvestigationDecisionKind,
    AstInvestigationStopReason,
    AstInvestigationTargetKind,
    AstInvestigationTool,
    AstNoRuleReason,
)
from ruleatlas_ai.investigation.steps import (
    MAX_ORIENTATION_TARGETS,
    MAX_TOOL_RESULT_BYTES,
    AstInvestigationTarget,
    AstModelToolRequest,
    AstOrientationResult,
    AstTargetSelection,
    AstToolResultEnvelope,
)

__all__ = [
    "MAX_ORIENTATION_TARGETS",
    "MAX_TOOL_RESULT_BYTES",
    "AstInvestigationDecision",
    "AstInvestigationDecisionKind",
    "AstInvestigationStopReason",
    "AstInvestigationTarget",
    "AstInvestigationTargetKind",
    "AstInvestigationTool",
    "AstModelToolRequest",
    "AstNoRuleReason",
    "AstNoRuleResult",
    "AstOrientationResult",
    "AstTargetSelection",
    "AstToolResultEnvelope",
]
