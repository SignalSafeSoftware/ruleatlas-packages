"""Value objects and vocabularies for parser-independent AST records.

These contracts deliberately describe parser facts without importing tree-sitter or a persistence
library. Rows and columns use tree-sitter's zero-based point convention. Byte ranges are half-open:
``start_byte`` is included and ``end_byte`` is excluded.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AstParseStatus(StrEnum):
    """Lifecycle outcome for one parse run or AST document."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"
    REUSED = "reused"
    CANCELLED = "cancelled"


class AstNodeCategory(StrEnum):
    """Optional language-neutral category layered over a parser's raw node type.

    ``UNKNOWN`` is an honest fallback. Consumers must retain and expose the raw parser node type
    rather than assuming every language-specific construct maps to one of these categories.
    """

    UNKNOWN = "unknown"
    DOCUMENT = "document"
    NAMESPACE = "namespace"
    IMPORT = "import"
    EXPORT = "export"
    TYPE_DEFINITION = "type_definition"
    CLASS_DEFINITION = "class_definition"
    INTERFACE_DEFINITION = "interface_definition"
    FUNCTION_DEFINITION = "function_definition"
    METHOD_DEFINITION = "method_definition"
    PARAMETER = "parameter"
    BLOCK = "block"
    CONDITION = "condition"
    BRANCH = "branch"
    LOOP = "loop"
    MATCH = "match"
    CALL = "call"
    ASSIGNMENT = "assignment"
    RETURN = "return"
    EXCEPTION = "exception"
    LITERAL = "literal"
    IDENTIFIER = "identifier"
    COMMENT = "comment"


class AstLinkType(StrEnum):
    """Relationship between an AST node and another persisted artifact."""

    GRAPH_NODE = "graph_node"
    SOURCE_SYMBOL = "source_symbol"
    EVIDENCE = "evidence"
    CALL_TARGET = "call_target"
    DEFINITION = "definition"
    REFERENCE = "reference"
    RELATED_TEST = "related_test"
    RELATED_BDD_SCENARIO = "related_bdd_scenario"
    CONFIGURATION_REFERENCE = "configuration_reference"


class AstResolutionType(StrEnum):
    """Strength of an AST link without overstating inferred relationships."""

    EXTRACTED = "extracted"
    RESOLVED = "resolved"
    INFERRED = "inferred"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


def _require_non_negative(value: int, field_name: str) -> None:
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")


