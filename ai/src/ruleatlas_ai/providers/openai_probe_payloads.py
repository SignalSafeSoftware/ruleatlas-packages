"""Probe schema validation, model heuristics, and request-payload builders for the OpenAI compatibility
probe. Extracted from ``openai_compatibility_probe`` (god-module split) so the probe runners stay focused.
"""

from __future__ import annotations

from typing import Any

from ruleatlas_contracts.enums import AICapabilityProbeStatus

COMPATIBILITY_TEST_VERSION = "2.1.1"
STRUCTURED_PROBE_SCHEMA_VERSION = "status-ok-v1"
ADAPTER_VERSION = "openai-httpx-2.1.1"
STRUCTURED_PROBE_VALIDATION_MSG = (
    "The structured-output probe returned a payload RuleAtlas could not validate."
)

_UNKNOWN = AICapabilityProbeStatus.UNKNOWN.value
_SUPPORTED = AICapabilityProbeStatus.SUPPORTED.value
_UNSUPPORTED = AICapabilityProbeStatus.UNSUPPORTED.value

# Minimal deterministic structured-output schema (not RuleAtlas business data).
STRUCTURED_PROBE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["ok"],
        }
    },
    "required": ["status"],
    "additionalProperties": False,
}

_UNSUPPORTED_SCHEMA_KEYWORDS = frozenset(
    {
        "patternProperties",
        "unevaluatedProperties",
        "unevaluatedItems",
        "$ref",
        "$dynamicRef",
        "not",
        "if",
        "then",
        "else",
    }
)


def unknown_capability_probe() -> dict[str, str]:
    return {
        "text_generation": _UNKNOWN,
        "structured_output": _UNKNOWN,
        "json_schema": _UNKNOWN,
        "tool_calling": _UNKNOWN,
        "responses_api": _UNKNOWN,
    }


def validate_structured_probe_schema(schema: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate the probe schema locally before calling OpenAI."""
    candidate = dict(schema or STRUCTURED_PROBE_SCHEMA)
    if candidate.get("type") != "object":
        raise ValueError("Probe schema type must be object")
    if candidate.get("additionalProperties") is not False:
        raise ValueError("Probe schema must set additionalProperties=false")
    props = candidate.get("properties")
    if not isinstance(props, dict) or "status" not in props:
        raise ValueError("Probe schema must define properties.status")
    required = candidate.get("required")
    if not isinstance(required, list) or "status" not in required:
        raise ValueError("Probe schema required must include status")
    status = props.get("status")
    if not isinstance(status, dict) or status.get("type") != "string":
        raise ValueError("Probe schema status must be a string")
    if status.get("enum") != ["ok"]:
        raise ValueError("Probe schema status enum must be ['ok']")

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in _UNSUPPORTED_SCHEMA_KEYWORDS:
                    raise ValueError(f"Unsupported JSON Schema keyword for strict probe: {key}")
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(candidate)
    return candidate


def _uses_responses_api(model_id: str) -> bool:
    mid = model_id.lower()
    return mid.startswith(("gpt-5", "o1", "o3", "o4"))


def _is_reasoning_model(model_id: str) -> bool:
    return _uses_responses_api(model_id)


def _structured_max_output_tokens(model_id: str) -> int:
    # Reasoning models consume output budget for hidden reasoning before JSON.
    # 64 is too low and commonly yields incomplete / unparseable probes.
    return 1024 if _is_reasoning_model(model_id) else 256


def _tool_max_output_tokens(model_id: str) -> int:
    return 512 if _is_reasoning_model(model_id) else 128


def build_responses_structured_payload(*, model_id: str, schema: dict[str, Any] | None = None) -> dict[str, Any]:
    validated = validate_structured_probe_schema(schema)
    payload: dict[str, Any] = {
        "model": model_id,
        "input": 'Return a JSON object with status set to "ok".',
        "text": {
            "format": {
                "type": "json_schema",
                "name": "ruleatlas_structured_probe",
                "strict": True,
                "schema": validated,
            }
        },
        "max_output_tokens": _structured_max_output_tokens(model_id),
        "store": False,
    }
    if _is_reasoning_model(model_id):
        # gpt-5.6-terra rejects "minimal"; supported: none|low|medium|high|xhigh.
        payload["reasoning"] = {"effort": "none"}
    return payload


def build_chat_structured_payload(*, model_id: str, schema: dict[str, Any] | None = None) -> dict[str, Any]:
    validated = validate_structured_probe_schema(schema)
    payload: dict[str, Any] = {
        "model": model_id,
        "messages": [
            {
                "role": "user",
                "content": 'Return a JSON object with status set to "ok".',
            }
        ],
        "max_tokens": _structured_max_output_tokens(model_id),
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "ruleatlas_structured_probe",
                "strict": True,
                "schema": validated,
            },
        },
    }
    if not _is_reasoning_model(model_id):
        payload["temperature"] = 0
    return payload
