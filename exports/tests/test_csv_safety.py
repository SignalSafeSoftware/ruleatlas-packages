"""CSV formula-injection neutralization (RA-08-002)."""

from __future__ import annotations

import pytest

from ruleatlas_exports.csv_safety import sanitize_csv_cell


def test_none_becomes_empty() -> None:
    assert sanitize_csv_cell(None) == ""


def test_plain_values_pass_through() -> None:
    assert sanitize_csv_cell("hello") == "hello"
    assert sanitize_csv_cell(42) == "42"
    assert sanitize_csv_cell("a=b+c") == "a=b+c"  # trigger char not leading


@pytest.mark.parametrize("payload", ["=SUM(A1)", "+1", "-1", "@cmd", "\ttab", "\rcr"])
def test_formula_triggers_are_quote_prefixed(payload: str) -> None:
    out = sanitize_csv_cell(payload)
    assert out == "'" + payload
    assert out[0] == "'"
