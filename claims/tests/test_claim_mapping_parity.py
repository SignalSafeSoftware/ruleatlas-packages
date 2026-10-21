"""Shared claim mapping retains each API's transaction and evidence boundaries."""

import pytest
from ruleatlas_contracts.claims import ClaimDraft
from ruleatlas_persistence.base import Base
from ruleatlas_persistence.models import SourceClaim, SourceClaimEvidence
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from ruleatlas_claims.claim_service import persist_claim, persist_claims


def snapshot(batch: bool) -> tuple[dict[str, object], list[dict[str, object]], int, int]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    commits: list[Session] = []
    refreshes: list[str] = []

    def refreshed(target: SourceClaim, _context: object, _attrs: object) -> None:
        refreshes.append(target.id)

    event.listen(SourceClaim, "refresh", refreshed)
    try:
        with Session(engine) as session:
            event.listen(session, "after_commit", commits.append)
            draft = ClaimDraft(
                claim_text="Require approval",
                provider_key="policy",
                claim_role="requirement",
                confidence=0.75,
                actor="reviewer",
                condition_text="ready",
                action_text="approve",
                result_text="approved",
                exception_text="deny",
                subject_text="invoice",
                state_transition="ready:approved",
                source_path="billing.py",
                start_line=3,
                end_line=5,
                provider_version="2",
                graph_node_id="node",
                attributes={"preserved": [1, False]},
                evidence=[
                    {"excerpt": "first", "graph_edge_id": "edge"},
                    {
                        "evidence_kind": "custom",
                        "reference_path": "other.py",
                        "start_line": 9,
                        "end_line": 10,
                        "graph_node_id": "other",
                        "attributes": {"nested": [0]},
                    },
                ],
            )
            if batch:
                row = persist_claims(session, project_id="p", analysis_version_id="a", scan_run_id="s", drafts=[draft])[
                    0
                ]
            else:
                row = persist_claim(session, project_id="p", analysis_version_id="a", scan_run_id="s", draft=draft)
            fields = {
                column.name: getattr(row, column.name)
                for column in SourceClaim.__table__.columns
                if column.name not in {"id", "created_at", "updated_at"}
            }
            evidence = [
                {
                    column.name: getattr(item, column.name)
                    for column in SourceClaimEvidence.__table__.columns
                    if column.name not in {"id", "source_claim_id", "created_at", "updated_at"}
                }
                for item in session.query(SourceClaimEvidence).order_by(SourceClaimEvidence.reference_path).all()
            ]
            return fields, evidence, len(commits), len(refreshes)
    finally:
        event.remove(SourceClaim, "refresh", refreshed)
        engine.dispose()


def test_single_and_batch_preserve_every_field_without_sharing_transaction_ownership() -> None:
    single, single_evidence, single_commits, single_refreshes = snapshot(False)
    batch, batch_evidence, batch_commits, batch_refreshes = snapshot(True)
    assert single == batch
    assert single_evidence == batch_evidence
    assert single["attributes_json"] == {"preserved": [1, False]}
    assert single_evidence[0]["reference_path"] == "billing.py"
    assert single_evidence[0]["evidence_kind"] == "source_span"
    assert single_evidence[1]["attributes_json"] == {"nested": [0]}
    assert (single_commits, single_refreshes) == (1, 1)
    assert (batch_commits, batch_refreshes) == (0, 0)


@pytest.mark.parametrize("batch", [False, True])
def test_evidence_construction_stays_lazy_with_original_failure_mutations(batch: bool) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        commits: list[Session] = []
        event.listen(session, "after_commit", commits.append)
        draft = ClaimDraft(
            claim_text="invalid evidence",
            provider_key="test",
            evidence=[
                {"excerpt": "first"},
                {"attributes": object()},
            ],
        )
        with pytest.raises(TypeError):
            if batch:
                persist_claims(session, project_id="p", analysis_version_id="a", scan_run_id=None, drafts=[draft])
            else:
                persist_claim(session, project_id="p", analysis_version_id="a", scan_run_id=None, draft=draft)
        pending = [item.excerpt for item in session.new if isinstance(item, SourceClaimEvidence)]
        assert pending == ([] if batch else ["first"])
        assert commits == []
    engine.dispose()
