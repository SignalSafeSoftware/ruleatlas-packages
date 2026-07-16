"""Shared helpers for enum and string coercion."""

from __future__ import annotations


def enum_value(value: object, default: str = "") -> str:
    if value is None:
        return default
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)
