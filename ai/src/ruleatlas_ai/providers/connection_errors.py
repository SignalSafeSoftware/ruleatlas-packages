"""Shared errors + result types for AI provider connection services (RA-17-001).

Extracted from the former ``connection_service`` god module so credential-storage, field-update, and CRUD
collaborators can share these types without importing the large service module (avoids an import cycle).
"""

from __future__ import annotations

from typing import TypedDict


class ConnectionError(ValueError):
    pass


class VaultUnavailableError(RuntimeError):
    """Encrypted credential storage is not available in this deployment."""


class SecretStoreUnavailableError(RuntimeError):
    """Organization secret store (SSM) is not available in this deployment."""


class ConnectionTestResult(TypedDict):
    ok: bool
    status: str
    message: str
    latency_ms: float | None
