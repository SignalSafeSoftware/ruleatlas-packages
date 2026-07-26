"""Normalize citation-validated AST proposals into the claim intermediate representation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace

from ruleatlas_contracts.ast import AstNodeCitation, ExactSourceCitation
from ruleatlas_contracts.claims import ClaimDraft
from ruleatlas_contracts.enums import SourceClaimRole

from ruleatlas_claims.text_normalize import normalize_rule_text

AST_PROPOSAL_PROVIDER_KEY = "ai_ast_investigation"
_INTENT_STATUSES = frozenset({"observed", "inferred", "not_established"})
_EVIDENCE_ROLES = frozenset({"implementation", "product_intent", "verification", "exception", "counterevidence"})


def _require_non_blank(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")


@dataclass(frozen=True)
class AstProposalEvidenceInput:
    role: str
    citation: ExactSourceCitation
    supports_fields: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.role not in _EVIDENCE_ROLES:
            raise ValueError(f"unsupported evidence role: {self.role}")
        if not self.supports_fields:
            raise ValueError("supports_fields must not be empty")
        if any(not value.strip() for value in self.supports_fields):
            raise ValueError("supports_fields must not contain blank values")


@dataclass(frozen=True)
class ValidatedAstProposalInput:
    """AI-independent input created only after proposal validation succeeds."""

    proposal_fingerprint: str
    schema_version: str
    canonical_rule_text: str
    observed_behavior: str
    product_intent_status: str
    inferred_product_intent: str | None
    actor: str
    condition: str
    action: str
    result: str
    exception: str | None
    ast_citations: tuple[AstNodeCitation, ...]
    evidence_citations: tuple[AstProposalEvidenceInput, ...]
    confidence: float
    confidence_explanation: str
    uncertainty: tuple[str, ...]
    provider_key: str
    model_id: str
    provider_schema_version: str
    prompt_schema_version: str
    validator_key: str
    validator_version: str

    def __post_init__(self) -> None:
        for field_name, value in {
            "proposal_fingerprint": self.proposal_fingerprint,
            "schema_version": self.schema_version,
            "canonical_rule_text": self.canonical_rule_text,
            "observed_behavior": self.observed_behavior,
            "actor": self.actor,
            "condition": self.condition,
            "action": self.action,
            "result": self.result,
            "confidence_explanation": self.confidence_explanation,
            "provider_key": self.provider_key,
            "model_id": self.model_id,
            "provider_schema_version": self.provider_schema_version,
            "prompt_schema_version": self.prompt_schema_version,
            "validator_key": self.validator_key,
            "validator_version": self.validator_version,
        }.items():
            _require_non_blank(value, field_name)
        if self.product_intent_status not in _INTENT_STATUSES:
            raise ValueError(f"unsupported product_intent_status: {self.product_intent_status}")
        if not self.ast_citations or not self.evidence_citations:
            raise ValueError("validated proposals require AST and evidence citations")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")


@dataclass(frozen=True)
class AstClaimOrigin:
    proposal_fingerprint: str
    schema_version: str
    provider_key: str
    model_id: str
    provider_schema_version: str
    prompt_schema_version: str
    validator_key: str
    validator_version: str
    observed_behavior: str
    product_intent_status: str
    inferred_product_intent: str | None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "proposal_fingerprint": self.proposal_fingerprint,
            "schema_version": self.schema_version,
            "provider_key": self.provider_key,
            "model_id": self.model_id,
            "provider_schema_version": self.provider_schema_version,
            "prompt_schema_version": self.prompt_schema_version,
            "validator_key": self.validator_key,
            "validator_version": self.validator_version,
            "observed_behavior": self.observed_behavior,
            "product_intent_status": self.product_intent_status,
            "inferred_product_intent": self.inferred_product_intent,
        }


@dataclass(frozen=True)
class NormalizedAstClaim:
    draft: ClaimDraft
    deduplication_key: str
    ast_citation_ids: tuple[str, ...]
    evidence_citation_ids: tuple[str, ...]
    origins: tuple[AstClaimOrigin, ...]


@dataclass(frozen=True)
class NormalizedAstProposal:
    implementation_claim: NormalizedAstClaim
    product_intent_claim: NormalizedAstClaim | None

    @property
    def claims(self) -> tuple[NormalizedAstClaim, ...]:
        if self.product_intent_claim is None:
            return (self.implementation_claim,)
        return (self.implementation_claim, self.product_intent_claim)


def normalize_validated_ast_proposal(
    proposal: ValidatedAstProposalInput,
) -> NormalizedAstProposal:
    ast_ids = tuple(_ast_citation_id(value) for value in proposal.ast_citations)
    evidence_ids = tuple(_source_citation_id(value.citation) for value in proposal.evidence_citations)
    origin = AstClaimOrigin(
        proposal_fingerprint=proposal.proposal_fingerprint,
        schema_version=proposal.schema_version,
        provider_key=proposal.provider_key,
        model_id=proposal.model_id,
        provider_schema_version=proposal.provider_schema_version,
        prompt_schema_version=proposal.prompt_schema_version,
        validator_key=proposal.validator_key,
        validator_version=proposal.validator_version,
        observed_behavior=proposal.observed_behavior,
        product_intent_status=proposal.product_intent_status,
        inferred_product_intent=proposal.inferred_product_intent,
    )
    implementation = _normalized_claim(
        proposal,
        claim_text=proposal.canonical_rule_text,
        claim_role=SourceClaimRole.IMPLEMENTATION.value,
        behavior_identity=proposal.observed_behavior,
        ast_ids=ast_ids,
        evidence_ids=evidence_ids,
        origin=origin,
        evidence_roles=None,
    )
    product_intent = None
    if proposal.product_intent_status == "observed" and proposal.inferred_product_intent is not None:
        product_intent = _normalized_claim(
            proposal,
            claim_text=proposal.inferred_product_intent,
            claim_role=SourceClaimRole.PRODUCT_INTENT.value,
            behavior_identity=proposal.inferred_product_intent,
            ast_ids=(),
            evidence_ids=tuple(
                _source_citation_id(item.citation)
                for item in proposal.evidence_citations
                if item.role == "product_intent"
            ),
            origin=origin,
            evidence_roles=frozenset({"product_intent"}),
        )
    return NormalizedAstProposal(implementation, product_intent)


def deduplicate_normalized_ast_claims(
    claims: list[NormalizedAstClaim],
) -> list[NormalizedAstClaim]:
    grouped: dict[str, list[NormalizedAstClaim]] = {}
    order: list[str] = []
    for claim in claims:
        if claim.deduplication_key not in grouped:
            grouped[claim.deduplication_key] = []
            order.append(claim.deduplication_key)
        grouped[claim.deduplication_key].append(claim)
    return [_merge_claim_group(grouped[key]) for key in order]


def _normalized_claim(
    proposal: ValidatedAstProposalInput,
    *,
    claim_text: str,
    claim_role: str,
    behavior_identity: str,
    ast_ids: tuple[str, ...],
    evidence_ids: tuple[str, ...],
    origin: AstClaimOrigin,
    evidence_roles: frozenset[str] | None,
) -> NormalizedAstClaim:
    primary = proposal.ast_citations[0]
    evidence_payloads = [
        {
            "citation_id": _source_citation_id(item.citation),
            "role": item.role,
            "supports_fields": list(item.supports_fields),
            "citation": item.citation.to_dict(),
        }
        for item in proposal.evidence_citations
        if evidence_roles is None or item.role in evidence_roles
    ]
    attributes = {
        "origin": origin.to_dict(),
        "ast_citation_ids": list(ast_ids),
        "evidence_citation_ids": list(evidence_ids),
        "observed_behavior": proposal.observed_behavior,
        "product_intent_status": proposal.product_intent_status,
        "inferred_product_intent": proposal.inferred_product_intent,
        "confidence_explanation": proposal.confidence_explanation,
        "uncertainty": list(proposal.uncertainty),
        "never_auto_approve": True,
    }
    draft = ClaimDraft(
        claim_text=claim_text,
        provider_key=AST_PROPOSAL_PROVIDER_KEY,
        provider_version=proposal.prompt_schema_version,
        claim_role=claim_role,
        confidence=proposal.confidence,
        actor=proposal.actor,
        condition_text=proposal.condition,
        action_text=proposal.action,
        result_text=proposal.result,
        exception_text=proposal.exception,
        source_path=primary.source_path,
        start_line=primary.source_range.start_point.row + 1,
        end_line=primary.source_range.end_point.row + 1,
        evidence=evidence_payloads,
        attributes=attributes,
    )
    return NormalizedAstClaim(
        draft=draft,
        deduplication_key=_deduplication_key(
            claim_text,
            claim_role,
            behavior_identity,
        ),
        ast_citation_ids=ast_ids,
        evidence_citation_ids=evidence_ids,
        origins=(origin,),
    )


def _deduplication_key(
    claim_text: str,
    claim_role: str,
    behavior_identity: str,
) -> str:
    payload = "\n".join(
        (
            claim_role,
            normalize_rule_text(claim_text),
            normalize_rule_text(behavior_identity),
        )
    )
    return f"ast-claim:{hashlib.sha256(payload.encode()).hexdigest()}"


def _ast_citation_id(citation: AstNodeCitation) -> str:
    return _stable_id("ast", citation.to_dict())


def _source_citation_id(citation: ExactSourceCitation) -> str:
    return _stable_id("source", citation.to_dict())


def _stable_id(prefix: str, value: dict[str, object]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"


def _merge_claim_group(group: list[NormalizedAstClaim]) -> NormalizedAstClaim:
    first = group[0]
    ast_ids = tuple(dict.fromkeys(value for item in group for value in item.ast_citation_ids))
    evidence_ids = tuple(dict.fromkeys(value for item in group for value in item.evidence_citation_ids))
    origins = tuple(dict.fromkeys(origin for item in group for origin in item.origins))
    evidence_by_id: dict[str, dict[str, object]] = {}
    for item in group:
        for evidence in item.draft.evidence:
            citation_id = str(evidence["citation_id"])
            evidence_by_id.setdefault(citation_id, evidence)
    attributes = dict(first.draft.attributes)
    attributes["ast_citation_ids"] = list(ast_ids)
    attributes["evidence_citation_ids"] = list(evidence_ids)
    attributes["origins"] = [origin.to_dict() for origin in origins]
    draft = replace(
        first.draft,
        confidence=max(item.draft.confidence for item in group),
        evidence=list(evidence_by_id.values()),
        attributes=attributes,
    )
    return NormalizedAstClaim(
        draft=draft,
        deduplication_key=first.deduplication_key,
        ast_citation_ids=ast_ids,
        evidence_citation_ids=evidence_ids,
        origins=origins,
    )


__all__ = [
    "AST_PROPOSAL_PROVIDER_KEY",
    "AstClaimOrigin",
    "AstProposalEvidenceInput",
    "NormalizedAstClaim",
    "NormalizedAstProposal",
    "ValidatedAstProposalInput",
    "deduplicate_normalized_ast_claims",
    "normalize_validated_ast_proposal",
]
