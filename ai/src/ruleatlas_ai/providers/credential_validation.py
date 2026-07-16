"""Credential-source validation and secret-safe helpers for AI provider connections."""

from __future__ import annotations

import re
from typing import Final

from ruleatlas_contracts.enums import AICredentialSource

# Canonical production-ready sources for OpenAI in this release.
OPENAI_READY_CREDENTIAL_SOURCES: Final[frozenset[str]] = frozenset(
    {
        AICredentialSource.SSM_SECURE_STRING.value,
        AICredentialSource.ENCRYPTED_ORGANIZATION_SECRET.value,
        AICredentialSource.ENVIRONMENT_VARIABLE.value,
    }
)

_ORG_MANAGED_SOURCES: Final[frozenset[str]] = frozenset(
    {
        AICredentialSource.SSM_SECURE_STRING.value,
        AICredentialSource.ENCRYPTED_ORGANIZATION_SECRET.value,
        AICredentialSource.ENCRYPTED_SECRET.value,
        "vault",
    }
)

_ENV_VAR_NAME_RE = re.compile(r"^[A-Za-z_]\w*$", re.ASCII)

# Prefixes that look like pasted secrets, not environment variable names.
_SECRET_LIKE_PREFIXES: Final[tuple[str, ...]] = (
    "sk-",
    "sk-proj-",
    "AIza",
    "xox",
    "ghp_",
    "github_pat_",
    "glpat-",
    "AKIA",
)

_SECRET_FIELD_NAMES: Final[frozenset[str]] = frozenset(
    {
        "api_key",
        "token",
        "secret",
        "credential",
        "authorization",
        "secret_string",
        "parameter_value",
        "encrypted_secret",
        "password",
    }
)


class CredentialValidationError(ValueError):
    """Controlled validation error — must never include secret material."""


def normalize_credential_source(raw: str | None) -> str:
    """Map legacy and canonical credential_source strings to canonical values."""
    value = (raw or "").strip().lower()
    if value in {
        AICredentialSource.SSM_SECURE_STRING.value,
        "ssm",
        "secure_string",
        "encrypted_organization_secret_ssm",
    }:
        return AICredentialSource.SSM_SECURE_STRING.value
    if value in {
        AICredentialSource.ENCRYPTED_SECRET.value,
        "encrypted_organization_secret",
        "vault",
    }:
        return AICredentialSource.ENCRYPTED_ORGANIZATION_SECRET.value
    if value in {
        AICredentialSource.ENVIRONMENT.value,
        "environment_variable",
        "env",
    }:
        return AICredentialSource.ENVIRONMENT_VARIABLE.value
    if value == AICredentialSource.MANAGED_IDENTITY.value:
        return AICredentialSource.MANAGED_IDENTITY.value
    if value == AICredentialSource.NONE.value:
        return AICredentialSource.NONE.value
    if not value:
        raise CredentialValidationError("credential_source is required")
    raise CredentialValidationError(f"Unsupported credential source: {value}")


def is_organization_managed_secret(source: str | None) -> bool:
    """True for SSM SecureString or legacy Fernet vault sources."""
    try:
        canonical = normalize_credential_source(source)
    except CredentialValidationError:
        return (source or "").strip().lower() in _ORG_MANAGED_SOURCES
    return canonical in {
        AICredentialSource.SSM_SECURE_STRING.value,
        AICredentialSource.ENCRYPTED_ORGANIZATION_SECRET.value,
    }


def is_encrypted_organization_secret(source: str | None) -> bool:
    """Backward-compatible alias — includes SSM and Fernet org-managed secrets."""
    return is_organization_managed_secret(source)


def is_ssm_secure_string_source(source: str | None) -> bool:
    try:
        return normalize_credential_source(source) == AICredentialSource.SSM_SECURE_STRING.value
    except CredentialValidationError:
        return False


def is_environment_variable_source(source: str | None) -> bool:
    return normalize_credential_source(source) == AICredentialSource.ENVIRONMENT_VARIABLE.value


