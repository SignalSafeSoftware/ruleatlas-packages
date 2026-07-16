"""Structured AI rule proposal schema and validation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError

AI_RULE_SCHEMA_VERSION = "1.0.0"


class AiRuleProposal(BaseModel):
    schema_version: str = AI_RULE_SCHEMA_VERSION
    canonical_wording: str = Field(min_length=8)
    actor: str | None = None
    condition: str | None = None
    action: str | None = None
    outcome: str | None = None
    exceptions: str | None = None
    scope: str | None = None
    domain: str | None = None
    threshold: str | None = None
    state: str | None = None
    timing: str | None = None
    object: str | None = None
    authority_status: str | None = None
    provenance_explanation: str | None = None
    cluster_role: str | None = None
    attached_exception_ids: list[str] = Field(default_factory=list)
    superseded_claim_ids: list[str] = Field(default_factory=list)
    supporting_claim_ids: list[str] = Field(default_factory=list)
    contradicting_claim_ids: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    confidence_explanation: str = Field(min_length=4)
    cluster_id: str | None = None


def validate_proposal_payload(payload: dict[str, Any]) -> tuple[AiRuleProposal | None, list[str]]:
    try:
        model = AiRuleProposal.model_validate(payload)
    except ValidationError as exc:
        return None, [e["msg"] for e in exc.errors()]
    errors: list[str] = []
    if not model.supporting_claim_ids and not model.supporting_evidence_ids:
        errors.append("Free-form uncited answers are rejected: supporting IDs required")
    if model.schema_version != AI_RULE_SCHEMA_VERSION:
        errors.append(f"Unsupported schema_version {model.schema_version}")
    if errors:
        return None, errors
    return model, []


def proposal_json_schema() -> dict:
    return AiRuleProposal.model_json_schema()
