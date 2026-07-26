"""Validation-gated adapter from AI proposals to the claims package input."""

from __future__ import annotations

import hashlib
import json

from ruleatlas_claims.ast_normalization import (
    AstProposalEvidenceInput,
    ValidatedAstProposalInput,
)
from ruleatlas_contracts.ast import AstCitationScope

from ruleatlas_ai.synthesis.ast_proposal import AstRuleProposal
from ruleatlas_ai.synthesis.ast_proposal_validation import (
    validate_ast_rule_proposal,
)

AST_PROPOSAL_VALIDATOR_KEY = "ruleatlas_ast_proposal"
AST_PROPOSAL_VALIDATOR_VERSION = "1.0.0"


def prepare_validated_ast_proposal_input(
    proposal: AstRuleProposal,
    *,
    expected_scope: AstCitationScope,
) -> ValidatedAstProposalInput:
    validation = validate_ast_rule_proposal(
        proposal,
        expected_scope=expected_scope,
    )
    if not validation.valid:
        codes = ", ".join(issue.code.value for issue in validation.issues)
        raise ValueError(f"AST proposal failed citation validation: {codes}")
    return ValidatedAstProposalInput(
        proposal_fingerprint=_proposal_fingerprint(proposal),
        schema_version=proposal.schema_version,
        canonical_rule_text=proposal.canonical_rule_text,
        observed_behavior=proposal.observed_behavior,
        product_intent_status=proposal.product_intent_status.value,
        inferred_product_intent=proposal.inferred_product_intent,
        actor=proposal.actor,
        condition=proposal.condition,
        action=proposal.action,
        result=proposal.result,
        exception=proposal.exception,
        ast_citations=tuple(proposal.ast_citations),
        evidence_citations=tuple(
            AstProposalEvidenceInput(
                role=evidence.role.value,
                citation=evidence.citation,
                supports_fields=tuple(value.value for value in evidence.supports_fields),
            )
            for evidence in proposal.supporting_evidence_citations
        ),
        confidence=proposal.confidence,
        confidence_explanation=proposal.confidence_explanation,
        uncertainty=tuple(proposal.uncertainty),
        provider_key=proposal.provider_key,
        model_id=proposal.model_id,
        provider_schema_version=proposal.provider_schema_version,
        prompt_schema_version=proposal.prompt_schema_version,
        validator_key=AST_PROPOSAL_VALIDATOR_KEY,
        validator_version=AST_PROPOSAL_VALIDATOR_VERSION,
    )


def _proposal_fingerprint(proposal: AstRuleProposal) -> str:
    encoded = json.dumps(
        proposal.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


__all__ = [
    "AST_PROPOSAL_VALIDATOR_KEY",
    "AST_PROPOSAL_VALIDATOR_VERSION",
    "prepare_validated_ast_proposal_input",
]
