"""Behavioral tests for parser-independent AST value objects."""

from __future__ import annotations

import pytest

from ruleatlas_contracts.ast import (
    AstLinkType,
    AstNodeCategory,
    AstNodeFlags,
    AstParseStatus,
    AstPoint,
    AstResolutionType,
    AstSourceRange,
    ParserIdentity,
    ParserRuntimeIdentity,
)


def test_ast_vocabularies_are_stable_strings() -> None:
    assert AstParseStatus.SUCCEEDED.value == "succeeded"
    assert AstNodeCategory.CONDITION.value == "condition"
    assert AstLinkType.RELATED_TEST.value == "related_test"
    assert AstResolutionType.AMBIGUOUS.value == "ambiguous"


def test_ast_point_is_ordered_and_serializable() -> None:
    start = AstPoint(row=2, column=4)
    end = AstPoint(row=2, column=9)

    assert start < end
    assert start.to_dict() == {"row": 2, "column": 4}
    assert AstPoint.from_dict(start.to_dict()) == start


@pytest.mark.parametrize(("row", "column"), [(-1, 0), (0, -1)])
def test_ast_point_rejects_negative_coordinates(row: int, column: int) -> None:
    with pytest.raises(ValueError, match="must be non-negative"):
        AstPoint(row=row, column=column)


@pytest.mark.parametrize(
    "payload",
    [
        {"row": True, "column": 0},
        {"row": 0, "column": False},
        {"row": "0", "column": 0},
        {"row": 0},
    ],
)
def test_ast_point_rejects_non_integer_payloads(payload: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="must be an integer"):
        AstPoint.from_dict(payload)


def test_ast_source_range_uses_half_open_bytes() -> None:
    source_range = AstSourceRange(
        start_byte=10,
        end_byte=15,
        start_point=AstPoint(1, 2),
        end_point=AstPoint(1, 7),
    )

    assert source_range.byte_length == 5
    assert not source_range.is_empty
    assert source_range.contains_byte(10)
    assert source_range.contains_byte(14)
    assert not source_range.contains_byte(15)
    assert source_range.contains_byte(15, include_end=True)


def test_ast_source_range_contains_and_overlaps() -> None:
    outer = AstSourceRange(0, 20, AstPoint(0, 0), AstPoint(2, 0))
    inner = AstSourceRange(5, 10, AstPoint(0, 5), AstPoint(0, 10))
    overlap = AstSourceRange(15, 25, AstPoint(1, 0), AstPoint(3, 0))
    adjacent = AstSourceRange(20, 25, AstPoint(2, 0), AstPoint(3, 0))

    assert outer.contains_range(inner)
    assert outer.overlaps(overlap)
    assert not outer.overlaps(adjacent)


def test_ast_source_range_round_trips() -> None:
    source_range = AstSourceRange(3, 8, AstPoint(0, 3), AstPoint(0, 8))
    assert AstSourceRange.from_dict(source_range.to_dict()) == source_range


def test_ast_source_range_rejects_reversed_bytes_or_points() -> None:
    reversed_bytes_start = AstPoint(0, 0)
    reversed_bytes_end = AstPoint(0, 1)
    with pytest.raises(ValueError, match="end_byte"):
        AstSourceRange(4, 3, reversed_bytes_start, reversed_bytes_end)
    reversed_points_start = AstPoint(2, 0)
    reversed_points_end = AstPoint(1, 0)
    with pytest.raises(ValueError, match="end_point"):
        AstSourceRange(0, 1, reversed_points_start, reversed_points_end)


def test_ast_node_flags_round_trip_and_validate_types() -> None:
    flags = AstNodeFlags(is_named=True, is_error=True, has_error=True)
    assert AstNodeFlags.from_dict(flags.to_dict()) == flags

    with pytest.raises(ValueError, match="is_error must be a boolean"):
        AstNodeFlags.from_dict({"is_named": True, "is_error": 1})


def test_parser_identity_is_stable_and_serializable() -> None:
    identity = ParserIdentity(
        parser_key="tree_sitter",
        parser_version="0.26.0",
        language_key="python",
        grammar_key="tree-sitter-python",
        grammar_version="0.25.0",
    )

    assert identity.to_dict()["language_key"] == "python"


def test_parser_runtime_identity_has_no_document_grammar() -> None:
    identity = ParserRuntimeIdentity(parser_key="tree_sitter", parser_version="0.26.0")
    assert identity.to_dict() == {
        "parser_key": "tree_sitter",
        "parser_version": "0.26.0",
    }


@pytest.mark.parametrize(
    "field_name",
    ["parser_key", "parser_version", "language_key", "grammar_key", "grammar_version"],
)
def test_parser_identity_rejects_blank_fields(field_name: str) -> None:
    values = {
        "parser_key": "tree_sitter",
        "parser_version": "0.26.0",
        "language_key": "python",
        "grammar_key": "tree-sitter-python",
        "grammar_version": "0.25.0",
    }
    values[field_name] = " "

    with pytest.raises(ValueError, match=field_name):
        ParserIdentity(**values)
