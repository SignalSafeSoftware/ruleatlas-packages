"""Deterministic rule-relationship suggestion heuristics (claims/rules context, ORM-free).

Pure suggestion algorithms operating on lightweight DTOs (``RuleView`` / ``EvidenceView``) rather than ORM
models, so this logic belongs to the rules package. The ``RelationshipSuggestionServiceRepository`` adapter
maps ORM rows to these DTOs, adds the session-bound SAME_AS (duplicate-cluster) heuristic, and persists.
"""

from __future__ import annotations

from dataclasses import dataclass

from ruleatlas_contracts.enums import (
    EvidenceSourceType,
    RuleCategory,
    RuleRelationshipType,
)

from ruleatlas_claims.text_normalize import normalize_rule_text

MIN_CONFIDENCE = 55.0

SUGGESTION_TYPES = frozenset(
    {
        RuleRelationshipType.SAME_AS,
        RuleRelationshipType.PARENT_OF,
        RuleRelationshipType.DEPENDS_ON,
        RuleRelationshipType.CONSTRAINS,
        RuleRelationshipType.IMPLEMENTED_BY,
        RuleRelationshipType.TESTED_BY,
        RuleRelationshipType.DOCUMENTED_BY,
    }
)

PARENT_LIKE_PHRASES = (
    "handles",
    "manages",
    "workflow",
    "process",
    "during signup",
    "signup flow",
    "registration",
    "onboarding",
)

CHILD_LIKE_PHRASES = (
    "if email",
    "send email",
    "generate password",
    "reject duplicate",
    "expire token",
    "when user",
    "must not allow",
)

ORDERING_PHRASES = ("before", "after", "then", "first", "next step", "followed by")

TEST_EVIDENCE_TYPES = frozenset(
    {
        EvidenceSourceType.UNIT_TEST,
        EvidenceSourceType.INTEGRATION_TEST,
        EvidenceSourceType.API_TEST,
        EvidenceSourceType.BDD_SPEC,
        EvidenceSourceType.E2E_TEST,
    }
)

DOC_EVIDENCE_TYPES = frozenset(
    {
        EvidenceSourceType.README_DOC,
        EvidenceSourceType.DESIGN_DOC,
    }
)

__all__ = [
    "CHILD_LIKE_PHRASES",
    "DOC_EVIDENCE_TYPES",
    "MIN_CONFIDENCE",
    "ORDERING_PHRASES",
    "PARENT_LIKE_PHRASES",
    "SUGGESTION_TYPES",
    "TEST_EVIDENCE_TYPES",
    "EvidenceView",
    "RuleView",
    "SuggestionCandidate",
    "filter_best_candidates",
    "suggest_deterministic_relationships",
]


@dataclass(frozen=True)
class RuleView:
    """ORM-free view of a rule for suggestion heuristics."""

    id: str
    rule_category: RuleCategory
    text: str


@dataclass(frozen=True)
class EvidenceView:
    """ORM-free view of a piece of rule evidence."""

    source_type: EvidenceSourceType
    reference_path: str | None


@dataclass(frozen=True)
class SuggestionCandidate:
    source_rule_id: str
    target_rule_id: str
    suggested_relationship_type: RuleRelationshipType
    confidence: float
    reason: str
    signals: dict


def _shared_terms(left: str, right: str) -> list[str]:
    left_tokens = set(normalize_rule_text(left).split())
    right_tokens = set(normalize_rule_text(right).split())
    return sorted(left_tokens & right_tokens)[:8]


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in phrases)


def _suggest_parent_child(rules: list[RuleView]) -> list[SuggestionCandidate]:
    candidates: list[SuggestionCandidate] = []
    for parent in rules:
        parent_text = parent.text
        if not _contains_any(parent_text, PARENT_LIKE_PHRASES):
            continue
        for child in rules:
            if parent.id == child.id:
                continue
            child_text = child.text
            if not _contains_any(child_text, CHILD_LIKE_PHRASES):
                continue
            shared = _shared_terms(parent_text, child_text)
            if not shared:
                continue
            candidates.append(
                SuggestionCandidate(
                    source_rule_id=parent.id,
                    target_rule_id=child.id,
                    suggested_relationship_type=RuleRelationshipType.PARENT_OF,
                    confidence=62.0 + min(20.0, len(shared) * 4.0),
                    reason="Parent-like workflow claim paired with child-like step claim in the same workflow.",
                    signals={
                        "signal": "parent_child_wording",
                        "shared_terms": shared,
                    },
                )
            )
    return candidates


