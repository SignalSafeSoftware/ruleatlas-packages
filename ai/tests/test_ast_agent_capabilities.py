"""Tests for deterministic AST-agent provider compatibility evaluation."""

from __future__ import annotations

import pytest

from ruleatlas_ai.providers import (
    AstAgentCapabilityRequirements,
    AstAgentModelCapabilities,
    CapabilityIssueCode,
    CapabilitySupport,
    ModelCostMetadata,
    ModelExecutionLocation,
    ParallelToolCallPolicy,
    StructuredOutputMode,
    capabilities_from_discovered_model,
    evaluate_ast_agent_capabilities,
)
from ruleatlas_ai.providers.protocols import DiscoveredModel


def _capabilities(
    **overrides: object,
) -> AstAgentModelCapabilities:
    values: dict[str, object] = {
        "provider_key": "provider-1",
        "model_id": "model-1",
        "structured_output": StructuredOutputMode.JSON_SCHEMA,
        "tool_calling": CapabilitySupport.SUPPORTED,
        "parallel_tool_calling": CapabilitySupport.UNKNOWN,
        "context_window": 128_000,
        "maximum_output_tokens": 8_000,
        "deterministic_temperature": CapabilitySupport.SUPPORTED,
        "streaming": CapabilitySupport.SUPPORTED,
        "execution_location": ModelExecutionLocation.REMOTE,
        "cost": ModelCostMetadata(1.0, 4.0),
    }
    values.update(overrides)
    return AstAgentModelCapabilities(**values)  # type: ignore[arg-type]


def _codes(
    result_blockers: tuple[object, ...],
) -> set[CapabilityIssueCode]:
    return {item.code for item in result_blockers}  # type: ignore[attr-defined]


def test_compatible_model_passes_default_requirements() -> None:
    result = evaluate_ast_agent_capabilities(
        _capabilities(),
        AstAgentCapabilityRequirements(),
    )

    assert result.compatible
    assert result.blockers == ()
    assert result.to_dict()["compatible"] is True


def test_required_capabilities_must_be_explicitly_supported() -> None:
    result = evaluate_ast_agent_capabilities(
        _capabilities(
            tool_calling=CapabilitySupport.UNKNOWN,
            deterministic_temperature=CapabilitySupport.UNSUPPORTED,
        ),
        AstAgentCapabilityRequirements(),
    )

    codes = _codes(result.blockers)
    assert CapabilityIssueCode.TOOL_CALLING in codes
    assert CapabilityIssueCode.DETERMINISTIC_TEMPERATURE in codes
    assert not result.compatible


def test_structured_context_output_and_streaming_requirements_are_enforced() -> None:
    result = evaluate_ast_agent_capabilities(
        _capabilities(
            structured_output=StructuredOutputMode.JSON_OBJECT,
            context_window=8_000,
            maximum_output_tokens=None,
            streaming=CapabilitySupport.UNKNOWN,
        ),
        AstAgentCapabilityRequirements(require_streaming=True),
    )

    codes = _codes(result.blockers)
    assert CapabilityIssueCode.STRUCTURED_OUTPUT in codes
    assert CapabilityIssueCode.CONTEXT_WINDOW in codes
    assert CapabilityIssueCode.OUTPUT_TOKENS in codes
    assert CapabilityIssueCode.STREAMING in codes


def test_parallel_tool_calls_are_checked_only_when_required() -> None:
    unknown_parallel = _capabilities(parallel_tool_calling=CapabilitySupport.UNKNOWN)

    default_result = evaluate_ast_agent_capabilities(
        unknown_parallel,
        AstAgentCapabilityRequirements(),
    )
    required_result = evaluate_ast_agent_capabilities(
        unknown_parallel,
        AstAgentCapabilityRequirements(parallel_tool_calls=ParallelToolCallPolicy.REQUIRED),
    )

    assert CapabilityIssueCode.PARALLEL_TOOL_CALLING not in _codes(default_result.blockers)
    assert CapabilityIssueCode.PARALLEL_TOOL_CALLING in _codes(required_result.blockers)


def test_local_only_governance_blocks_remote_models() -> None:
    result = evaluate_ast_agent_capabilities(
        _capabilities(execution_location=ModelExecutionLocation.REMOTE),
        AstAgentCapabilityRequirements(allowed_execution_locations=frozenset({ModelExecutionLocation.LOCAL})),
    )

    assert CapabilityIssueCode.EXECUTION_LOCATION in _codes(result.blockers)


def test_cost_thresholds_unknown_cost_and_currency_are_handled_truthfully() -> None:
    expensive = evaluate_ast_agent_capabilities(
        _capabilities(cost=ModelCostMetadata(3.0, 12.0)),
        AstAgentCapabilityRequirements(
            maximum_input_cost_per_million_tokens=2.0,
            maximum_output_cost_per_million_tokens=10.0,
        ),
    )
    unknown = evaluate_ast_agent_capabilities(
        _capabilities(cost=ModelCostMetadata()),
        AstAgentCapabilityRequirements(
            maximum_input_cost_per_million_tokens=2.0,
        ),
    )
    wrong_currency = evaluate_ast_agent_capabilities(
        _capabilities(cost=ModelCostMetadata(1.0, 4.0, currency="EUR")),
        AstAgentCapabilityRequirements(cost_currency="USD"),
    )

    assert {
        CapabilityIssueCode.INPUT_COST,
        CapabilityIssueCode.OUTPUT_COST,
    } <= _codes(expensive.blockers)
    assert CapabilityIssueCode.COST_UNKNOWN in _codes(unknown.warnings)
    assert CapabilityIssueCode.COST_CURRENCY in _codes(wrong_currency.blockers)


def test_known_cost_can_be_required_even_without_a_maximum() -> None:
    result = evaluate_ast_agent_capabilities(
        _capabilities(cost=ModelCostMetadata()),
        AstAgentCapabilityRequirements(require_known_cost=True),
    )

    assert CapabilityIssueCode.COST_UNKNOWN in _codes(result.blockers)


def test_discovered_model_is_normalized_without_inventing_unprobed_capabilities() -> None:
    discovered = DiscoveredModel(
        provider_model_id="model-1",
        display_name="Model 1",
        context_window=64_000,
        maximum_output_tokens=4_000,
        supports_tool_calling=True,
        supports_structured_output=True,
        supports_json_schema=False,
        supports_streaming=True,
    )

    normalized = capabilities_from_discovered_model(
        discovered,
        provider_key="provider-1",
        execution_location=ModelExecutionLocation.LOCAL,
    )

    assert normalized.structured_output == StructuredOutputMode.JSON_OBJECT
    assert normalized.tool_calling == CapabilitySupport.SUPPORTED
    assert normalized.parallel_tool_calling == CapabilitySupport.UNKNOWN
    assert normalized.deterministic_temperature == CapabilitySupport.UNKNOWN


def test_invalid_capability_and_requirement_values_are_rejected() -> None:
    with pytest.raises(ValueError, match="context_window must be positive"):
        _capabilities(context_window=0)
    with pytest.raises(ValueError, match="must not be empty"):
        AstAgentCapabilityRequirements(allowed_execution_locations=frozenset())
    with pytest.raises(ValueError, match="must be non-negative"):
        ModelCostMetadata(input_cost_per_million_tokens=-1)
