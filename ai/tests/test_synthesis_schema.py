"""AI rule-proposal schema validation (candidate rules must be cited)."""

from __future__ import annotations

from ruleatlas_ai.synthesis.schema import proposal_json_schema, validate_proposal_payload


def test_valid_cited_proposal() -> None:
    model, errors = validate_proposal_payload(
        {
            "canonical_wording": "Invoices over $10,000 require manager approval",
            "confidence_explanation": "cited by billing/approvals.py",
            "supporting_claim_ids": ["claim-1"],
        }
    )
    assert errors == []
    assert model is not None
    assert model.canonical_wording.startswith("Invoices")


def test_uncited_proposal_rejected() -> None:
    model, errors = validate_proposal_payload(
        {
            "canonical_wording": "Invoices require approval",
            "confidence_explanation": "cited",
        }
    )
    assert model is None
    assert any("supporting" in e.lower() or "uncited" in e.lower() for e in errors)


def test_missing_required_fields_rejected() -> None:
    model, errors = validate_proposal_payload({})
    assert model is None
    assert errors


def test_json_schema_is_exposed() -> None:
    schema = proposal_json_schema()
    assert isinstance(schema, dict)
    assert "properties" in schema
    assert "canonical_wording" in schema["properties"]
