"""Provider-neutral capability requirements for AST investigation models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from ruleatlas_ai.providers.protocols import DiscoveredModel


class CapabilitySupport(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


class StructuredOutputMode(StrEnum):
    NONE = "none"
    JSON_OBJECT = "json_object"
    JSON_SCHEMA = "json_schema"


class ModelExecutionLocation(StrEnum):
    LOCAL = "local"
    REMOTE = "remote"


class ParallelToolCallPolicy(StrEnum):
    FORBIDDEN = "forbidden"
    ALLOWED = "allowed"
    REQUIRED = "required"


class CapabilityIssueCode(StrEnum):
    STRUCTURED_OUTPUT = "structured_output"
    TOOL_CALLING = "tool_calling"
    PARALLEL_TOOL_CALLING = "parallel_tool_calling"
    CONTEXT_WINDOW = "context_window"
    OUTPUT_TOKENS = "output_tokens"
    DETERMINISTIC_TEMPERATURE = "deterministic_temperature"
    STREAMING = "streaming"
    EXECUTION_LOCATION = "execution_location"
    INPUT_COST = "input_cost"
    OUTPUT_COST = "output_cost"
    COST_CURRENCY = "cost_currency"
    COST_UNKNOWN = "cost_unknown"


@dataclass(frozen=True)
class ModelCostMetadata:
    input_cost_per_million_tokens: float | None = None
    output_cost_per_million_tokens: float | None = None
    currency: str = "USD"
    estimated: bool = True

    def __post_init__(self) -> None:
        for field_name, value in {
            "input_cost_per_million_tokens": self.input_cost_per_million_tokens,
            "output_cost_per_million_tokens": self.output_cost_per_million_tokens,
        }.items():
            if value is not None and value < 0:
                raise ValueError(f"{field_name} must be non-negative")
        if not self.currency.strip():
            raise ValueError("currency must not be blank")

    def to_dict(self) -> dict[str, object]:
        return {
            "input_cost_per_million_tokens": self.input_cost_per_million_tokens,
            "output_cost_per_million_tokens": self.output_cost_per_million_tokens,
            "currency": self.currency,
            "estimated": self.estimated,
        }


@dataclass(frozen=True)
class AstAgentModelCapabilities:
    provider_key: str
    model_id: str
    structured_output: StructuredOutputMode
    tool_calling: CapabilitySupport
    parallel_tool_calling: CapabilitySupport
    context_window: int | None
    maximum_output_tokens: int | None
    deterministic_temperature: CapabilitySupport
    streaming: CapabilitySupport
    execution_location: ModelExecutionLocation
    cost: ModelCostMetadata = field(default_factory=ModelCostMetadata)

    def __post_init__(self) -> None:
        if not self.provider_key.strip():
            raise ValueError("provider_key must not be blank")
        if not self.model_id.strip():
            raise ValueError("model_id must not be blank")
        if self.context_window is not None and self.context_window <= 0:
            raise ValueError("context_window must be positive")
        if self.maximum_output_tokens is not None and self.maximum_output_tokens <= 0:
            raise ValueError("maximum_output_tokens must be positive")

    def to_dict(self) -> dict[str, object]:
        return {
            "provider_key": self.provider_key,
            "model_id": self.model_id,
            "structured_output": self.structured_output.value,
            "tool_calling": self.tool_calling.value,
            "parallel_tool_calling": self.parallel_tool_calling.value,
            "context_window": self.context_window,
            "maximum_output_tokens": self.maximum_output_tokens,
            "deterministic_temperature": self.deterministic_temperature.value,
            "streaming": self.streaming.value,
            "execution_location": self.execution_location.value,
            "cost": self.cost.to_dict(),
        }


@dataclass(frozen=True)
class AstAgentCapabilityRequirements:
    minimum_structured_output: StructuredOutputMode = StructuredOutputMode.JSON_SCHEMA
    require_tool_calling: bool = True
    parallel_tool_calls: ParallelToolCallPolicy = ParallelToolCallPolicy.FORBIDDEN
    minimum_context_window: int = 32_000
    minimum_output_tokens: int = 2_000
    require_deterministic_temperature: bool = True
    require_streaming: bool = False
    allowed_execution_locations: frozenset[ModelExecutionLocation] = field(
        default_factory=lambda: frozenset(ModelExecutionLocation)
    )
    maximum_input_cost_per_million_tokens: float | None = None
    maximum_output_cost_per_million_tokens: float | None = None
    cost_currency: str = "USD"
    require_known_cost: bool = False

    def __post_init__(self) -> None:
        if self.minimum_structured_output == StructuredOutputMode.NONE:
            raise ValueError("AST agents require at least JSON object output")
        if self.minimum_context_window <= 0:
            raise ValueError("minimum_context_window must be positive")
        if self.minimum_output_tokens <= 0:
            raise ValueError("minimum_output_tokens must be positive")
        if not self.allowed_execution_locations:
            raise ValueError("allowed_execution_locations must not be empty")
        if not self.cost_currency.strip():
            raise ValueError("cost_currency must not be blank")
        for field_name, value in {
            "maximum_input_cost_per_million_tokens": self.maximum_input_cost_per_million_tokens,
            "maximum_output_cost_per_million_tokens": self.maximum_output_cost_per_million_tokens,
        }.items():
            if value is not None and value < 0:
                raise ValueError(f"{field_name} must be non-negative")

    def to_dict(self) -> dict[str, object]:
        return {
            "minimum_structured_output": self.minimum_structured_output.value,
            "require_tool_calling": self.require_tool_calling,
            "parallel_tool_calls": self.parallel_tool_calls.value,
            "minimum_context_window": self.minimum_context_window,
            "minimum_output_tokens": self.minimum_output_tokens,
            "require_deterministic_temperature": self.require_deterministic_temperature,
            "require_streaming": self.require_streaming,
            "allowed_execution_locations": sorted(value.value for value in self.allowed_execution_locations),
            "maximum_input_cost_per_million_tokens": self.maximum_input_cost_per_million_tokens,
            "maximum_output_cost_per_million_tokens": self.maximum_output_cost_per_million_tokens,
            "cost_currency": self.cost_currency,
            "require_known_cost": self.require_known_cost,
        }


@dataclass(frozen=True)
class CapabilityIssue:
    code: CapabilityIssueCode
    message: str
    actual: str | int | float | None
    required: str | int | float | None

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code.value,
            "message": self.message,
            "actual": self.actual,
            "required": self.required,
        }


@dataclass(frozen=True)
class AstAgentCompatibilityResult:
    blockers: tuple[CapabilityIssue, ...] = field(default_factory=tuple)
    warnings: tuple[CapabilityIssue, ...] = field(default_factory=tuple)

    @property
    def compatible(self) -> bool:
        return not self.blockers

    def to_dict(self) -> dict[str, object]:
        return {
            "compatible": self.compatible,
            "blockers": [issue.to_dict() for issue in self.blockers],
            "warnings": [issue.to_dict() for issue in self.warnings],
        }


def evaluate_ast_agent_capabilities(
    capabilities: AstAgentModelCapabilities,
    requirements: AstAgentCapabilityRequirements,
) -> AstAgentCompatibilityResult:
    blockers: list[CapabilityIssue] = []
    warnings: list[CapabilityIssue] = []
    _check_structured_output(capabilities, requirements, blockers)
    _check_support(
        capabilities.tool_calling,
        required=requirements.require_tool_calling,
        code=CapabilityIssueCode.TOOL_CALLING,
        label="tool calling",
        blockers=blockers,
    )
    if requirements.parallel_tool_calls == ParallelToolCallPolicy.REQUIRED:
        _check_support(
            capabilities.parallel_tool_calling,
            required=True,
            code=CapabilityIssueCode.PARALLEL_TOOL_CALLING,
            label="parallel tool calling",
            blockers=blockers,
        )
    _check_numeric_minimum(
        capabilities.context_window,
        requirements.minimum_context_window,
        CapabilityIssueCode.CONTEXT_WINDOW,
        "context window",
        blockers,
    )
    _check_numeric_minimum(
        capabilities.maximum_output_tokens,
        requirements.minimum_output_tokens,
        CapabilityIssueCode.OUTPUT_TOKENS,
        "maximum output tokens",
        blockers,
    )
    _check_support(
        capabilities.deterministic_temperature,
        required=requirements.require_deterministic_temperature,
        code=CapabilityIssueCode.DETERMINISTIC_TEMPERATURE,
        label="deterministic temperature",
        blockers=blockers,
    )
    _check_support(
        capabilities.streaming,
        required=requirements.require_streaming,
        code=CapabilityIssueCode.STREAMING,
        label="streaming",
        blockers=blockers,
    )
    if capabilities.execution_location not in requirements.allowed_execution_locations:
        blockers.append(
            CapabilityIssue(
                CapabilityIssueCode.EXECUTION_LOCATION,
                "model execution location is forbidden by governance",
                capabilities.execution_location.value,
                ",".join(sorted(value.value for value in requirements.allowed_execution_locations)),
            )
        )
    _check_costs(capabilities.cost, requirements, blockers, warnings)
    return AstAgentCompatibilityResult(tuple(blockers), tuple(warnings))


def capabilities_from_discovered_model(
    model: DiscoveredModel,
    *,
    provider_key: str,
    execution_location: ModelExecutionLocation,
    parallel_tool_calling: CapabilitySupport = CapabilitySupport.UNKNOWN,
    deterministic_temperature: CapabilitySupport = CapabilitySupport.UNKNOWN,
    cost: ModelCostMetadata | None = None,
) -> AstAgentModelCapabilities:
    structured_output = StructuredOutputMode.NONE
    if model.supports_json_schema:
        structured_output = StructuredOutputMode.JSON_SCHEMA
    elif model.supports_structured_output:
        structured_output = StructuredOutputMode.JSON_OBJECT
    return AstAgentModelCapabilities(
        provider_key=provider_key,
        model_id=model.provider_model_id,
        structured_output=structured_output,
        tool_calling=_support(model.supports_tool_calling),
        parallel_tool_calling=parallel_tool_calling,
        context_window=model.context_window,
        maximum_output_tokens=model.maximum_output_tokens,
        deterministic_temperature=deterministic_temperature,
        streaming=_support(model.supports_streaming),
        execution_location=execution_location,
        cost=cost or ModelCostMetadata(),
    )


def _support(value: bool) -> CapabilitySupport:
    return CapabilitySupport.SUPPORTED if value else CapabilitySupport.UNSUPPORTED


def _check_structured_output(
    capabilities: AstAgentModelCapabilities,
    requirements: AstAgentCapabilityRequirements,
    blockers: list[CapabilityIssue],
) -> None:
    rank = {
        StructuredOutputMode.NONE: 0,
        StructuredOutputMode.JSON_OBJECT: 1,
        StructuredOutputMode.JSON_SCHEMA: 2,
    }
    if rank[capabilities.structured_output] < rank[requirements.minimum_structured_output]:
        blockers.append(
            CapabilityIssue(
                CapabilityIssueCode.STRUCTURED_OUTPUT,
                "structured output capability is below the required mode",
                capabilities.structured_output.value,
                requirements.minimum_structured_output.value,
            )
        )


def _check_support(
    actual: CapabilitySupport,
    *,
    required: bool,
    code: CapabilityIssueCode,
    label: str,
    blockers: list[CapabilityIssue],
) -> None:
    if required and actual != CapabilitySupport.SUPPORTED:
        blockers.append(
            CapabilityIssue(
                code,
                f"{label} must be explicitly supported",
                actual.value,
                CapabilitySupport.SUPPORTED.value,
            )
        )


def _check_numeric_minimum(
    actual: int | None,
    required: int,
    code: CapabilityIssueCode,
    label: str,
    blockers: list[CapabilityIssue],
) -> None:
    if actual is None or actual < required:
        blockers.append(
            CapabilityIssue(
                code,
                f"{label} is unknown or below the required minimum",
                actual,
                required,
            )
        )


def _check_costs(
    cost: ModelCostMetadata,
    requirements: AstAgentCapabilityRequirements,
    blockers: list[CapabilityIssue],
    warnings: list[CapabilityIssue],
) -> None:
    has_comparable_cost = (
        cost.input_cost_per_million_tokens is not None or cost.output_cost_per_million_tokens is not None
    )
    if has_comparable_cost and cost.currency != requirements.cost_currency:
        blockers.append(
            CapabilityIssue(
                CapabilityIssueCode.COST_CURRENCY,
                "model cost currency does not match the requirement currency",
                cost.currency,
                requirements.cost_currency,
            )
        )
        return
    pairs = (
        (
            cost.input_cost_per_million_tokens,
            requirements.maximum_input_cost_per_million_tokens,
            CapabilityIssueCode.INPUT_COST,
            "input token cost",
        ),
        (
            cost.output_cost_per_million_tokens,
            requirements.maximum_output_cost_per_million_tokens,
            CapabilityIssueCode.OUTPUT_COST,
            "output token cost",
        ),
    )
    for actual, maximum, code, label in pairs:
        if actual is None:
            if requirements.require_known_cost:
                blockers.append(
                    CapabilityIssue(
                        CapabilityIssueCode.COST_UNKNOWN,
                        f"{label} must be known",
                        None,
                        maximum,
                    )
                )
            elif maximum is not None:
                warnings.append(
                    CapabilityIssue(
                        CapabilityIssueCode.COST_UNKNOWN,
                        f"{label} is unknown; configured maximum cannot be verified",
                        None,
                        maximum,
                    )
                )
        elif maximum is not None and actual > maximum:
            blockers.append(
                CapabilityIssue(
                    code,
                    f"{label} exceeds the configured maximum",
                    actual,
                    maximum,
                )
            )


__all__ = [
    "AstAgentCapabilityRequirements",
    "AstAgentCompatibilityResult",
    "AstAgentModelCapabilities",
    "CapabilityIssue",
    "CapabilityIssueCode",
    "CapabilitySupport",
    "ModelCostMetadata",
    "ModelExecutionLocation",
    "ParallelToolCallPolicy",
    "StructuredOutputMode",
    "capabilities_from_discovered_model",
    "evaluate_ast_agent_capabilities",
]
