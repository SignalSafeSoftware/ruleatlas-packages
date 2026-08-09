"""Tests for the immutable, compressed AST payload representation."""

from __future__ import annotations

import pytest
from ruleatlas_contracts.ast import AstNodeFlags, AstNodeRecord, AstPoint, AstSourceRange

from ruleatlas_persistence.ast_payload_codec import decode_ast_payload, encode_ast_payload


def _nodes() -> list[AstNodeRecord]:
    return [
        AstNodeRecord(
            document_key="src/auth.py:sha256:first",
            node_key="root",
            raw_type="module",
            source_range=AstSourceRange(0, 24, AstPoint(0, 0), AstPoint(1, 0)),
            flags=AstNodeFlags(is_named=True),
            sibling_ordinal=0,
            attributes={"language": "python"},
        ),
        AstNodeRecord(
            document_key="src/auth.py:sha256:first",
            node_key="condition",
            parent_node_key="root",
            raw_type="if_statement",
            source_range=AstSourceRange(0, 23, AstPoint(0, 0), AstPoint(0, 23)),
            flags=AstNodeFlags(is_named=True, is_error=True),
            sibling_ordinal=0,
            field_name="body",
        ),
    ]


def test_codec_is_deterministic_and_round_trips_all_normalized_fields() -> None:
    records = _nodes()

    encoded = encode_ast_payload(records)
    reordered = encode_ast_payload(list(reversed(records)))
    decoded = decode_ast_payload(
        encoded.payload_bytes,
        expected_sha256=encoded.uncompressed_sha256,
    )

    assert reordered.payload_bytes == encoded.payload_bytes
    assert reordered.uncompressed_sha256 == encoded.uncompressed_sha256
    assert decoded.document_key == records[0].document_key
    assert decoded.root_node_key == "root"
    assert decoded.records == tuple(sorted(records, key=lambda record: record.node_key))
    assert encoded.node_count == 2
    assert encoded.error_node_count == 1


def test_codec_rejects_checksum_mismatch() -> None:
    encoded = encode_ast_payload(_nodes())

    with pytest.raises(ValueError, match="checksum"):
        decode_ast_payload(encoded.payload_bytes, expected_sha256="0" * 64)


def test_codec_round_trips_an_empty_document_when_document_key_is_explicit() -> None:
    encoded = encode_ast_payload([], document_key="src/empty.py:sha256:first")

    decoded = decode_ast_payload(
        encoded.payload_bytes,
        expected_sha256=encoded.uncompressed_sha256,
    )

    assert decoded.document_key == "src/empty.py:sha256:first"
    assert decoded.root_node_key is None
    assert decoded.records == ()
    assert decoded.node_count == 0


def test_codec_rejects_disconnected_cycle() -> None:
    records = _nodes()
    records[0] = AstNodeRecord(
        document_key=records[0].document_key,
        node_key="root",
        parent_node_key="cycle",
        raw_type="module",
        source_range=records[0].source_range,
        flags=records[0].flags,
        sibling_ordinal=0,
    )
    records[1] = AstNodeRecord(
        document_key=records[1].document_key,
        node_key="cycle",
        parent_node_key="root",
        raw_type="if_statement",
        source_range=records[1].source_range,
        flags=records[1].flags,
        sibling_ordinal=0,
    )
    records.append(
        AstNodeRecord(
            document_key=records[0].document_key,
            node_key="standalone",
            raw_type="module",
            source_range=AstSourceRange(0, 0, AstPoint(0, 0), AstPoint(0, 0)),
            flags=AstNodeFlags(is_named=True),
            sibling_ordinal=0,
        )
    )

    with pytest.raises(ValueError, match="cycle"):
        encode_ast_payload(records)
