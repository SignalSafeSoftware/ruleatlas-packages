"""Integration tests for scoped, batched AST write repositories."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from ruleatlas_contracts.ast import (
    AstDocumentRecord,
    AstLinkRecord,
    AstLinkType,
    AstNodeFlags,
    AstNodeRecord,
    AstParseRunRecord,
    AstParseStatus,
    AstParseSummary,
    AstPoint,
    AstResolutionType,
    AstSourceRange,
    ParserIdentity,
    ParserRuntimeIdentity,
)
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session

import ruleatlas_persistence.models as _models  # noqa: F401
from ruleatlas_persistence.base import Base
from ruleatlas_persistence.models import AstDocument, AstNode, AstNodeLink, AstParseRun, AstPayload, AstPayloadBlob
from ruleatlas_persistence.repositories import RepositoryFactory


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as value:
        yield value
        value.rollback()
    engine.dispose()


@pytest.fixture
def parser() -> ParserIdentity:
    return ParserIdentity(
        parser_key="tree_sitter",
        parser_version="0.26.0",
        language_key="python",
        grammar_key="tree-sitter-python",
        grammar_version="0.25.0",
    )


def _parse_run_record() -> AstParseRunRecord:
    return AstParseRunRecord(
        parse_run_id="parse-1",
        project_id="project-1",
        analysis_version_id="analysis-1",
        scan_run_id="scan-1",
        parser=ParserRuntimeIdentity("tree_sitter", "0.26.0"),
        status=AstParseStatus.RUNNING,
    )


def _document_record(parser: ParserIdentity, *, content_hash: str = "sha256:first") -> AstDocumentRecord:
    return AstDocumentRecord(
        document_key=f"src/auth.py:{content_hash}",
        project_id="project-1",
        analysis_version_id="analysis-1",
        parse_run_id="parse-1",
        scan_run_id="scan-1",
        source_file_id="file-1",
        source_path="src/auth.py",
        parser=parser,
        content_hash=content_hash,
        status=AstParseStatus.SUCCEEDED,
        source_bytes=24,
        node_count=2,
        root_node_key="root",
    )


def _node_records(document_key: str) -> list[AstNodeRecord]:
    return [
        AstNodeRecord(
            document_key=document_key,
            node_key="root",
            raw_type="module",
            source_range=AstSourceRange(0, 24, AstPoint(0, 0), AstPoint(1, 0)),
            flags=AstNodeFlags(is_named=True),
            sibling_ordinal=0,
            subtree_hash="sha256:root",
        ),
        AstNodeRecord(
            document_key=document_key,
            node_key="condition",
            parent_node_key="root",
            raw_type="if_statement",
            source_range=AstSourceRange(0, 23, AstPoint(0, 0), AstPoint(0, 23)),
            flags=AstNodeFlags(is_named=True),
            sibling_ordinal=0,
            field_name="body",
            subtree_hash="sha256:condition",
        ),
    ]


def _create_document(
    repos: RepositoryFactory,
    record: AstDocumentRecord,
) -> AstDocument:
    payload = repos.ast_payloads().create_for_record(record)
    return repos.ast_documents().create_from_record(
        record,
        ast_payload_id=payload.id,
    )


def test_parse_run_lifecycle_does_not_commit(session: Session) -> None:
    repos = RepositoryFactory(session)
    row = repos.ast_parse_runs().create_from_record(_parse_run_record())
    assert row.status == AstParseStatus.RUNNING.value

    summary = AstParseSummary(
        files_attempted=1,
        files_succeeded=1,
        documents_created=1,
        nodes_created=2,
        source_bytes=24,
    )
    repos.ast_parse_runs().update_outcome(
        row.id,
        status=AstParseStatus.SUCCEEDED,
        summary=summary,
    )
    assert row.files_succeeded == 1
    assert row.nodes_count == 2

    session.rollback()
    assert session.get(AstParseRun, "parse-1") is None


def test_bulk_nodes_insert_once_and_assign_root(
    session: Session,
    parser: ParserIdentity,
) -> None:
    repos = RepositoryFactory(session)
    repos.ast_parse_runs().create_from_record(_parse_run_record())
    document = _create_document(repos, _document_record(parser))
    node_insert_calls = 0

    def count_node_insert(_conn, _cursor, statement, _parameters, _context, _executemany) -> None:
        nonlocal node_insert_calls
        if statement.lstrip().upper().startswith("INSERT INTO AST_NODES"):
            node_insert_calls += 1

    event.listen(session.get_bind(), "before_cursor_execute", count_node_insert)
    try:
        ids = repos.ast_nodes().bulk_create_for_document(
            document,
            _node_records(document.document_key),
        )
    finally:
        event.remove(session.get_bind(), "before_cursor_execute", count_node_insert)

    assert node_insert_calls == 1
    assert document.root_node_id == ids["root"]
    assert document.node_count == 2
    assert session.scalar(select(func.count()).select_from(AstNode)) == 2
    blob = session.scalar(
        select(AstPayloadBlob).where(AstPayloadBlob.ast_payload_id == document.ast_payload_id)
    )
    assert blob is not None
    assert blob.node_count == document.node_count
    assert blob.root_node_key == "root"


def test_payload_blob_decode_is_scope_bound_and_matches_relational_nodes(
    session: Session,
    parser: ParserIdentity,
) -> None:
    repos = RepositoryFactory(session)
    repos.ast_parse_runs().create_from_record(_parse_run_record())
    document = _create_document(repos, _document_record(parser))
    repos.ast_nodes().bulk_create_for_document(document, _node_records(document.document_key))
    payload = session.get(AstPayload, document.ast_payload_id)
    assert payload is not None

    decoded = repos.ast_payload_blobs().decode_for_document(
        project_id="project-1",
        analysis_version_id="analysis-1",
        document_id=document.id,
    )

    assert decoded is not None
    assert decoded.root_node_key == "root"
    assert decoded.node_count == 2
    assert repos.ast_payload_blobs().verify_against_relational_nodes(payload) == decoded
    assert (
        repos.ast_payload_blobs().decode_for_document(
            project_id="other-project",
            analysis_version_id="analysis-1",
            document_id=document.id,
        )
        is None
    )


def test_payload_blob_backfill_is_bounded_resumable_and_verifies_each_payload(
    session: Session,
    parser: ParserIdentity,
) -> None:
    repos = RepositoryFactory(session)
    repos.ast_parse_runs().create_from_record(_parse_run_record())
    document = _create_document(repos, _document_record(parser))
    repos.ast_nodes().bulk_create_for_document(document, _node_records(document.document_key))
    payload = session.get(AstPayload, document.ast_payload_id)
    assert payload is not None
    original_blob = repos.ast_payload_blobs().get_for_payload(payload.id)
    assert original_blob is not None
    session.delete(original_blob)
    session.flush()

    assert [row.id for row in repos.ast_payload_blobs().list_payloads_without_blob(limit=1)] == [payload.id]
    restored_blob = repos.ast_payload_blobs().backfill_payload(payload.id)

    assert restored_blob.ast_payload_id == payload.id
    assert repos.ast_payload_blobs().verify_against_relational_nodes(payload).node_count == 2
    assert repos.ast_payload_blobs().list_payloads_without_blob(limit=1) == []


def test_payload_blob_rejects_conflicting_immutable_rewrite(
    session: Session,
    parser: ParserIdentity,
) -> None:
    repos = RepositoryFactory(session)
    repos.ast_parse_runs().create_from_record(_parse_run_record())
    document = _create_document(repos, _document_record(parser))
    nodes = _node_records(document.document_key)
    repos.ast_nodes().bulk_create_for_document(document, nodes)
    payload = session.get(AstPayload, document.ast_payload_id)
    assert payload is not None
    conflicting_root = AstNodeRecord(
        document_key=document.document_key,
        node_key="root",
        raw_type="changed_module",
        source_range=nodes[0].source_range,
        flags=nodes[0].flags,
        sibling_ordinal=0,
        subtree_hash=nodes[0].subtree_hash,
    )
    with pytest.raises(ValueError, match="different node content"):
        repos.ast_payload_blobs().create_for_node_records(payload, [conflicting_root, nodes[1]])


def test_bulk_nodes_reject_missing_parent(
    session: Session,
    parser: ParserIdentity,
) -> None:
    repos = RepositoryFactory(session)
    repos.ast_parse_runs().create_from_record(_parse_run_record())
    document = _create_document(repos, _document_record(parser))
    nodes = _node_records(document.document_key)
    nodes[1] = AstNodeRecord(
        document_key=document.document_key,
        node_key="condition",
        parent_node_key="missing",
        raw_type="if_statement",
        source_range=nodes[1].source_range,
        flags=nodes[1].flags,
        sibling_ordinal=0,
    )

    with pytest.raises(ValueError, match="parent node is missing"):
        repos.ast_nodes().bulk_create_for_document(document, nodes)


def test_links_are_bulk_inserted_with_generic_and_typed_targets(
    session: Session,
    parser: ParserIdentity,
) -> None:
    repos = RepositoryFactory(session)
    repos.ast_parse_runs().create_from_record(_parse_run_record())
    document = _create_document(repos, _document_record(parser))
    node_ids = repos.ast_nodes().bulk_create_for_document(
        document,
        _node_records(document.document_key),
    )
    links = [
        AstLinkRecord(
            document_key=document.document_key,
            source_node_key="condition",
            link_type=AstLinkType.CALL_TARGET,
            target_id=node_ids["root"],
            resolution_type=AstResolutionType.RESOLVED,
            resolver_key="test",
            resolver_version="1",
            confidence=0.9,
        ),
        AstLinkRecord(
            document_key=document.document_key,
            source_node_key="condition",
            link_type=AstLinkType.RELATED_BDD_SCENARIO,
            target_id="scenario-1",
            resolution_type=AstResolutionType.INFERRED,
            resolver_key="test",
            resolver_version="1",
            confidence=0.6,
        ),
    ]

    assert repos.ast_node_links().bulk_create_for_document(document, links) == 2
    rows = list(session.scalars(select(AstNodeLink).order_by(AstNodeLink.link_type)))
    by_type = {row.link_type: row for row in rows}
    assert by_type[AstLinkType.CALL_TARGET.value].ast_node_key == "condition"
    assert by_type[AstLinkType.CALL_TARGET.value].target_ast_node_id == node_ids["root"]
    assert by_type[AstLinkType.CALL_TARGET.value].target_ast_document_id == document.id
    assert by_type[AstLinkType.CALL_TARGET.value].target_ast_node_key == "root"
    assert by_type[AstLinkType.RELATED_BDD_SCENARIO.value].target_id == "scenario-1"
    assert by_type[AstLinkType.RELATED_BDD_SCENARIO.value].target_ast_node_id is None
    by_type[AstLinkType.CALL_TARGET.value].ast_node_key = None
    session.flush()
    assert repos.ast_node_links().backfill_stable_node_keys(limit=1) == 1
    session.expire(by_type[AstLinkType.CALL_TARGET.value])
    assert by_type[AstLinkType.CALL_TARGET.value].ast_node_key == "condition"
    by_type[AstLinkType.CALL_TARGET.value].target_ast_document_id = None
    by_type[AstLinkType.CALL_TARGET.value].target_ast_node_key = None
    session.flush()
    assert repos.ast_node_links().backfill_stable_target_node_pointers(limit=1) == 1
    session.expire(by_type[AstLinkType.CALL_TARGET.value])
    assert by_type[AstLinkType.CALL_TARGET.value].target_ast_document_id == document.id
    assert by_type[AstLinkType.CALL_TARGET.value].target_ast_node_key == "root"


def test_replace_document_deletes_old_tree_and_links(
    session: Session,
    parser: ParserIdentity,
) -> None:
    repos = RepositoryFactory(session)
    repos.ast_parse_runs().create_from_record(_parse_run_record())
    original = _create_document(repos, _document_record(parser))
    node_ids = repos.ast_nodes().bulk_create_for_document(
        original,
        _node_records(original.document_key),
    )
    repos.ast_node_links().bulk_create_for_document(
        original,
        [
            AstLinkRecord(
                document_key=original.document_key,
                source_node_key="condition",
                link_type=AstLinkType.CALL_TARGET,
                target_id=node_ids["root"],
                resolution_type=AstResolutionType.RESOLVED,
                resolver_key="test",
                resolver_version="1",
                confidence=1.0,
            )
        ],
    )

    replacement_record = _document_record(parser, content_hash="sha256:replacement")
    replacement_payload = repos.ast_payloads().create_for_record(replacement_record)
    replacement = repos.ast_documents().replace_for_source(
        replacement_record,
        ast_payload_id=replacement_payload.id,
    )

    assert replacement.id != original.id
    assert session.scalar(select(func.count()).select_from(AstDocument)) == 1
    assert session.scalar(select(func.count()).select_from(AstNode)) == 2
    assert session.scalar(select(func.count()).select_from(AstNodeLink)) == 0


def test_scoped_delete_cannot_remove_another_project_document(
    session: Session,
    parser: ParserIdentity,
) -> None:
    repos = RepositoryFactory(session)
    repos.ast_parse_runs().create_from_record(_parse_run_record())
    document = _create_document(repos, _document_record(parser))

    removed = repos.ast_documents().delete_scoped(
        project_id="other-project",
        analysis_version_id="analysis-1",
        document_id=document.id,
    )

    assert removed == 0
    assert session.get(AstDocument, document.id) is document
