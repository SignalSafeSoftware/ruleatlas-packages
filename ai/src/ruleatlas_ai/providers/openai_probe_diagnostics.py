"""Diagnostic + result builders and HTTP-error classification for the OpenAI compatibility probe.

Extracted from ``openai_compatibility_probe`` (god-module split). These build ``CompatibilityTestResult``
values for the various failure/unsupported paths and classify provider HTTP errors.
"""

from __future__ import annotations

from typing import Any

from ruleatlas_contracts.enums import (
    AICompatibilityFailureCategory,
    AIModelAvailabilityStatus,
    AIModelCompatibilityStatus,
)

from ruleatlas_ai.providers.openai_probe_payloads import (
    _UNKNOWN,
    _UNSUPPORTED,
    ADAPTER_VERSION,
    COMPATIBILITY_TEST_VERSION,
    STRUCTURED_PROBE_SCHEMA_VERSION,
    unknown_capability_probe,
)
from ruleatlas_ai.providers.openai_probe_sanitization import sanitize_provider_error
from ruleatlas_ai.providers.protocols import CompatibilityTestResult


def _base_diagnostics(*, endpoint: str, http_status: int | None = None) -> dict[str, Any]:
    return {
        "endpoint": endpoint,
        "adapter_version": ADAPTER_VERSION,
        "probe_version": COMPATIBILITY_TEST_VERSION,
        "schema_version": STRUCTURED_PROBE_SCHEMA_VERSION,
        "http_status": http_status,
    }


def _infra_unavailable(
    *,
    category: str,
    detail: str,
    latency_ms: int,
    diagnostics: dict[str, Any] | None = None,
    availability_status: str | None = None,
) -> CompatibilityTestResult:
    return CompatibilityTestResult(
        ok=False,
        compatibility_status=AIModelCompatibilityStatus.TEST_UNAVAILABLE.value,
        failure_category=category,
        sanitized_detail=detail,
        latency_ms=latency_ms,
        capability_probe=unknown_capability_probe(),
        availability_status=availability_status,
        sanitized_diagnostics=dict(diagnostics or {}),
    )


def _test_failed(
    *,
    category: str,
    detail: str,
    latency_ms: int,
    probe: dict[str, str] | None = None,
    diagnostics: dict[str, Any] | None = None,
    token_usage: dict[str, Any] | None = None,
) -> CompatibilityTestResult:
    capability = dict(probe or unknown_capability_probe())
    # Parse/schema failures never claim Unsupported.
    for key in ("structured_output", "json_schema", "tool_calling", "text_generation"):
        if capability.get(key) == _UNSUPPORTED:
            capability[key] = _UNKNOWN
    return CompatibilityTestResult(
        ok=False,
        compatibility_status=AIModelCompatibilityStatus.TEST_FAILED.value,
        failure_category=category,
        sanitized_detail=detail,
        latency_ms=latency_ms,
        token_usage=dict(token_usage or {}),
        capability_probe=capability,
        sanitized_diagnostics=dict(diagnostics or {}),
    )


def _explicit_unsupported(
    *,
    category: str,
    detail: str,
    latency_ms: int,
    diagnostics: dict[str, Any] | None = None,
) -> CompatibilityTestResult:
    probe = unknown_capability_probe()
    probe["structured_output"] = _UNSUPPORTED
    probe["json_schema"] = _UNSUPPORTED
    return CompatibilityTestResult(
        ok=False,
        compatibility_status=AIModelCompatibilityStatus.INCOMPATIBLE.value,
        failure_category=category,
        sanitized_detail=detail,
        latency_ms=latency_ms,
        capability_probe=probe,
        sanitized_diagnostics=dict(diagnostics or {}),
    )


def _classify_http_error_body(
    *,
    status_code: int,
    body: dict[str, Any] | None,
    latency_ms: int,
    diagnostics: dict[str, Any],
) -> tuple[CompatibilityTestResult | None, dict[str, Any]]:
    diagnostics = {
        **diagnostics,
        "http_status": status_code,
        **sanitize_provider_error(body),
    }
    if status_code == 401:
        return _infra_unavailable(
            category=AICompatibilityFailureCategory.CREDENTIAL_UNAVAILABLE.value,
            detail="Credential unavailable or rejected by provider",
            latency_ms=latency_ms,
            diagnostics=diagnostics,
        ), diagnostics
    if status_code == 403:
        return _infra_unavailable(
            category=AICompatibilityFailureCategory.MODEL_ACCESS_DENIED.value,
            detail="Organization connection may not have access to this model",
            latency_ms=latency_ms,
            diagnostics=diagnostics,
            availability_status=AIModelAvailabilityStatus.UNAVAILABLE_FOR_CONNECTION.value,
        ), diagnostics
    if status_code == 404:
        return _infra_unavailable(
            category=AICompatibilityFailureCategory.MODEL_ACCESS_DENIED.value,
            detail="Model unavailable for this organization connection",
            latency_ms=latency_ms,
            diagnostics=diagnostics,
            availability_status=AIModelAvailabilityStatus.UNAVAILABLE_FOR_CONNECTION.value,
        ), diagnostics
    if status_code == 429:
        return _infra_unavailable(
            category=AICompatibilityFailureCategory.RATE_LIMITED.value,
            detail="Provider rate limited the request",
            latency_ms=latency_ms,
            diagnostics=diagnostics,
        ), diagnostics
    if status_code >= 500:
        return _infra_unavailable(
            category=AICompatibilityFailureCategory.PROVIDER_UNAVAILABLE.value,
            detail="Provider connection unavailable",
            latency_ms=latency_ms,
            diagnostics=diagnostics,
        ), diagnostics

    message = str(diagnostics.get("provider_error_summary") or "").lower()
    code = str(diagnostics.get("provider_error_code") or "").lower()
    param = str(diagnostics.get("provider_error_param") or "").lower()

    # Adapter/probe request mistakes (e.g. invalid reasoning.effort) are test_failed,
    # not structured-output Unsupported.
    if param.startswith("reasoning") or "reasoning.effort" in message:
        return _test_failed(
            category=AICompatibilityFailureCategory.UNSUPPORTED_PARAMETER.value,
            detail="Structured-output probe request used an unsupported parameter for this model",
            latency_ms=latency_ms,
            diagnostics={
                **diagnostics,
                "validation_error_category": "malformed_probe_request",
            },
        ), diagnostics

    format_related = any(
        token in message or token in param
        for token in (
            "response_format",
            "json_schema",
            "text.format",
            "text/format",
            "structured output",
            "structured_output",
        )
    )
    unsupported_language = any(
        marker in message
        for marker in (
            "unsupported",
            "not supported",
            "unknown parameter",
            "invalid parameter",
            "does not support",
        )
    ) or "unsupported" in code
    if unsupported_language and format_related:
        if "schema" in message or "json_schema" in message or "format" in param:
            return _explicit_unsupported(
                category=AICompatibilityFailureCategory.PROVIDER_REJECTED_SCHEMA.value,
                detail="Provider rejected the structured-output schema or format",
                latency_ms=latency_ms,
                diagnostics=diagnostics,
            ), diagnostics
        return _explicit_unsupported(
            category=AICompatibilityFailureCategory.UNSUPPORTED_RESPONSE_FORMAT.value,
            detail="Provider explicitly rejected structured-output formatting",
            latency_ms=latency_ms,
            diagnostics=diagnostics,
        ), diagnostics
    return None, diagnostics
