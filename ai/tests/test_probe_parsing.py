"""Parsing + sanitization helpers for the OpenAI compatibility probe."""

from __future__ import annotations

from ruleatlas_ai.providers.openai_probe_parsing import is_status_ok, parse_json_object
from ruleatlas_ai.providers.openai_probe_sanitization import sanitize_provider_error


def test_parse_json_object_extracts_embedded_object() -> None:
    assert parse_json_object('{"status": "ok"}') == {"status": "ok"}
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_object('prefix {"a": 1} suffix') == {"a": 1}


def test_parse_json_object_rejects_non_objects() -> None:
    assert parse_json_object("no object here") is None
    assert parse_json_object("") is None
    assert parse_json_object("[1, 2, 3]") is None


def test_is_status_ok_is_strict() -> None:
    assert is_status_ok({"status": "ok"})
    assert not is_status_ok({"status": "ok", "extra": 1})
    assert not is_status_ok({"status": "bad"})
    assert not is_status_ok({})


def test_sanitize_provider_error_always_returns_dict() -> None:
    assert isinstance(sanitize_provider_error(None), dict)
    assert isinstance(sanitize_provider_error({"error": {"message": "boom"}}), dict)
