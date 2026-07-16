"""Safe provider-error metadata extraction for compatibility probes."""

from __future__ import annotations

from typing import Any


def sanitize_provider_error(body: dict[str, Any] | None) -> dict[str, Any]:
    """Extract safe provider error metadata — never raw bodies or secrets."""
    if not isinstance(body, dict):
        return {}
    error = body.get("error")
    if not isinstance(error, dict):
        return {}
    message = str(error.get("message") or "")
    code = str(error.get("code") or error.get("type") or "")
    param = str(error.get("param") or "")
    safe_message = message
    for needle in ("sk-", "Bearer ", "Authorization"):
        if needle in safe_message:
            safe_message = safe_message.split(needle)[0].rstrip() + "[redacted]"
    return {
        "provider_error_code": code.lower() or None,
        "provider_error_param": param.lower() or None,
        "provider_error_summary": safe_message[:180] or None,
    }
