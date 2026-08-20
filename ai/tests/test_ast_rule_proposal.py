"""Tests for citation-required AST rule proposals and legacy migration."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from ruleatlas_contracts.ast import (
    AstCitationScope,
    AstNodeCitation,
    AstPoint,
    AstSourceRange,
    ExactSourceCitation,
    ParserIdentity,
)

from ruleatlas_ai.synthesis import (
    AI_RULE_SCHEMA_VERSION,
    AST_RULE_SCHEMA_VERSION,
    AstRuleEvidenceCitation,
    AstRuleField,
    AstRuleProposal,
    LegacyProposalMigrationContext,
    ProductIntentStatus,
    RuleEvidenceRole,
    ast_proposal_json_schema,
    migrate_legacy_proposal,
    prepare_validated_ast_proposal_input,
    validate_ast_proposal_payload,
)


def _range() -> AstSourceRange:
    return AstSourceRange(0, 20, AstPoint(0, 0), AstPoint(0, 20))


def _source_citation() -> ExactSourceCitation:
    return ExactSourceCitation(
        scope=AstCitationScope("project-1", "analysis-1"),
        source_file_id="file-1",
        source_path="src/approval.py",
        content_hash="sha256:source",
        source_range=_range(),
        excerpt_hash="sha256:excerpt",
    )


def _node_citation() -> AstNodeCitation:
    return AstNodeCitation(
        scope=AstCitationScope("project-1", "analysis-1"),
        document_key="src/approval.py:sha256:source",
        node_key="node-condition",
        source_file_id="file-1",
        source_path="src/approval.py",
        content_hash="sha256:source",
        subtree_hash="sha256:subtree",
        source_range=_range(),
        parser=ParserIdentity(
            parser_key="tree_sitter",
            parser_version="0.26.0",
            language_key="python",
            grammar_key="tree-sitter-python",
            grammar_version="0.25.0",
        ),
        raw_node_type="if_statement",
        field_name="condition",
    )


def _evidence_citation() -> AstRuleEvidenceCitation:
    return AstRuleEvidenceCitation(
        role=RuleEvidenceRole.IMPLEMENTATION,
        citation=_source_citation(),
        supports_fields=list(AstRuleField),
    )


def _payload() -> dict[str, object]:
    return {
        "schema_version": AST_RULE_SCHEMA_VERSION,
        "proposal_kind": "candidate_rule",
        "canonical_rule_text": ("Managers must approve invoices over $10,000 before submission."),
        "observed_behavior": ("The submission branch calls manager approval when total exceeds $10,000."),
        "product_intent_status": "inferred",
        "inferred_product_intent": ("High-value invoices require managerial authorization."),
        "actor": "manager",
        "condition": "an invoice total exceeds $10,000",
        "action": "approve the invoice",
        "result": "submission may continue",
        "exception": None,
        "ast_citations": [_node_citation()],
        "supporting_evidence_citations": [_evidence_citation()],
        "confidence": 0.85,
        "confidence_explanation": "The condition and approval call are explicit.",
        "uncertainty": ["No product requirements document was available."],
        "provider_key": "openai",
        "model_id": "example-model",
        "provider_schema_version": "responses-v1",
        "prompt_schema_version": "ast-rule-v1",
    }


def test_valid_ast_proposal_preserves_observation_intent_and_provenance() -> None:
    proposal, errors = validate_ast_proposal_payload(_payload())

    assert errors == []
    assert proposal is not None
    assert proposal.schema_version == "2.0.0"
    assert proposal.product_intent_status == ProductIntentStatus.INFERRED
    assert proposal.ast_citations[0].node_key == "node-condition"
    assert proposal.provider_key == "openai"


def test_serialized_transport_citations_accept_kind_discriminators() -> None:
    payload = _payload()
    payload["ast_citations"] = [
        payload["ast_citations"][0].to_dict()  # type: ignore[index, union-attr]
    ]
    evidence = payload["supporting_evidence_citations"][0]  # type: ignore[index]
    payload["supporting_evidence_citations"] = [
        {
            "role": evidence.role,  # type: ignore[union-attr]
            "citation": evidence.citation.to_dict(),  # type: ignore[union-attr]
            "supports_fields": evidence.supports_fields,  # type: ignore[union-attr]
        }
    ]

    proposal, errors = validate_ast_proposal_payload(payload)

    assert errors == []
    assert proposal is not None
    assert proposal.ast_citations[0].node_key == "node-condition"


def test_ast_and_supporting_citations_are_both_required() -> None:
    for field_name in ("ast_citations", "supporting_evidence_citations"):
        payload = _payload()
        payload[field_name] = []

        proposal, errors = validate_ast_proposal_payload(payload)

        assert proposal is None
        assert any("at least 1" in error.lower() for error in errors)


def test_product_intent_status_cannot_overstate_inference() -> None:
    payload = _payload()
    payload["product_intent_status"] = "not_established"

    proposal, errors = validate_ast_proposal_payload(payload)

    assert proposal is None
    assert any("must be absent" in error for error in errors)

    payload["inferred_product_intent"] = None
    proposal, errors = validate_ast_proposal_payload(payload)
    assert errors == []
    assert proposal is not None


def test_confidence_below_one_requires_uncertainty() -> None:
    payload = _payload()
    payload["uncertainty"] = []

    proposal, errors = validate_ast_proposal_payload(payload)

    assert proposal is None
    assert any("requires at least one uncertainty" in error for error in errors)


@pytest.mark.parametrize(
    "forbidden_field",
    ["status", "approved", "approval_status", "auto_approve"],
)
def test_approval_state_is_impossible_to_express(forbidden_field: str) -> None:
    payload = _payload()
    payload[forbidden_field] = "approved"

    proposal, errors = validate_ast_proposal_payload(payload)

    assert proposal is None
    assert any("extra inputs are not permitted" in error.lower() for error in errors)


def test_schema_exposes_required_citations_and_no_approval_field() -> None:
    schema = ast_proposal_json_schema()
    properties = schema["properties"]

    assert "ast_citations" in schema["required"]
    assert "supporting_evidence_citations" in schema["required"]
    assert "status" not in properties
    assert "approved" not in properties
    assert properties["schema_version"]["const"] == AST_RULE_SCHEMA_VERSION


def test_legacy_proposal_requires_explicit_evidence_to_migrate() -> None:
    legacy = {
        "schema_version": AI_RULE_SCHEMA_VERSION,
        "canonical_wording": "Invoices over $10,000 require manager approval.",
        "actor": "manager",
        "condition": "invoice total exceeds $10,000",
        "action": "approve invoice",
        "outcome": "submission continues",
        "confidence_explanation": "Legacy claim evidence supported this.",
        "supporting_claim_ids": ["claim-1"],
    }
    context = LegacyProposalMigrationContext(
        observed_behavior=("A conditional branch calls approval for invoices over $10,000."),
        product_intent_status=ProductIntentStatus.INFERRED,
        inferred_product_intent="High-value invoices require manager approval.",
        ast_citations=(_node_citation(),),
        supporting_evidence_citations=(_evidence_citation(),),
        provider_key="openai",
        model_id="example-model",
        provider_schema_version="responses-v1",
        prompt_schema_version="ast-rule-v1",
        confidence=0.8,
        uncertainty=("Legacy intent was inferred from implementation.",),
    )

    migrated = migrate_legacy_proposal(legacy, context=context)

    assert isinstance(migrated, AstRuleProposal)
    assert migrated.schema_version == AST_RULE_SCHEMA_VERSION
    assert migrated.canonical_rule_text == legacy["canonical_wording"]
    assert migrated.ast_citations == [_node_citation()]

    missing_ast_context = LegacyProposalMigrationContext(
        observed_behavior=context.observed_behavior,
        product_intent_status=context.product_intent_status,
        inferred_product_intent=context.inferred_product_intent,
        ast_citations=(),
        supporting_evidence_citations=context.supporting_evidence_citations,
        provider_key=context.provider_key,
        model_id=context.model_id,
        provider_schema_version=context.provider_schema_version,
        prompt_schema_version=context.prompt_schema_version,
        confidence=context.confidence,
        uncertainty=context.uncertainty,
    )
    with pytest.raises(ValidationError):
        migrate_legacy_proposal(legacy, context=missing_ast_context)


def test_invalid_legacy_proposal_cannot_be_migrated() -> None:
    invalid_context = LegacyProposalMigrationContext(
        observed_behavior="Observed behavior is available.",
        product_intent_status=ProductIntentStatus.NOT_ESTABLISHED,
        ast_citations=(_node_citation(),),
        supporting_evidence_citations=(_evidence_citation(),),
        provider_key="openai",
        model_id="example-model",
        provider_schema_version="responses-v1",
        prompt_schema_version="ast-rule-v1",
        confidence=1.0,
    )
    with pytest.raises(ValueError, match="invalid legacy proposal"):
        migrate_legacy_proposal(
            {"schema_version": AI_RULE_SCHEMA_VERSION},
            context=invalid_context,
        )


def test_migration_does_not_invent_missing_structured_facts() -> None:
    legacy = {
        "schema_version": AI_RULE_SCHEMA_VERSION,
        "canonical_wording": "Invoices over $10,000 require manager approval.",
        "confidence_explanation": "Legacy evidence supported this.",
        "supporting_claim_ids": ["claim-1"],
    }
    context = LegacyProposalMigrationContext(
        observed_behavior="Approval is called above the threshold.",
        product_intent_status=ProductIntentStatus.NOT_ESTABLISHED,
        ast_citations=(_node_citation(),),
        supporting_evidence_citations=(_evidence_citation(),),
        provider_key="openai",
        model_id="example-model",
        provider_schema_version="responses-v1",
        prompt_schema_version="ast-rule-v1",
        confidence=1.0,
    )

    with pytest.raises(ValueError, match="requires explicit actor"):
        migrate_legacy_proposal(legacy, context=context)


def test_claims_adapter_only_emits_input_after_pure_validation() -> None:
    proposal = AstRuleProposal.model_validate(_payload())

    normalized_input = prepare_validated_ast_proposal_input(
        proposal,
        expected_scope=AstCitationScope("project-1", "analysis-1"),
    )

    assert normalized_input.proposal_fingerprint.startswith("sha256:")
    assert normalized_input.validator_key == "ruleatlas_ast_proposal"
    assert normalized_input.ast_citations == (_node_citation(),)

    invalid_evidence = _evidence_citation().model_copy(update={"supports_fields": [AstRuleField.OBSERVED_BEHAVIOR]})
    invalid = proposal.model_copy(update={"supporting_evidence_citations": [invalid_evidence]})
    expected_scope = AstCitationScope("project-1", "analysis-1")
    with pytest.raises(ValueError, match="failed citation validation"):
        prepare_validated_ast_proposal_input(invalid, expected_scope=expected_scope)