def _suggest_depends_on(rules: list[RuleView]) -> list[SuggestionCandidate]:
    candidates: list[SuggestionCandidate] = []
    for left in rules:
        left_text = left.text.lower()
        if not any(phrase in left_text for phrase in ORDERING_PHRASES):
            continue
        for right in rules:
            if left.id == right.id:
                continue
            shared = _shared_terms(left.text, right.text)
            if len(shared) < 2:
                continue
            candidates.append(
                SuggestionCandidate(
                    source_rule_id=left.id,
                    target_rule_id=right.id,
                    suggested_relationship_type=RuleRelationshipType.DEPENDS_ON,
                    confidence=58.0 + min(15.0, len(shared) * 3.0),
                    reason="Ordering language in one claim with shared workflow terms suggests dependency.",
                    signals={"signal": "ordering_language", "shared_terms": shared},
                )
            )
    return candidates


def _suggest_constrains(rules: list[RuleView]) -> list[SuggestionCandidate]:
    candidates: list[SuggestionCandidate] = []
    business = [rule for rule in rules if rule.rule_category == RuleCategory.BUSINESS]
    validators = [
        rule for rule in rules if rule.rule_category in {RuleCategory.VALIDATION, RuleCategory.SECURITY_AUTHORIZATION}
    ]
    for business_rule in business:
        business_text = business_rule.text
        for validator in validators:
            shared = _shared_terms(business_text, validator.text)
            if len(shared) < 2:
                continue
            candidates.append(
                SuggestionCandidate(
                    source_rule_id=validator.id,
                    target_rule_id=business_rule.id,
                    suggested_relationship_type=RuleRelationshipType.CONSTRAINS,
                    confidence=60.0 + min(18.0, len(shared) * 3.0),
                    reason="Validation or authorization rule shares terms with a business rule in the same workflow.",
                    signals={
                        "signal": "category_constrains",
                        "validator_category": validator.rule_category.value,
                        "shared_terms": shared,
                    },
                )
            )
    return candidates


def _suggest_doc_code_links(
    doc_rule: RuleView,
    code_rules: list[RuleView],
    evidence_map: dict[str, list[EvidenceView]],
) -> list[SuggestionCandidate]:
    doc_evidences = [
        evidence for evidence in evidence_map.get(doc_rule.id, []) if evidence.source_type in DOC_EVIDENCE_TYPES
    ]
    if not doc_evidences:
        return []
    doc_text = doc_rule.text
    candidates: list[SuggestionCandidate] = []
    for code_rule in code_rules:
        if doc_rule.id == code_rule.id:
            continue
        backend = [
            evidence
            for evidence in evidence_map.get(code_rule.id, [])
            if evidence.source_type == EvidenceSourceType.BACKEND_CODE
        ]
        if not backend:
            continue
        shared = _shared_terms(doc_text, code_rule.text)
        if len(shared) < 2:
            continue
        candidates.append(
            SuggestionCandidate(
                source_rule_id=doc_rule.id,
                target_rule_id=code_rule.id,
                suggested_relationship_type=RuleRelationshipType.DOCUMENTED_BY,
                confidence=57.0 + min(20.0, len(shared) * 3.0),
                reason="Documentation evidence and backend code share claim terms in this workflow.",
                signals={
                    "signal": "doc_code_terms",
                    "shared_terms": shared,
                    "doc_path": doc_evidences[0].reference_path,
                    "code_path": backend[0].reference_path,
                },
            )
        )
        candidates.append(
            SuggestionCandidate(
                source_rule_id=code_rule.id,
                target_rule_id=doc_rule.id,
                suggested_relationship_type=RuleRelationshipType.IMPLEMENTED_BY,
                confidence=55.0 + min(18.0, len(shared) * 3.0),
                reason="Backend implementation claim aligns with documentation in the same workflow.",
                signals={
                    "signal": "code_doc_terms",
                    "shared_terms": shared,
                    "doc_path": doc_evidences[0].reference_path,
                    "code_path": backend[0].reference_path,
                },
            )
        )
    return candidates


def _paths_share_basename(left: str, right: str) -> bool:
    return left == right or left.split("/")[-1] == right.split("/")[-1]