def _require_non_blank(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")


@dataclass(frozen=True, order=True)
class AstPoint:
    """Zero-based row and column within one decoded source document."""

    row: int
    column: int

    def __post_init__(self) -> None:
        _require_non_negative(self.row, "row")
        _require_non_negative(self.column, "column")

    def to_dict(self) -> dict[str, int]:
        return {"row": self.row, "column": self.column}

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> AstPoint:
        row = value.get("row")
        column = value.get("column")
        if not isinstance(row, int) or isinstance(row, bool):
            raise ValueError("row must be an integer")
        if not isinstance(column, int) or isinstance(column, bool):
            raise ValueError("column must be an integer")
        return cls(row=row, column=column)


@dataclass(frozen=True)
class AstSourceRange:
    """Half-open byte range plus zero-based start/end points."""

    start_byte: int
    end_byte: int
    start_point: AstPoint
    end_point: AstPoint

    def __post_init__(self) -> None:
        _require_non_negative(self.start_byte, "start_byte")
        _require_non_negative(self.end_byte, "end_byte")
        if self.end_byte < self.start_byte:
            raise ValueError("end_byte must be greater than or equal to start_byte")
        if self.end_point < self.start_point:
            raise ValueError("end_point must be greater than or equal to start_point")

    @property
    def byte_length(self) -> int:
        return self.end_byte - self.start_byte

    @property
    def is_empty(self) -> bool:
        return self.byte_length == 0

    def contains_byte(self, offset: int, *, include_end: bool = False) -> bool:
        """Return whether ``offset`` falls in this range.

        AST ranges are normally half-open. ``include_end`` is useful when resolving a cursor at the
        exact end point of an empty or terminal node.
        """

        _require_non_negative(offset, "offset")
        if include_end:
            return self.start_byte <= offset <= self.end_byte
        return self.start_byte <= offset < self.end_byte

    def contains_range(self, other: AstSourceRange) -> bool:
        return self.start_byte <= other.start_byte and other.end_byte <= self.end_byte

    def overlaps(self, other: AstSourceRange) -> bool:
        return self.start_byte < other.end_byte and other.start_byte < self.end_byte

    def to_dict(self) -> dict[str, object]:
        return {
            "start_byte": self.start_byte,
            "end_byte": self.end_byte,
            "start_point": self.start_point.to_dict(),
            "end_point": self.end_point.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> AstSourceRange:
        start_byte = value.get("start_byte")
        end_byte = value.get("end_byte")
        start_point = value.get("start_point")
        end_point = value.get("end_point")
        if not isinstance(start_byte, int) or isinstance(start_byte, bool):
            raise ValueError("start_byte must be an integer")
        if not isinstance(end_byte, int) or isinstance(end_byte, bool):
            raise ValueError("end_byte must be an integer")
        if not isinstance(start_point, dict):
            raise ValueError("start_point must be an object")
        if not isinstance(end_point, dict):
            raise ValueError("end_point must be an object")
        return cls(
            start_byte=start_byte,
            end_byte=end_byte,
            start_point=AstPoint.from_dict(start_point),
            end_point=AstPoint.from_dict(end_point),
        )


@dataclass(frozen=True)
class AstNodeFlags:
    """Tree-sitter node flags preserved without exposing a runtime ``Node``."""

    is_named: bool
    is_extra: bool = False
    is_error: bool = False
    is_missing: bool = False
    has_error: bool = False
    has_changes: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            "is_named": self.is_named,
            "is_extra": self.is_extra,
            "is_error": self.is_error,
            "is_missing": self.is_missing,
            "has_error": self.has_error,
            "has_changes": self.has_changes,
        }

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> AstNodeFlags:
        field_names = (
            "is_named",
            "is_extra",
            "is_error",
            "is_missing",
            "has_error",
            "has_changes",
        )
        for field_name in field_names:
            if field_name in value and not isinstance(value[field_name], bool):
                raise ValueError(f"{field_name} must be a boolean")
        is_named = value.get("is_named")
        if not isinstance(is_named, bool):
            raise ValueError("is_named must be a boolean")
        return cls(
            is_named=is_named,
            is_extra=bool(value.get("is_extra", False)),
            is_error=bool(value.get("is_error", False)),
            is_missing=bool(value.get("is_missing", False)),
            has_error=bool(value.get("has_error", False)),
            has_changes=bool(value.get("has_changes", False)),
        )


@dataclass(frozen=True)
class ParserRuntimeIdentity:
    """Parser runtime identity shared by every document in a parse run."""

    parser_key: str
    parser_version: str

    def __post_init__(self) -> None:
        _require_non_blank(self.parser_key, "parser_key")
        _require_non_blank(self.parser_version, "parser_version")

    def to_dict(self) -> dict[str, str]:
        return {
            "parser_key": self.parser_key,
            "parser_version": self.parser_version,
        }


@dataclass(frozen=True)
class ParserIdentity:
    """Parser plus language grammar identity for one reproducible AST document."""

    parser_key: str
    parser_version: str
    language_key: str
    grammar_key: str
    grammar_version: str

    def __post_init__(self) -> None:
        _require_non_blank(self.parser_key, "parser_key")
        _require_non_blank(self.parser_version, "parser_version")
        _require_non_blank(self.language_key, "language_key")
        _require_non_blank(self.grammar_key, "grammar_key")
        _require_non_blank(self.grammar_version, "grammar_version")

    def to_dict(self) -> dict[str, str]:
        return {
            "parser_key": self.parser_key,
            "parser_version": self.parser_version,
            "language_key": self.language_key,
            "grammar_key": self.grammar_key,
            "grammar_version": self.grammar_version,
        }


__all__ = [
    "AstLinkType",
    "AstNodeCategory",
    "AstNodeFlags",
    "AstParseStatus",
    "AstPoint",
    "AstResolutionType",
    "AstSourceRange",
    "ParserIdentity",
    "ParserRuntimeIdentity",
]
