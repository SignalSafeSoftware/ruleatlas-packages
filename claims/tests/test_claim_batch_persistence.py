"""Regression coverage for batched source-claim persistence."""

from __future__ import annotations

import ruleatlas_persistence.models  # noqa: F401
from ruleatlas_contracts.claims import ClaimDraft
from ruleatlas_persistence.base import Base
from ruleatlas_persistence.models import SourceClaim, SourceClaimEvidence
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from ruleatlas_claims.claim_service import persist_claims


def test_persist_claims_prefetches_existing_rows_and_keeps_first_duplicate_evidence() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    statements: list[str] = []

    def record_statement(conn, cursor, statement, parameters, context, executemany) -> None:
        del conn, cursor, parameters, context, executemany
        statements.append(statement)

    drafts = [
        ClaimDraft(
            claim_text="The invoice must be approved.",
            provider_key="test",
            source_path="billing.py",
            start_line=3,
            evidence=[{"evidence_kind": "source_span", "reference_path": "billing.py"}],
        ),
        ClaimDraft(
            claim_text="The invoice must be approved.",
            provider_key="test",
            source_path="billing.py",
            start_line=3,
            evidence=[{"evidence_kind": "duplicate", "reference_path": "ignored.py"}],
        ),
        ClaimDraft(
            claim_text="The invoice must be paid.",
            provider_key="test",
            source_path="billing.py",
            start_line=4,
            evidence=[{"evidence_kind": "source_span", "reference_path": "billing.py"}],
        ),
    ]
    try:
        event.listen(session.bind, "before_cursor_execute", record_statement)
        try:
            rows = persist_claims(
                session,
                project_id="project-id",
                analysis_version_id="analysis-id",
                scan_run_id=None,
                drafts=drafts,
            )
        finally:
            event.remove(session.bind, "before_cursor_execute", record_statement)

        assert rows[0] is rows[1]
        assert len(session.query(SourceClaim).all()) == 2
        evidence = session.query(SourceClaimEvidence).all()
        assert len(evidence) == 2
        assert {row.evidence_kind for row in evidence} == {"source_span"}
        source_claim_selects = [
            statement.lower()
            for statement in statements
            if statement.lstrip().upper().startswith("SELECT") and "source_claims" in statement
        ]
        assert len(source_claim_selects) == 1
    finally:
        session.close()
        Base.metadata.drop_all(engine)