def _test_same_file_candidate(
    test_rule: RuleView,
    code_rule: RuleView,
    test_path: str,
    backend_path: str,
) -> SuggestionCandidate:
    return SuggestionCandidate(
        source_rule_id=test_rule.id,
        target_rule_id=code_rule.id,
        suggested_relationship_type=RuleRelationshipType.TESTED_BY,
        confidence=65.0,
        reason="Test/BDD evidence references the same source file as a backend rule.",
        signals={
            "signal": "test_same_file",
            "test_path": test_path,
            "code_path": backend_path,
        },
    )


def _matching_backend_path(test_path: str, backend_paths: set[str]) -> str | None:
    for backend_path in backend_paths:
        if _paths_share_basename(test_path, backend_path):
            return backend_path
    return None


def _suggest_test_same_file_links(
    code_rule: RuleView,
    rules: list[RuleView],
    evidence_map: dict[str, list[EvidenceView]],
) -> list[SuggestionCandidate]:
    code_evidences = evidence_map.get(code_rule.id, [])
    backend_paths = {
        evidence.reference_path
        for evidence in code_evidences
        if evidence.source_type == EvidenceSourceType.BACKEND_CODE and evidence.reference_path
    }
    if not backend_paths:
        return []
    candidates: list[SuggestionCandidate] = []
    for test_rule in rules:
        if test_rule.id == code_rule.id:
            continue
        test_evidences = [
            evidence for evidence in evidence_map.get(test_rule.id, []) if evidence.source_type in TEST_EVIDENCE_TYPES
        ]
        for test_evidence in test_evidences:
            test_path = test_evidence.reference_path or ""
            if not test_path:
                continue
            backend_path = _matching_backend_path(test_path, backend_paths)
            if backend_path is None:
                continue
            candidates.append(_test_same_file_candidate(test_rule, code_rule, test_path, backend_path))
    return candidates


def _suggest_evidence_links(
    rules: list[RuleView],
    evidence_map: dict[str, list[EvidenceView]],
) -> list[SuggestionCandidate]:
    candidates: list[SuggestionCandidate] = []
    code_rules = [
        rule
        for rule in rules
        if any(evidence.source_type == EvidenceSourceType.BACKEND_CODE for evidence in evidence_map.get(rule.id, []))
    ]
    doc_rules = [
        rule for rule in rules if rule.rule_category in {RuleCategory.BUSINESS, RuleCategory.WORKFLOW_LIFECYCLE}
    ]
    for doc_rule in doc_rules:
        candidates.extend(_suggest_doc_code_links(doc_rule, code_rules, evidence_map))
    for code_rule in code_rules:
        candidates.extend(_suggest_test_same_file_links(code_rule, rules, evidence_map))
    return candidates


def suggest_deterministic_relationships(
    rules: list[RuleView], evidence_map: dict[str, list[EvidenceView]]
) -> list[SuggestionCandidate]:
    """Run all non-session heuristics: parent/child, depends-on, constrains, and evidence links."""
    candidates: list[SuggestionCandidate] = []
    candidates.extend(_suggest_parent_child(rules))
    candidates.extend(_suggest_depends_on(rules))
    candidates.extend(_suggest_constrains(rules))
    candidates.extend(_suggest_evidence_links(rules, evidence_map))
    return candidates


def filter_best_candidates(
    raw_candidates: list[SuggestionCandidate],
    *,
    existing: set[tuple[str, str, str]],
    rejected: set[tuple[str, str, str]],
) -> dict[tuple[str, str, str], SuggestionCandidate]:
    """Keep the highest-confidence candidate per (source, target, type), dropping existing/rejected/low ones."""
    best_by_pair: dict[tuple[str, str, str], SuggestionCandidate] = {}
    for candidate in raw_candidates:
        if candidate.suggested_relationship_type not in SUGGESTION_TYPES:
            continue
        if candidate.confidence < MIN_CONFIDENCE:
            continue
        rel_value = candidate.suggested_relationship_type.value
        edge_key = (candidate.source_rule_id, candidate.target_rule_id, rel_value)
        if edge_key in existing or edge_key in rejected:
            continue
        current = best_by_pair.get(edge_key)
        if current is None or candidate.confidence > current.confidence:
            best_by_pair[edge_key] = candidate
    return best_by_pair
