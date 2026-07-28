"""Citation-required candidate rule proposal produced by AST investigation."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from ruleatlas_contracts.ast import AstNodeCitation, ExactSourceCitation

AST_RULE_SCHEMA_VERSION = "2.0.0"
AST_RULE_PROPOSAL_KIND = "candidate_rule"


class ProductIntentStatus(StrEnum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    NOT_ESTABLISHED = "not_established"


class AstRuleField(StrEnum):
    CANONICAL_RULE_TEXT = "canonical_rule_text"
    OBSERVED_BEHAVIOR = "observed_behavior"
    INFERRED_PRODUCT_INTENT = "inferred_product_intent"
    ACTOR = "actor"
    CONDITION = "condition"
    ACTION = "action"
    RESULT = "result"
    EXCEPTION = "exception"


class RuleEvidenceRole(StrEnum):
    IMPLEMENTATION = "implementation"
    PRODUCT_INTENT = "product_intent"
    VERIFICATION = "verification"
    EXCEPTION = "exception"
    COUNTEREVIDENCE = "counterevidence"


class AstRuleEvidenceCitation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    role: RuleEvidenceRole
    citation: ExactSourceCitation
    supports_fields: list[AstRuleField] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_fields(self) -> AstRuleEvidenceCitation:
        if len(set(self.supports_fields)) != len(self.supports_fields):
            raise ValueError("supports_fields must not contain duplicates")
        return self


class AstRuleProposal(BaseModel):
    """Untrusted candidate proposal; approval state is intentionally unrepresentable."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["2.0.0"] = "2.0.0"
    proposal_kind: Literal["candidate_rule"] = "candidate_rule"
    canonical_rule_text: str = Field(min_length=8)
    observed_behavior: str = Field(min_length=8)
    product_intent_status: ProductIntentStatus
    inferred_product_intent: str | None = None
    actor: str = Field(min_length=1)
    condition: str = Field(min_length=1)
    action: str = Field(min_length=1)
    result: str = Field(min_length=1)
    exception: str | None = None
    ast_citations: list[AstNodeCitation] = Field(min_length=1)
    supporting_evidence_citations: list[AstRuleEvidenceCitation] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_explanation: str = Field(min_length=4)
    uncertainty: list[str] = Field(default_factory=list)
    provider_key: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    provider_schema_version: str = Field(min_length=1)
    prompt_schema_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_product_intent_and_uncertainty(self) -> AstRuleProposal:
        intent = self.inferred_product_intent.strip() if self.inferred_product_intent is not None else None
        if self.product_intent_status == ProductIntentStatus.NOT_ESTABLISHED:
            if intent is not None:
                raise ValueError("inferred_product_intent must be absent when intent is not established")
        elif intent is None:
            raise ValueError("observed or inferred product intent requires inferred_product_intent")
        if any(not item.strip() for item in self.uncertainty):
            raise ValueError("uncertainty must not contain blank values")
        if self.confidence < 1.0 and not self.uncertainty:
            raise ValueError("confidence below 1.0 requires at least one uncertainty")
        return self


def validate_ast_proposal_payload(
    payload: dict[str, Any],
) -> tuple[AstRuleProposal | None, list[str]]:
    normalized = dict(payload)
    normalized["ast_citations"] = [
        _without_transport_kind(citation)
        for citation in payload.get("ast_citations", [])
    ]
    normalized["supporting_evidence_citations"] = [
        {
            **evidence,
            "citation": _without_transport_kind(evidence.get("citation")),
        }
        if isinstance(evidence, dict)
        else evidence
        for evidence in payload.get("supporting_evidence_citations", [])
    ]
    try:
        return AstRuleProposal.model_validate(normalized), []
    except ValidationError as exc:
        return None, [
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        ]


def _without_transport_kind(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    return {key: item for key, item in value.items() if key != "kind"}


def ast_proposal_json_schema() -> dict[str, Any]:
    return AstRuleProposal.model_json_schema()


__all__ = [
    "AST_RULE_PROPOSAL_KIND",
    "AST_RULE_SCHEMA_VERSION",
    "AstRuleEvidenceCitation",
    "AstRuleField",
    "AstRuleProposal",
    "ProductIntentStatus",
    "RuleEvidenceRole",
    "ast_proposal_json_schema",
    "validate_ast_proposal_payload",
]
