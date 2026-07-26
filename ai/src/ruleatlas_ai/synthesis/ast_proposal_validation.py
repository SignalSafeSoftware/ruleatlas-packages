"""Pure validation for AST-backed candidate rule proposals.

This module validates internal citation coherence only. Database existence, retained-version checks,
tenant ownership, and authorization remain application-layer responsibilities.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

from ruleatlas_contracts.ast import AstCitationScope, AstNodeCitation, ExactSourceCitation

from ruleatlas_ai.synthesis.ast_proposal import (
    AstRuleField,
    AstRuleProposal,
    ProductIntentStatus,
    RuleEvidenceRole,
)


class AstProposalValidationCode(StrEnum):
    DUPLICATE_AST_CITATION = "duplicate_ast_citation"
    DUPLICATE_EVIDENCE_CITATION = "duplicate_evidence_citation"
    INVALID_RANGE = "invalid_range"
    SCOPE_MISMATCH = "scope_mismatch"
    DISALLOWED_EVIDENCE_ROLE = "disallowed_evidence_role"
    MISSING_IMPLEMENTATION_EVIDENCE = "missing_implementation_evidence"
    MISSING_PRODUCT_INTENT_EVIDENCE = "missing_product_intent_evidence"
    INVALID_ROLE_COVERAGE = "invalid_role_coverage"
    UNCITED_PROPOSAL_FIELD = "uncited_proposal_field"
    UNSUPPORTED_APPROVAL_ASSERTION = "unsupported_approval_assertion"


@dataclass(frozen=True)
class AstProposalValidationIssue:
    code: AstProposalValidationCode
    message: str
    field_name: str | None = None
    citation_index: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code.value,
            "message": self.message,
            "field_name": self.field_name,
            "citation_index": self.citation_index,
        }


@dataclass(frozen=True)
class AstProposalValidationResult:
    issues: tuple[AstProposalValidationIssue, ...] = field(default_factory=tuple)
    warnings: tuple[AstProposalValidationIssue, ...] = field(default_factory=tuple)

    @property
    def valid(self) -> bool:
        return not self.issues

    def to_dict(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "issues": [issue.to_dict() for issue in self.issues],
            "warnings": [warning.to_dict() for warning in self.warnings],
        }


_META_APPROVAL_PATTERNS = (
    re.compile(r"\b(?:this|the)\s+(?:candidate\s+)?rule\s+is\s+approved\b", re.I),
    re.compile(r"\bauto(?:matically)?[- ]approved\b", re.I),
    re.compile(r"\bapproved\s+by\s+(?:a\s+)?(?:human\s+)?reviewer\b", re.I),
    re.compile(r"\bhuman[- ]reviewed\s+(?:and\s+)?approved\b", re.I),
    re.compile(r"\bconfirmed\s+product\s+intent\b", re.I),
    re.compile(r"\bauthoritative\s+product\s+requirement\b", re.I),
)

_EXCEPTION_ROLE_FIELDS = frozenset({AstRuleField.CANONICAL_RULE_TEXT, AstRuleField.EXCEPTION})
_SUPPORTIVE_ROLES = frozenset(
    {
        RuleEvidenceRole.IMPLEMENTATION,
        RuleEvidenceRole.PRODUCT_INTENT,
        RuleEvidenceRole.VERIFICATION,
        RuleEvidenceRole.EXCEPTION,
    }
)


def validate_ast_rule_proposal(
    proposal: AstRuleProposal,
    *,
    expected_scope: AstCitationScope | None = None,
    allowed_evidence_roles: frozenset[RuleEvidenceRole] | None = None,
) -> AstProposalValidationResult:
    allowed_roles = allowed_evidence_roles or frozenset(RuleEvidenceRole)
    issues: list[AstProposalValidationIssue] = []
    warnings: list[AstProposalValidationIssue] = []

    canonical_scope = expected_scope or proposal.ast_citations[0].scope
    _validate_ast_citations(proposal, canonical_scope, issues)
    _validate_evidence_citations(
        proposal,
        canonical_scope,
        allowed_roles,
        issues,
    )
    _validate_role_requirements(proposal, issues)
    _validate_field_coverage(proposal, issues)
    _validate_unsupported_assertions(proposal, issues)
    return AstProposalValidationResult(tuple(issues), tuple(warnings))


def _validate_ast_citations(
    proposal: AstRuleProposal,
    expected_scope: AstCitationScope,
    issues: list[AstProposalValidationIssue],
) -> None:
    seen: set[tuple[object, ...]] = set()
    for index, citation in enumerate(proposal.ast_citations):
        identity = _ast_identity(citation)
        if identity in seen:
            issues.append(
                AstProposalValidationIssue(
                    AstProposalValidationCode.DUPLICATE_AST_CITATION,
                    "AST citations must not contain duplicates",
                    "ast_citations",
                    index,
                )
            )
        seen.add(identity)
        _validate_scope(citation.scope, expected_scope, "ast_citations", index, issues)
        _validate_range(
            citation.source_range.start_byte,
            citation.source_range.end_byte,
            "ast_citations",
            index,
            issues,
        )


def _validate_evidence_citations(
    proposal: AstRuleProposal,
    expected_scope: AstCitationScope,
    allowed_roles: frozenset[RuleEvidenceRole],
    issues: list[AstProposalValidationIssue],
) -> None:
    seen: set[tuple[object, ...]] = set()
    for index, evidence in enumerate(proposal.supporting_evidence_citations):
        citation = evidence.citation
        identity = _source_identity(citation)
        if identity in seen:
            issues.append(
                AstProposalValidationIssue(
                    AstProposalValidationCode.DUPLICATE_EVIDENCE_CITATION,
                    "supporting evidence citations must not contain duplicates",
                    "supporting_evidence_citations",
                    index,
                )
            )
        seen.add(identity)
        _validate_scope(
            citation.scope,
            expected_scope,
            "supporting_evidence_citations",
            index,
            issues,
        )
        _validate_range(
            citation.source_range.start_byte,
            citation.source_range.end_byte,
            "supporting_evidence_citations",
            index,
            issues,
        )
        if evidence.role not in allowed_roles:
            issues.append(
                AstProposalValidationIssue(
                    AstProposalValidationCode.DISALLOWED_EVIDENCE_ROLE,
                    f"evidence role is not allowed: {evidence.role.value}",
                    "supporting_evidence_citations",
                    index,
                )
            )
        if evidence.role == RuleEvidenceRole.EXCEPTION and not set(evidence.supports_fields) <= _EXCEPTION_ROLE_FIELDS:
            issues.append(
                AstProposalValidationIssue(
                    AstProposalValidationCode.INVALID_ROLE_COVERAGE,
                    "exception evidence may only support canonical text and exception fields",
                    "supporting_evidence_citations",
                    index,
                )
            )


def _validate_role_requirements(
    proposal: AstRuleProposal,
    issues: list[AstProposalValidationIssue],
) -> None:
    roles = {item.role for item in proposal.supporting_evidence_citations}
    if RuleEvidenceRole.IMPLEMENTATION not in roles:
        issues.append(
            AstProposalValidationIssue(
                AstProposalValidationCode.MISSING_IMPLEMENTATION_EVIDENCE,
                "at least one implementation-role citation is required",
                "supporting_evidence_citations",
            )
        )
    if proposal.product_intent_status == ProductIntentStatus.OBSERVED and RuleEvidenceRole.PRODUCT_INTENT not in roles:
        issues.append(
            AstProposalValidationIssue(
                AstProposalValidationCode.MISSING_PRODUCT_INTENT_EVIDENCE,
                "observed product intent requires product-intent evidence",
                "supporting_evidence_citations",
            )
        )


def _validate_field_coverage(
    proposal: AstRuleProposal,
    issues: list[AstProposalValidationIssue],
) -> None:
    required = {
        AstRuleField.CANONICAL_RULE_TEXT,
        AstRuleField.OBSERVED_BEHAVIOR,
        AstRuleField.ACTOR,
        AstRuleField.CONDITION,
        AstRuleField.ACTION,
        AstRuleField.RESULT,
    }
    if proposal.inferred_product_intent is not None:
        required.add(AstRuleField.INFERRED_PRODUCT_INTENT)
    if proposal.exception is not None:
        required.add(AstRuleField.EXCEPTION)
    covered = {
        covered_field
        for evidence in proposal.supporting_evidence_citations
        if evidence.role in _SUPPORTIVE_ROLES
        for covered_field in evidence.supports_fields
    }
    for missing in sorted(required - covered, key=lambda value: value.value):
        issues.append(
            AstProposalValidationIssue(
                AstProposalValidationCode.UNCITED_PROPOSAL_FIELD,
                f"proposal field lacks a supporting citation: {missing.value}",
                missing.value,
            )
        )


def _validate_unsupported_assertions(
    proposal: AstRuleProposal,
    issues: list[AstProposalValidationIssue],
) -> None:
    text_fields = {
        "canonical_rule_text": proposal.canonical_rule_text,
        "observed_behavior": proposal.observed_behavior,
        "inferred_product_intent": proposal.inferred_product_intent,
        "confidence_explanation": proposal.confidence_explanation,
    }
    for field_name, value in text_fields.items():
        if value is not None and any(pattern.search(value) for pattern in _META_APPROVAL_PATTERNS):
            issues.append(
                AstProposalValidationIssue(
                    AstProposalValidationCode.UNSUPPORTED_APPROVAL_ASSERTION,
                    "AI proposals cannot assert review, approval, or authoritative product intent",
                    field_name,
                )
            )


def _validate_scope(
    actual: AstCitationScope,
    expected: AstCitationScope,
    field_name: str,
    citation_index: int,
    issues: list[AstProposalValidationIssue],
) -> None:
    if actual != expected:
        issues.append(
            AstProposalValidationIssue(
                AstProposalValidationCode.SCOPE_MISMATCH,
                "citation scope does not match the proposal scope",
                field_name,
                citation_index,
            )
        )


def _validate_range(
    start_byte: int,
    end_byte: int,
    field_name: str,
    citation_index: int,
    issues: list[AstProposalValidationIssue],
) -> None:
    if start_byte < 0 or end_byte < start_byte:
        issues.append(
            AstProposalValidationIssue(
                AstProposalValidationCode.INVALID_RANGE,
                "citation byte range is invalid",
                field_name,
                citation_index,
            )
        )


def _ast_identity(citation: AstNodeCitation) -> tuple[object, ...]:
    return (
        citation.scope.project_id,
        citation.scope.analysis_version_id,
        citation.document_key,
        citation.node_key,
        citation.content_hash,
        citation.subtree_hash,
        citation.source_range.start_byte,
        citation.source_range.end_byte,
    )


def _source_identity(citation: ExactSourceCitation) -> tuple[object, ...]:
    return (
        citation.scope.project_id,
        citation.scope.analysis_version_id,
        citation.source_file_id,
        citation.content_hash,
        citation.source_range.start_byte,
        citation.source_range.end_byte,
        citation.excerpt_hash,
    )


__all__ = [
    "AstProposalValidationCode",
    "AstProposalValidationIssue",
    "AstProposalValidationResult",
    "validate_ast_rule_proposal",
]
