"""Deterministic, integrity-checked encoding for compact AST payloads.

The relational ``ast_nodes`` table remains the read model during the RA-01
transition.  This module defines the canonical packed representation used for
dual-write and later migration verification.  Keeping the format independent
of ORM identifiers makes it portable across database copies and backfills.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

import zstandard as zstd
from ruleatlas_contracts.ast import (
    AstNodeCategory,
    AstNodeFlags,
    AstNodeRecord,
    AstSourceRange,
)

ENCODING_VERSION = "ast-node-records/v1"
COMPRESSION_CODEC = "zstd"
MAX_UNCOMPRESSED_BYTES = 256 * 1024 * 1024


@dataclass(frozen=True)
class EncodedAstPayload:
    """Canonical payload bytes and integrity metadata ready for persistence."""

    encoding_version: str
    compression_codec: str
    payload_bytes: bytes
    uncompressed_sha256: str
    uncompressed_bytes: int
    compressed_bytes: int
    document_key: str
    root_node_key: str | None
    node_count: int
    error_node_count: int


@dataclass(frozen=True)
class DecodedAstPayload:
    """Validated records reconstructed from an ``EncodedAstPayload`` blob."""

    document_key: str
    root_node_key: str | None
    records: tuple[AstNodeRecord, ...]
    uncompressed_sha256: str
    uncompressed_bytes: int
    node_count: int
    error_node_count: int


def encode_ast_payload(
    records: list[AstNodeRecord] | tuple[AstNodeRecord, ...],
    *,
    document_key: str | None = None,
) -> EncodedAstPayload:
    """Encode a complete document tree in canonical node-key order.

    Ordering caller input differently produces identical bytes.  The format
    retains every normalized node field required to recreate the present AST
    read model, but deliberately excludes database UUIDs and timestamps.
    """

    normalized_records, validated_document_key, root_node_key = _validate_tree(
        records,
        document_key=document_key,
    )
    error_node_count = sum(
        1 for record in normalized_records if record.flags.is_error or record.flags.is_missing
    )
    document = {
        "schema_version": ENCODING_VERSION,
        "document_key": validated_document_key,
        "root_node_key": root_node_key,
        "node_count": len(normalized_records),
        "error_node_count": error_node_count,
        "nodes": [_node_to_dict(record) for record in normalized_records],
    }
    try:
        uncompressed = json.dumps(
            document,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("AST node attributes must be JSON serializable") from exc
    compressed = zstd.ZstdCompressor(level=9, write_checksum=True).compress(uncompressed)
    return EncodedAstPayload(
        encoding_version=ENCODING_VERSION,
        compression_codec=COMPRESSION_CODEC,
        payload_bytes=compressed,
        uncompressed_sha256=sha256(uncompressed).hexdigest(),
        uncompressed_bytes=len(uncompressed),
        compressed_bytes=len(compressed),
        document_key=validated_document_key,
        root_node_key=root_node_key,
        node_count=len(normalized_records),
        error_node_count=error_node_count,
    )


def decode_ast_payload(
    payload_bytes: bytes,
    *,
    expected_sha256: str | None = None,
    max_uncompressed_bytes: int = MAX_UNCOMPRESSED_BYTES,
) -> DecodedAstPayload:
    """Decompress, checksum, and fully validate a packed AST payload."""

    if max_uncompressed_bytes < 1:
        raise ValueError("max_uncompressed_bytes must be positive")
    try:
        uncompressed = zstd.ZstdDecompressor().decompress(
            payload_bytes,
            max_output_size=max_uncompressed_bytes,
        )
    except zstd.ZstdError as exc:
        raise ValueError("AST payload is not valid zstd data") from exc
    actual_sha256 = sha256(uncompressed).hexdigest()
    if expected_sha256 is not None and actual_sha256 != expected_sha256:
        raise ValueError("AST payload checksum does not match stored metadata")
    try:
        document = json.loads(uncompressed.decode("utf-8"), parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("AST payload is not valid canonical JSON") from exc
    if not isinstance(document, dict):
        raise ValueError("AST payload root must be an object")
    if document.get("schema_version") != ENCODING_VERSION:
        raise ValueError("AST payload encoding version is unsupported")
    document_key = _require_string(document.get("document_key"), "document_key")
    root_node_key = _require_optional_string(document.get("root_node_key"), "root_node_key")
    encoded_nodes = document.get("nodes")
    if not isinstance(encoded_nodes, list):
        raise ValueError("AST payload nodes must be a list")
    records = tuple(_node_from_dict(node, document_key) for node in encoded_nodes)
    normalized_records, validated_document_key, validated_root_key = _validate_tree(
        records,
        document_key=document_key,
    )
    if document_key != validated_document_key or root_node_key != validated_root_key:
        raise ValueError("AST payload root metadata does not match its node tree")
    if _require_nonnegative_int(document.get("node_count"), "node_count") != len(normalized_records):
        raise ValueError("AST payload node count does not match its node tree")
    expected_error_nodes = sum(
        1 for record in normalized_records if record.flags.is_error or record.flags.is_missing
    )
    if _require_nonnegative_int(document.get("error_node_count"), "error_node_count") != expected_error_nodes:
        raise ValueError("AST payload error-node count does not match its node tree")
    return DecodedAstPayload(
        document_key=document_key,
        root_node_key=root_node_key,
        records=tuple(normalized_records),
        uncompressed_sha256=actual_sha256,
        uncompressed_bytes=len(uncompressed),
        node_count=len(normalized_records),
        error_node_count=expected_error_nodes,
    )


def _node_to_dict(record: AstNodeRecord) -> dict[str, Any]:
    return {
        "node_key": record.node_key,
        "parent_node_key": record.parent_node_key,
        "sibling_ordinal": record.sibling_ordinal,
        "raw_type": record.raw_type,
        "category": record.category.value,
        "field_name": record.field_name,
        "flags": record.flags.to_dict(),
        "source_range": record.source_range.to_dict(),
        "subtree_hash": record.subtree_hash,
        "display_name": record.display_name,
        "attributes": dict(record.attributes),
    }


def _node_from_dict(value: object, document_key: str) -> AstNodeRecord:
    if not isinstance(value, dict):
        raise ValueError("AST payload nodes must contain objects")
    source_range = value.get("source_range")
    flags = value.get("flags")
    attributes = value.get("attributes", {})
    if not isinstance(source_range, dict):
        raise ValueError("AST payload node source_range must be an object")
    if not isinstance(flags, dict):
        raise ValueError("AST payload node flags must be an object")
    if not isinstance(attributes, dict):
        raise ValueError("AST payload node attributes must be an object")
    try:
        category = AstNodeCategory(_require_string(value.get("category"), "category"))
    except ValueError as exc:
        raise ValueError("AST payload node category is unsupported") from exc
    return AstNodeRecord(
        document_key=document_key,
        node_key=_require_string(value.get("node_key"), "node_key"),
        parent_node_key=_require_optional_string(value.get("parent_node_key"), "parent_node_key"),
        sibling_ordinal=_require_nonnegative_int(value.get("sibling_ordinal"), "sibling_ordinal"),
        raw_type=_require_string(value.get("raw_type"), "raw_type"),
        category=category,
        field_name=_require_optional_string(value.get("field_name"), "field_name"),
        flags=AstNodeFlags.from_dict(flags),
        source_range=AstSourceRange.from_dict(source_range),
        subtree_hash=_require_optional_string(value.get("subtree_hash"), "subtree_hash"),
        display_name=_require_optional_string(value.get("display_name"), "display_name"),
        attributes=attributes,
    )


def _validate_tree(
    records: list[AstNodeRecord] | tuple[AstNodeRecord, ...],
    *,
    document_key: str | None = None,
) -> tuple[tuple[AstNodeRecord, ...], str, str | None]:
    if not records:
        if document_key is None:
            raise ValueError("empty AST payloads require document_key")
        return (), _require_string(document_key, "document_key"), None
    document_keys = {record.document_key for record in records}
    if len(document_keys) != 1:
        raise ValueError("every AST payload node must use the same document_key")
    if document_key is not None and document_key not in document_keys:
        raise ValueError("AST payload nodes do not match document_key")
    keys = [record.node_key for record in records]
    if len(set(keys)) != len(keys):
        raise ValueError("AST payload node_key values must be unique")
    by_key = {record.node_key: record for record in records}
    roots = [record for record in records if record.parent_node_key is None]
    if len(roots) != 1:
        raise ValueError("AST payload must contain exactly one root")
    sibling_positions: set[tuple[str | None, int]] = set()
    for record in records:
        if record.parent_node_key is not None and record.parent_node_key not in by_key:
            raise ValueError(f"AST payload parent node is missing: {record.parent_node_key}")
        position = (record.parent_node_key, record.sibling_ordinal)
        if position in sibling_positions:
            raise ValueError("AST payload sibling ordinals must be unique per parent")
        sibling_positions.add(position)
    children_by_parent: dict[str, list[str]] = {}
    for record in records:
        if record.parent_node_key is not None:
            children_by_parent.setdefault(record.parent_node_key, []).append(record.node_key)
    visited: set[str] = set()
    frontier = [roots[0].node_key]
    while frontier:
        node_key = frontier.pop()
        if node_key in visited:
            continue
        visited.add(node_key)
        frontier.extend(children_by_parent.get(node_key, ()))
    if len(visited) != len(records):
        unresolved = ", ".join(sorted(set(by_key) - visited)[:3])
        raise ValueError(f"AST payload node tree has a cycle or missing key: {unresolved}")
    return tuple(sorted(records, key=lambda record: record.node_key)), next(iter(document_keys)), roots[0].node_key


def _require_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"AST payload {field_name} must be a non-blank string")
    return value


def _require_optional_string(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _require_string(value, field_name)


def _require_nonnegative_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"AST payload {field_name} must be a non-negative integer")
    return value


def _reject_json_constant(value: str) -> object:
    raise ValueError(f"invalid JSON constant: {value}")


__all__ = [
    "COMPRESSION_CODEC",
    "ENCODING_VERSION",
    "DecodedAstPayload",
    "EncodedAstPayload",
    "decode_ast_payload",
    "encode_ast_payload",
]
