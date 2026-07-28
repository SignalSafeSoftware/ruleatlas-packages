from ruleatlas_claims.structured_semantics import StructuredSemantics

from ruleatlas_ai.synthesis.proposal_validation import unsupported_grounding_terms
from ruleatlas_ai.synthesis.schema import AiRuleProposal
from ruleatlas_ai.synthesis.wording_normalize import normalize_canonical_wording


def test_paid_invoice_policy_is_not_grounded_by_a_deleted_column_rename() -> None:
    unsupported = unsupported_grounding_terms(
        "Paid invoices cannot be deleted, except through the documented "
        "administrator correction workflow.",
        ['("deleted_at", "deleted_on"),'],
    )

    assert {"paid", "invoices", "administrator", "correction", "workflow"} <= set(unsupported)
    assert "deleted" not in unsupported


def test_grounding_accepts_supported_wording_with_simple_morphology() -> None:
    unsupported = unsupported_grounding_terms(
        "Administrators may delete inactive records.",
        ["An administrator can delete an inactive record."],
    )

    assert unsupported == []


def test_generic_delete_rule_is_not_rewritten_as_paid_invoice_policy() -> None:
    proposal = AiRuleProposal(
        canonical_wording="Admin users can delete records.",
        actor="admin",
        action="delete records",
        supporting_claim_ids=["claim-1"],
        confidence_explanation="Grounded by an administrator deletion implementation.",
    )

    normalized = normalize_canonical_wording(
        proposal,
        StructuredSemantics(
            actor="admin",
            action="delete records",
            action_family="delete",
            object="record",
            authority_status="current",
        ),
    )

    assert normalized.canonical_wording == "Admin users can delete records."
    assert "invoice" not in normalized.canonical_wording.lower()
