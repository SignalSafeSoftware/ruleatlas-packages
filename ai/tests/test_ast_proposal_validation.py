"""Pure validation tests for AST-backed rule-proposal citations."""

from __future__ import annotations

from ruleatlas_contracts.ast import (
    AstCitationScope,
    AstNodeCitation,
    AstPoint,
    AstSourceRange,
    ExactSourceCitation,
    ParserIdentity,
)

from ruleatlas_ai.synthesis import (
    AstProposalValidationCode,
    AstRuleEvidenceCitation,
    AstRuleField,
    AstRuleProposal,
    ProductIntentStatus,
    RuleEvidenceRole,
    validate_ast_rule_proposal,
)


def _scope(
    project_id: str = "project-1",
    analysis_version_id: str = "analysis-1",
) -> AstCitationScope:
    return AstCitationScope(project_id, analysis_version_id)


def _range(start: int = 0, end: int = 20) -> AstSourceRange:
    return AstSourceRange(start, end, AstPoint(0, start), AstPoint(0, end))


def _node_citation(
    node_key: str = "node-1",
    *,
    scope: AstCitationScope | None = None,
) -> AstNodeCitation:
    return AstNodeCitation(
        scope=scope or _scope(),
        document_key="src/approval.py:sha256:source",
        node_key=node_key,
        source_file_id="file-1",
        source_path="src/approval.py",
        content_hash="sha256:source",
        subtree_hash=f"sha256:{node_key}",
        source_range=_range(),
        parser=ParserIdentity(
            parser_key="tree_sitter",
            parser_version="0.26.0",
            language_key="python",
            grammar_key="tree-sitter-python",
            grammar_version="0.25.0",
        ),
        raw_node_type="if_statement",
    )


def _source_citation(
    source_file_id: str = "file-1",
    *,
    scope: AstCitationScope | None = None,
    start: int = 0,
    end: int = 20,
) -> ExactSourceCitation:
    return ExactSourceCitation(
        scope=scope or _scope(),
        source_file_id=source_file_id,
        source_path=f"src/{source_file_id}.py",
        content_hash=f"sha256:{source_file_id}",
        source_range=_range(start, end),
        excerpt_hash=f"sha256:excerpt-{source_file_id}-{start}",
    )


def _evidence(
    role: RuleEvidenceRole = RuleEvidenceRole.IMPLEMENTATION,
    *,
    citation: ExactSourceCitation | None = None,
    supports_fields: list[AstRuleField] | None = None,
) -> AstRuleEvidenceCitation:
    return AstRuleEvidenceCitation(
        role=role,
        citation=citation or _source_citation(),
        supports_fields=supports_fields or list(AstRuleField),
    )


def _proposal(
    *,
    ast_citations: list[AstNodeCitation] | None = None,
    evidence: list[AstRuleEvidenceCitation] | None = None,
    product_intent_status: ProductIntentStatus = ProductIntentStatus.INFERRED,
    inferred_product_intent: str | None = "High-value invoices require approval.",
    canonical_rule_text: str = ("Managers must approve invoices over $10,000 before submission."),
) -> AstRuleProposal:
    return AstRuleProposal(
        canonical_rule_text=canonical_rule_text,
        observed_behavior="A threshold branch invokes manager approval.",
        product_intent_status=product_intent_status,
        inferred_product_intent=inferred_product_intent,
        actor="manager",
        condition="invoice total exceeds $10,000",
        action="approve invoice",
        result="submission continues",
        exception=None,
        ast_citations=ast_citations or [_node_citation()],
        supporting_evidence_citations=evidence or [_evidence()],
        confidence=0.9,
        confidence_explanation="The condition and approval call are explicit.",
        uncertainty=["No requirements document was available."],
        provider_key="openai",
        model_id="example-model",
        provider_schema_version="responses-v1",
        prompt_schema_version="ast-rule-v1",
    )


def _codes(
    proposal: AstRuleProposal,
    *,
    expected_scope: AstCitationScope | None = None,
    allowed_evidence_roles: frozenset[RuleEvidenceRole] | None = None,
) -> list[AstProposalValidationCode]:
    return [
        issue.code
        for issue in validate_ast_rule_proposal(
            proposal,
            expected_scope=expected_scope,
            allowed_evidence_roles=allowed_evidence_roles,
        ).issues
    ]


