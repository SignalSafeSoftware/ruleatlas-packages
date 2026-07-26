"""Tests for normalization and deduplication of validated AST proposals."""

from __future__ import annotations

import pytest
from ruleatlas_contracts.ast import (
    AstCitationScope,
    AstNodeCitation,
    AstPoint,
    AstSourceRange,
    ExactSourceCitation,
    ParserIdentity,
)
from ruleatlas_contracts.enums import SourceClaimRole

from ruleatlas_claims.ast_normalization import (
    AST_PROPOSAL_PROVIDER_KEY,
    AstProposalEvidenceInput,
    ValidatedAstProposalInput,
    deduplicate_normalized_ast_claims,
    normalize_validated_ast_proposal,
)


def _range(start: int = 0, end: int = 20) -> AstSourceRange:
    return AstSourceRange(start, end, AstPoint(0, start), AstPoint(0, end))


def _node_citation(
    node_key: str = "node-1",
    *,
    source_file_id: str = "file-1",
) -> AstNodeCitation:
    return AstNodeCitation(
        scope=AstCitationScope("project-1", "analysis-1"),
        document_key=f"src/{source_file_id}.py:sha256:{source_file_id}",
        node_key=node_key,
        source_file_id=source_file_id,
        source_path=f"src/{source_file_id}.py",
        content_hash=f"sha256:{source_file_id}",
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


def _evidence(
    role: str = "implementation",
    *,
    source_file_id: str = "file-1",
) -> AstProposalEvidenceInput:
    return AstProposalEvidenceInput(
        role=role,
        citation=ExactSourceCitation(
            scope=AstCitationScope("project-1", "analysis-1"),
            source_file_id=source_file_id,
            source_path=f"src/{source_file_id}.py",
            content_hash=f"sha256:{source_file_id}",
            source_range=_range(),
            excerpt_hash=f"sha256:excerpt-{source_file_id}",
        ),
        supports_fields=(
            "canonical_rule_text",
            "observed_behavior",
            "actor",
            "condition",
            "action",
            "result",
        ),
    )


def _proposal(
    *,
    fingerprint: str = "sha256:proposal-1",
    observed_behavior: str = "A threshold branch invokes manager approval.",
    product_intent_status: str = "inferred",
    inferred_product_intent: str | None = ("High-value invoices require manager approval."),
    ast_citations: tuple[AstNodeCitation, ...] | None = None,
    evidence: tuple[AstProposalEvidenceInput, ...] | None = None,
    confidence: float = 0.8,
) -> ValidatedAstProposalInput:
    return ValidatedAstProposalInput(
        proposal_fingerprint=fingerprint,
        schema_version="2.0.0",
        canonical_rule_text=("Managers must approve invoices over $10,000 before submission."),
        observed_behavior=observed_behavior,
        product_intent_status=product_intent_status,
        inferred_product_intent=inferred_product_intent,
        actor="manager",
        condition="invoice total exceeds $10,000",
        action="approve invoice",
        result="submission continues",
        exception=None,
        ast_citations=(ast_citations if ast_citations is not None else (_node_citation(),)),
        evidence_citations=(evidence if evidence is not None else (_evidence(),)),
        confidence=confidence,
        confidence_explanation="The threshold and call are explicit.",
        uncertainty=("Product intent is inferred.",),
        provider_key="openai",
        model_id="example-model",
        provider_schema_version="responses-v1",
        prompt_schema_version="ast-rule-v1",
        validator_key="ruleatlas_ast_proposal",
        validator_version="1.0.0",
    )


def test_inferred_intent_remains_metadata_not_product_intent_claim() -> None:
    normalized = normalize_validated_ast_proposal(_proposal())

    assert len(normalized.claims) == 1
    implementation = normalized.implementation_claim
    assert implementation.draft.claim_role == SourceClaimRole.IMPLEMENTATION.value
    assert implementation.draft.attributes["product_intent_status"] == "inferred"
    assert implementation.draft.attributes["inferred_product_intent"] == "High-value invoices require manager approval."
    assert implementation.draft.provider_key == AST_PROPOSAL_PROVIDER_KEY
    assert implementation.draft.attributes["never_auto_approve"] is True


def test_observed_intent_emits_a_separate_product_intent_claim() -> None:
    proposal = _proposal(
        product_intent_status="observed",
        evidence=(
            _evidence(),
            _evidence("product_intent", source_file_id="requirements"),
        ),
    )

    normalized = normalize_validated_ast_proposal(proposal)

    assert len(normalized.claims) == 2
    intent = normalized.product_intent_claim
    assert intent is not None
    assert intent.draft.claim_role == SourceClaimRole.PRODUCT_INTENT.value
    assert intent.ast_citation_ids == ()
    assert len(intent.evidence_citation_ids) == 1
    assert {item["role"] for item in intent.draft.evidence} == {"product_intent"}


def test_citation_ids_and_origin_metadata_are_stable_and_retained() -> None:
    first = normalize_validated_ast_proposal(_proposal())
    second = normalize_validated_ast_proposal(_proposal())
    claim = first.implementation_claim

    assert claim.ast_citation_ids == second.implementation_claim.ast_citation_ids
    assert claim.evidence_citation_ids == second.implementation_claim.evidence_citation_ids
    assert claim.origins[0].provider_key == "openai"
    assert claim.origins[0].model_id == "example-model"
    assert claim.origins[0].validator_key == "ruleatlas_ast_proposal"


def test_equivalent_claims_merge_without_losing_citations_or_origins() -> None:
    first = normalize_validated_ast_proposal(_proposal()).implementation_claim
    second = normalize_validated_ast_proposal(
        _proposal(
            fingerprint="sha256:proposal-2",
            ast_citations=(_node_citation("node-2", source_file_id="file-2"),),
            evidence=(_evidence(source_file_id="file-2"),),
            confidence=0.9,
        )
    ).implementation_claim

    merged = deduplicate_normalized_ast_claims([first, second])

    assert len(merged) == 1
    assert len(merged[0].ast_citation_ids) == 2
    assert len(merged[0].evidence_citation_ids) == 2
    assert len(merged[0].origins) == 2
    assert merged[0].draft.confidence == 0.9
    assert len(merged[0].draft.evidence) == 2


def test_same_wording_with_distinct_observed_behavior_is_not_collapsed() -> None:
    first = normalize_validated_ast_proposal(_proposal()).implementation_claim
    second = normalize_validated_ast_proposal(
        _proposal(
            fingerprint="sha256:proposal-2",
            observed_behavior=("A batch import rejects the invoice before approval can run."),
        )
    ).implementation_claim

    deduplicated = deduplicate_normalized_ast_claims([first, second])

    assert len(deduplicated) == 2
    assert first.deduplication_key != second.deduplication_key


def test_input_rejects_unvalidated_shapes_and_unknown_roles() -> None:
    with pytest.raises(ValueError, match="AST and evidence citations"):
        _proposal(ast_citations=(), evidence=())
    with pytest.raises(ValueError, match="unsupported evidence role"):
        _evidence("invented-role")
