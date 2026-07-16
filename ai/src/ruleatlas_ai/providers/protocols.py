"""Provider-neutral protocols for AI connections and model discovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class DiscoveredModel:
    provider_model_id: str
    display_name: str
    description: str | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)
    context_window: int | None = None
    maximum_output_tokens: int | None = None
    supports_text_input: bool = True
    supports_text_output: bool = True
    supports_tool_calling: bool = False
    supports_structured_output: bool = False
    supports_json_schema: bool = False
    supports_reasoning: bool = False
    supports_streaming: bool = False
    supports_embeddings: bool = False
    supports_image_input: bool = False
    lifecycle_status: str = "unknown"


@dataclass(frozen=True)
class HealthCheckResult:
    ok: bool
    status: str
    message: str
    latency_ms: int | None = None


@dataclass(frozen=True)
class CompatibilityTestResult:
    ok: bool
    compatibility_status: str
    failure_category: str | None = None
    sanitized_detail: str | None = None
    latency_ms: int | None = None
    token_usage: dict[str, Any] = field(default_factory=dict)
    estimated_cost: float | None = None
    # Explicit probe results: supported | unsupported | unknown (never infer from discovery alone)
    capability_probe: dict[str, str] = field(default_factory=dict)
    # Optional availability update when the model is inaccessible for this connection
    availability_status: str | None = None
    # Safe operator diagnostics (never includes secrets or raw response bodies)
    sanitized_diagnostics: dict[str, Any] = field(default_factory=dict)


class AISecretResolver(Protocol):
    def resolve_secret(
        self,
        *,
        credential_source: str,
        environment_variable_name: str | None,
        encrypted_credential_reference: str | None,
        organization_id: str,
    ) -> str | None: ...

    def credential_present(
        self,
        *,
        credential_source: str,
        environment_variable_name: str | None,
        encrypted_credential_reference: str | None,
        organization_id: str,
    ) -> bool: ...


class AIProviderHealthChecker(Protocol):
    def test_connection(self, *, api_key: str | None, base_url: str | None) -> HealthCheckResult: ...


class AIModelDiscoveryProvider(Protocol):
    def list_models(self, *, api_key: str | None, base_url: str | None) -> list[DiscoveredModel]: ...


class AIModelCompatibilityTester(Protocol):
    def test_model_compatibility(
        self,
        *,
        api_key: str | None,
        base_url: str | None,
        model_id: str,
    ) -> CompatibilityTestResult: ...


class AIProviderAdapter(Protocol):
    provider_type: str
    implemented: bool

    def test_connection(self, *, api_key: str | None, base_url: str | None) -> HealthCheckResult: ...

    def list_models(self, *, api_key: str | None, base_url: str | None) -> list[DiscoveredModel]: ...

    def test_model_compatibility(
        self,
        *,
        api_key: str | None,
        base_url: str | None,
        model_id: str,
    ) -> CompatibilityTestResult: ...