def test_complete_scoped_proposal_is_valid() -> None:
    result = validate_ast_rule_proposal(
        _proposal(),
        expected_scope=_scope(),
    )

    assert result.valid
    assert result.to_dict()["issues"] == []


def test_duplicate_ast_and_source_citations_are_rejected() -> None:
    node = _node_citation()
    evidence = _evidence()
    proposal = _proposal(
        ast_citations=[node, node],
        evidence=[evidence, evidence],
    )

    codes = _codes(proposal)

    assert AstProposalValidationCode.DUPLICATE_AST_CITATION in codes
    assert AstProposalValidationCode.DUPLICATE_EVIDENCE_CITATION in codes


def test_all_citations_must_share_the_trusted_scope() -> None:
    other_scope = _scope("other-project", "analysis-2")
    proposal = _proposal(
        evidence=[
            _evidence(citation=_source_citation(scope=other_scope)),
        ]
    )

    codes = _codes(proposal, expected_scope=_scope())

    assert AstProposalValidationCode.SCOPE_MISMATCH in codes


def test_allowed_roles_and_required_implementation_role_are_enforced() -> None:
    verification = _evidence(
        RuleEvidenceRole.VERIFICATION,
        citation=_source_citation("test-file"),
    )
    proposal = _proposal(evidence=[verification])

    codes = _codes(
        proposal,
        allowed_evidence_roles=frozenset({RuleEvidenceRole.IMPLEMENTATION}),
    )

    assert AstProposalValidationCode.DISALLOWED_EVIDENCE_ROLE in codes
    assert AstProposalValidationCode.MISSING_IMPLEMENTATION_EVIDENCE in codes


def test_observed_product_intent_requires_product_intent_evidence() -> None:
    proposal = _proposal(
        product_intent_status=ProductIntentStatus.OBSERVED,
        inferred_product_intent="A policy explicitly requires approval.",
    )

    assert AstProposalValidationCode.MISSING_PRODUCT_INTENT_EVIDENCE in _codes(proposal)


def test_every_claimed_rule_field_requires_supporting_citation_coverage() -> None:
    evidence = _evidence(
        supports_fields=[AstRuleField.OBSERVED_BEHAVIOR],
    )
    proposal = _proposal(evidence=[evidence])

    result = validate_ast_rule_proposal(proposal)
    uncited_fields = {
        issue.field_name for issue in result.issues if issue.code == AstProposalValidationCode.UNCITED_PROPOSAL_FIELD
    }

    assert AstRuleField.ACTION.value in uncited_fields
    assert AstRuleField.CANONICAL_RULE_TEXT.value in uncited_fields
    assert AstRuleField.OBSERVED_BEHAVIOR.value not in uncited_fields


def test_counterevidence_does_not_count_as_positive_field_support() -> None:
    counterevidence = _evidence(
        RuleEvidenceRole.COUNTEREVIDENCE,
        supports_fields=list(AstRuleField),
    )
    proposal = _proposal(evidence=[counterevidence])

    codes = _codes(proposal)

    assert AstProposalValidationCode.MISSING_IMPLEMENTATION_EVIDENCE in codes
    assert AstProposalValidationCode.UNCITED_PROPOSAL_FIELD in codes


def test_exception_role_cannot_claim_unrelated_field_coverage() -> None:
    exception_evidence = _evidence(
        RuleEvidenceRole.EXCEPTION,
        supports_fields=[AstRuleField.ACTION],
    )
    proposal = _proposal(
        evidence=[_evidence(), exception_evidence],
    )

    assert AstProposalValidationCode.INVALID_ROLE_COVERAGE in _codes(proposal)


def test_business_approval_language_is_allowed_but_meta_approval_is_rejected() -> None:
    business_approval = _proposal()
    meta_approval = _proposal(
        canonical_rule_text=("This candidate rule is approved by a human reviewer and may be published.")
    )

    assert AstProposalValidationCode.UNSUPPORTED_APPROVAL_ASSERTION not in _codes(business_approval)
    assert AstProposalValidationCode.UNSUPPORTED_APPROVAL_ASSERTION in _codes(meta_approval)


def test_validator_is_pure_and_deterministic() -> None:
    proposal = _proposal()

    first = validate_ast_rule_proposal(proposal).to_dict()
    second = validate_ast_rule_proposal(proposal).to_dict()

    assert first == second
