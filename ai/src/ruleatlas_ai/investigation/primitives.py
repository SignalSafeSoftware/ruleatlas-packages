"""Provider-neutral vocabularies and safety helpers for AST investigations."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class AstInvestigationTool(StrEnum):
    LIST_FILES = "list_ast_files"
    GET_DOCUMENT = "get_ast_document"
    FIND_NODES = "find_ast_nodes"
    GET_NODE = "get_ast_node"
    LIST_CHILDREN = "list_ast_children"
    GET_SUBTREE = "get_ast_subtree"
    GET_SYMBOL_AST = "get_symbol_ast"
    GET_SOURCE_EXCERPT = "get_source_excerpt"
    FIND_CALLS = "find_ast_calls"
    FIND_CONDITIONS_ASSIGNMENTS = "find_conditions_assignments"
    FIND_RELATED_EVIDENCE = "find_related_evidence"


class AstInvestigationTargetKind(StrEnum):
    DOCUMENT = "document"
    SOURCE_SYMBOL = "source_symbol"
    AST_NODE = "ast_node"


class AstInvestigationDecisionKind(StrEnum):
    CONTINUE = "continue"
    PROPOSE_RULE = "propose_rule"
    NO_RULE = "no_rule"
    STOP = "stop"


class AstInvestigationStopReason(StrEnum):
    RULE_PROPOSED = "rule_proposed"
    NO_RULE_FOUND = "no_rule_found"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    BUDGET_EXHAUSTED = "budget_exhausted"
    TOOL_FAILURE = "tool_failure"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    CANCELLED = "cancelled"
    UNSUPPORTED_LANGUAGE = "unsupported_language"


class AstNoRuleReason(StrEnum):
    NO_ENFORCED_BEHAVIOR = "no_enforced_behavior"
    CONFIGURATION_ONLY = "configuration_only"
    SCAFFOLD_OR_BOILERPLATE = "scaffold_or_boilerplate"
    TEST_ONLY = "test_only"
    CONTRADICTED_BY_EVIDENCE = "contradicted_by_evidence"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    UNSUPPORTED_CONSTRUCT = "unsupported_construct"


_FORBIDDEN_SCOPE_KEYS = frozenset({"analysis_version_id", "organization_id", "project_id"})


def require_non_blank(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")


def require_optional_non_blank(value: str | None, field_name: str) -> None:
    if value is not None:
        require_non_blank(value, field_name)


def _reject_forbidden_scope_key(key: str | None) -> None:
    if key is not None and key.casefold() in _FORBIDDEN_SCOPE_KEYS:
        raise ValueError(f"trusted scope is forbidden in tool arguments: {key}")


def _visit_tool_argument(item: Any, *, key: str | None = None) -> None:
    _reject_forbidden_scope_key(key)
    if isinstance(item, dict):
        for nested_key, nested_value in item.items():
            if not isinstance(nested_key, str) or not nested_key.strip():
                raise ValueError("tool argument keys must be non-blank strings")
            _visit_tool_argument(nested_value, key=nested_key)
        return
    if isinstance(item, list):
        for nested_value in item:
            _visit_tool_argument(nested_value)
        return
    if item is not None and not isinstance(item, (str, int, float, bool)):
        raise ValueError("tool arguments must contain JSON-compatible values")


def validate_model_tool_arguments(value: dict[str, Any]) -> None:
    """Reject trusted scope and non-JSON values in model-authored tool arguments."""
    _visit_tool_argument(value)


__all__ = [
    "AstInvestigationDecisionKind",
    "AstInvestigationStopReason",
    "AstInvestigationTargetKind",
    "AstInvestigationTool",
    "AstNoRuleReason",
    "require_non_blank",
    "require_optional_non_blank",
    "validate_model_tool_arguments",
]