def looks_like_pasted_secret(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return False
    if any(stripped.startswith(prefix) for prefix in _SECRET_LIKE_PREFIXES):
        return True
    # Long opaque tokens without underscores are unlikely to be env var names.
    return bool(len(stripped) >= 24 and "_" not in stripped and "-" in stripped)


def validate_environment_variable_name(name: str | None) -> str:
    """Validate an environment variable *name* (never a secret value).

    Raises CredentialValidationError without echoing the rejected input.
    """
    if name is None or not str(name).strip():
        raise CredentialValidationError("environment_variable_name is required")
    candidate = str(name).strip()
    if looks_like_pasted_secret(candidate):
        raise CredentialValidationError(
            "environment_variable_name looks like a secret value. "
            "Enter the server environment variable name only (for example OPENAI_API_KEY)."
        )
    if not _ENV_VAR_NAME_RE.match(candidate):
        raise CredentialValidationError(
            "environment_variable_name must match ^[A-Za-z_]\\w*$"
        )
    if len(candidate) > 128:
        raise CredentialValidationError("environment_variable_name is too long")
    return candidate


def validate_api_key_present(api_key: str | None) -> str:
    if api_key is None or not str(api_key).strip():
        raise CredentialValidationError(
            "api_key is required for encrypted organization secret credential sources"
        )
    return str(api_key).strip()


def safe_key_fingerprint(api_key: str) -> str | None:
    """Return a non-reversible last-four display hint when the key is long enough."""
    key = api_key.strip()
    if len(key) < 8:
        return None
    return f"…{key[-4:]}"


def redact_secrets(text: str | None, *, secrets: list[str] | None = None) -> str:
    """Best-effort redaction for logs and error messages."""
    if not text:
        return ""
    redacted = text
    for secret in secrets or []:
        if secret and len(secret) >= 8 and secret in redacted:
            redacted = redacted.replace(secret, "[REDACTED]")
    for prefix in _SECRET_LIKE_PREFIXES:
        # Collapse sk-… style tokens in free text.
        pattern = re.compile(re.escape(prefix) + r"[\w\-]{8,}", re.ASCII)
        redacted = pattern.sub(f"{prefix}[REDACTED]", redacted)
    return redacted


def redact_mapping(data: dict | None, *, secrets: list[str] | None = None) -> dict:
    """Redact known secret field names and values in a shallow/deep mapping."""
    if not data:
        return {}

    def _walk(obj: object) -> object:
        if isinstance(obj, dict):
            out: dict = {}
            for key, value in obj.items():
                if str(key).lower() in _SECRET_FIELD_NAMES:
                    out[key] = "[REDACTED]"
                else:
                    out[key] = _walk(value)
            return out
        if isinstance(obj, list):
            return [_walk(item) for item in obj]
        if isinstance(obj, str):
            return redact_secrets(obj, secrets=secrets)
        return obj

    result = _walk(data)
    assert isinstance(result, dict)
    return result


def validate_create_credentials(
    *,
    credential_source: str,
    api_key: str | None,
    environment_variable_name: str | None,
) -> tuple[str, str | None, str | None]:
    """Return (canonical_source, api_key_or_none, env_name_or_none)."""
    source = normalize_credential_source(credential_source)
    if source in {
        AICredentialSource.SSM_SECURE_STRING.value,
        AICredentialSource.ENCRYPTED_ORGANIZATION_SECRET.value,
    }:
        if environment_variable_name:
            raise CredentialValidationError(
                "organization-managed secrets must not include environment_variable_name"
            )
        return source, validate_api_key_present(api_key), None
    if source == AICredentialSource.ENVIRONMENT_VARIABLE.value:
        if api_key:
            raise CredentialValidationError(
                "environment_variable must not include api_key. "
                "Enter the environment variable name only."
            )
        return source, None, validate_environment_variable_name(environment_variable_name)
    if source == AICredentialSource.NONE.value:
        return source, None, None
    raise CredentialValidationError(
        f"Credential source '{source}' is not available yet for OpenAI connections"
    )
