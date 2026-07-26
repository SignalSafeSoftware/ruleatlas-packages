"""Explicit migration from legacy claim-cited proposals to AST-cited candidates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ruleatlas_contracts.ast import AstNodeCitation

from ruleatlas_ai.synthesis.ast_proposal import (
    AstRuleEvidenceCitation,
    AstRuleProposal,
    ProductIntentStatus,
)
from ruleatlas_ai.synthesis.schema import (
    AI_RULE_SCHEMA_VERSION,
    AiRuleProposal,
    validate_proposal_payload,
)


@dataclass(frozen=True)
class LegacyProposalMigrationContext:
    observed_behavior: str
    product_intent_status: ProductIntentStatus
    ast_citations: tuple[AstNodeCitation, ...]
    supporting_evidence_citations: tuple[AstRuleEvidenceCitation, ...]
    provider_key: str
    model_id: str
    provider_schema_version: str
    prompt_schema_version: str
    confidence: float
    uncertainty: tuple[str, ...] = ()
    inferred_product_intent: str | None = None


def migrate_legacy_proposal(
    payload: dict[str, Any],
    *,
    context: LegacyProposalMigrationContext,
) -> AstRuleProposal:
    """Migrate facts only when the caller supplies new AST evidence and provenance."""

    legacy_payload = dict(payload)
    legacy_payload.setdefault("schema_version", AI_RULE_SCHEMA_VERSION)
    legacy, errors = validate_proposal_payload(legacy_payload)
    if legacy is None:
        raise ValueError(f"invalid legacy proposal: {'; '.join(errors)}")
    return _migrate_valid_legacy(legacy, context=context)


def _migrate_valid_legacy(
    legacy: AiRuleProposal,
    *,
    context: LegacyProposalMigrationContext,
) -> AstRuleProposal:
    return AstRuleProposal(
        canonical_rule_text=legacy.canonical_wording,
        observed_behavior=context.observed_behavior,
        product_intent_status=context.product_intent_status,
        inferred_product_intent=context.inferred_product_intent,
        actor=_required_legacy_fact(legacy.actor, "actor"),
        condition=_required_legacy_fact(legacy.condition, "condition"),
        action=_required_legacy_fact(legacy.action, "action"),
        result=_required_legacy_fact(legacy.outcome, "outcome"),
        exception=legacy.exceptions,
        ast_citations=list(context.ast_citations),
        supporting_evidence_citations=list(context.supporting_evidence_citations),
        confidence=context.confidence,
        confidence_explanation=legacy.confidence_explanation,
        uncertainty=list(context.uncertainty),
        provider_key=context.provider_key,
        model_id=context.model_id,
        provider_schema_version=context.provider_schema_version,
        prompt_schema_version=context.prompt_schema_version,
    )


def _required_legacy_fact(value: str | None, field_name: str) -> str:
    if value is None or not value.strip():
        raise ValueError(f"legacy proposal requires explicit {field_name} before migration")
    return value


__all__ = ["LegacyProposalMigrationContext", "migrate_legacy_proposal"]
