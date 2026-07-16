"""Parsing helpers for OpenAI compatibility-probe responses."""

from __future__ import annotations

import json
from typing import Any


def parse_json_object(content: str) -> dict[str, Any] | None:
    """Return the object embedded in a model text response, if valid."""
    cleaned = str(content).strip()
    if not cleaned:
        return None
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            return None
        parsed = json.loads(cleaned[start : end + 1])
        return parsed if isinstance(parsed, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


def is_status_ok(parsed: dict[str, Any]) -> bool:
    """Validate the intentionally minimal structured-output probe result."""
    return parsed.get("status") == "ok" and set(parsed.keys()) <= {"status"}
