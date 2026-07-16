"""Gap analysis v2 from canonical rules and linked evidence roles."""

from __future__ import annotations

from dataclasses import dataclass

from ruleatlas_contracts.enums import (
    EvidenceSourceType,
    GapType,
    ImplementationGapPriority,
    ImplementationGapStatus,
    SourceClaimRole,
)
from ruleatlas_persistence.models import (
    ImplementationGap,
    Rule,
)
from ruleatlas_persistence.repositories import RepositoryFactory
from sqlalchemy.orm import Session

IMPL_SOURCES = {
    EvidenceSourceType.BACKEND_CODE,
    EvidenceSourceType.FRONTEND_CODE,
    EvidenceSourceType.API_CONTRACT,
}
TEST_SOURCES = {
    EvidenceSourceType.UNIT_TEST,
    EvidenceSourceType.INTEGRATION_TEST,
    EvidenceSourceType.BDD_SPEC,
    EvidenceSourceType.API_TEST,
}
INTENT_SOURCES = {
    EvidenceSourceType.README_DOC,
    EvidenceSourceType.DESIGN_DOC,
    EvidenceSourceType.TICKET,
    EvidenceSourceType.BDD_SPEC,
}


@dataclass
class DetectedGap:
    gap_type: str
    title: str
    expected: str
    observed: str
    severity: str
    rule_id: str | None
    explanation: str


def _evidence_types(session: Session, rule_id: str) -> set[EvidenceSourceType]:
    rows = RepositoryFactory(session).rule_evidence().list_for_rule(rule_id)
    return {r.source_type for r in rows}


def _claim_roles(session: Session, project_id: str, analysis_version_id: str | None) -> set[str]:
    if not analysis_version_id:
        return set()
    rows = RepositoryFactory(session).source_claims_structured().list_roles_for_analysis(
        project_id, analysis_version_id
    )
    return set(rows)


def analyze_rule_gaps(
    session: Session,
    rule: Rule,
    *,
    has_coverage: bool,
    has_runtime: bool,
    claim_roles: set[str],
) -> list[DetectedGap]:
    types = _evidence_types(session, rule.id)
    gaps: list[DetectedGap] = []
    name = rule.name

    has_impl = bool(types & IMPL_SOURCES) or SourceClaimRole.IMPLEMENTATION.value in claim_roles
    has_test = bool(types & TEST_SOURCES) or SourceClaimRole.VERIFICATION.value in claim_roles
    has_intent = bool(types & INTENT_SOURCES) or SourceClaimRole.PRODUCT_INTENT.value in claim_roles

    if has_intent and not has_impl:
        gaps.append(
            DetectedGap(
                gap_type=GapType.MISSING_IMPLEMENTATION.value,
                title=f"Missing implementation: {name}",
                expected="Canonical rule should have linked implementation evidence",
                observed="Intent/product evidence present without implementation citations",
                severity="high",
                rule_id=rule.id,
                explanation="Gap based on canonical rule relationships — intent without code link",
            )
        )
    if has_impl and not has_test:
        gaps.append(
            DetectedGap(
                gap_type=GapType.MISSING_TEST.value,
                title=f"Missing test: {name}",
                expected="Implementation-backed rule should have verification evidence",
                observed="No test/BDD verification linked",
                severity="medium",
                rule_id=rule.id,
                explanation="Missing verification evidence for an implemented rule",
            )
        )
    if has_impl and not has_intent:
        gaps.append(
            DetectedGap(
                gap_type=GapType.MISSING_INTENT.value,
                title=f"Missing intent: {name}",
                expected="Product-intent or BDD/doc evidence preferred",
                observed="Implementation without intent citations",
                severity="low",
                rule_id=rule.id,
                explanation="Implementation exists without product-intent corroboration",
            )
        )
    if has_impl and not has_coverage:
        gaps.append(
            DetectedGap(
                gap_type=GapType.MISSING_COVERAGE.value,
                title=f"Missing coverage: {name}",
                expected="Coverage report may corroborate execution of linked code",
                observed="No coverage linked — absence is not proof of non-implementation",
                severity="low",
                rule_id=rule.id,
                explanation=(
                    "Coverage absence is corroboration gap only; not treated as proof the rule is unimplemented"
                ),
            )
        )
    if has_impl and not has_runtime:
        gaps.append(
            DetectedGap(
                gap_type=GapType.UNOBSERVED_RUNTIME.value,
                title=f"Unobserved runtime: {name}",
                expected="Optional runtime observation",
                observed="No runtime evidence — not proof of non-implementation",
                severity="low",
                rule_id=rule.id,
                explanation="Runtime unobserved; does not prove the behavior is absent in code",
            )
        )
    return gaps


def generate_gaps_v2(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str | None = None,
    persist: bool = True,
) -> list[DetectedGap]:
    """Semantic gap analysis over structured claims/rules.

    NOT WIRED (RA-04-001): no route or production pipeline calls this; ``persist=True`` is exercised
    only by tests and performs NO dedup / clear-existing. Add an idempotency guard (clear-existing,
    or upsert by semantic key) before wiring to any route, or repeated runs will duplicate rows.
    """
    repos = RepositoryFactory(session)
    rules = repos.rules().list_for_project(project_id, analysis_version_id=analysis_version_id)
    has_coverage = repos.coverage_reports().count_for_project(project_id) > 0
    # Runtime evidence optional — treat as absent unless rows exist
    has_runtime = False
    try:
        has_runtime = repos.runtime_log_evidence().count_for_project(project_id) > 0
    except (LookupError, ValueError, TypeError, AttributeError):
        has_runtime = False

    claim_roles = _claim_roles(session, project_id, analysis_version_id)
    all_gaps: list[DetectedGap] = []
    for rule in rules:
        all_gaps.extend(
            analyze_rule_gaps(
                session,
                rule,
                has_coverage=has_coverage,
                has_runtime=has_runtime,
                claim_roles=claim_roles,
            )
        )

    if persist:
        priority_map = {
            "high": ImplementationGapPriority.HIGH,
            "medium": ImplementationGapPriority.MEDIUM,
            "low": ImplementationGapPriority.LOW,
        }
        for g in all_gaps:
            session.add(
                ImplementationGap(
                    project_id=project_id,
                    analysis_version_id=analysis_version_id,
                    rule_id=g.rule_id,
                    title=g.title[:255],
                    current_observed_behavior=g.observed,
                    expected_product_behavior=g.expected,
                    tests_needed=g.explanation if g.gap_type == GapType.MISSING_TEST.value else None,
                    risk=g.severity,
                    priority=priority_map.get(g.severity, ImplementationGapPriority.MEDIUM),
                    status=ImplementationGapStatus.OPEN,
                    gap_type=g.gap_type,
                    attributes_json={"explanation": g.explanation},
                )
            )
        session.commit()
    return all_gaps
