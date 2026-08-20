"""Pure BDD extraction: turn a parsed BDD scenario into a candidate ClaimDraft.

Persistence + BDD-vs-implementation conflict detection live in
``ruleatlas.application.pipeline.bdd_claim_generation`` (app tier) so this extraction module stays free
of claims/persistence dependencies (breakup Phase 2).
"""

from __future__ import annotations

from ruleatlas_contracts.claims import ClaimDraft
from ruleatlas_contracts.enums import BddEvidenceRole, BddStepLinkStatus, SourceClaimRole
from ruleatlas_persistence.models import BddFeature, BddScenario, BddStep, BddStepLink


def resolve_bdd_claim_role(policy: str) -> str:
    if policy == BddEvidenceRole.VERIFICATION.value:
        return SourceClaimRole.VERIFICATION.value
    return SourceClaimRole.PRODUCT_INTENT.value


def _keyword_bucket(step: BddStep) -> str | None:
    keyword_type = (step.keyword_type or "").lower()
    keyword = step.keyword.lower()
    if keyword_type == "context" or keyword.startswith("given"):
        return "given"
    if keyword_type == "action" or keyword.startswith("when"):
        return "when"
    if keyword_type == "outcome" or keyword.startswith("then"):
        return "then"
    return None


def _inherit_and_but(steps: list[BddStep], givens: list[str], whens: list[str], thens: list[str]) -> None:
    for step in steps:
        keyword = step.keyword.lower()
        if keyword.startswith("given"):
            givens.append(step.text)
        elif keyword.startswith("when"):
            whens.append(step.text)
        elif keyword.startswith("then"):
            thens.append(step.text)
        elif keyword.startswith(("and", "but")):
            (thens or whens or givens).append(step.text)


def _partition_step_texts(steps: list[BddStep]) -> tuple[list[str], list[str], list[str]]:
    givens: list[str] = []
    whens: list[str] = []
    thens: list[str] = []
    buckets = {"given": givens, "when": whens, "then": thens}
    for step in steps:
        bucket = _keyword_bucket(step)
        if bucket is not None:
            buckets[bucket].append(step.text)
    if not givens and not whens and not thens:
        _inherit_and_but(steps, givens, whens, thens)
    return givens, whens, thens


def _linked_definitions(steps: list[BddStep], links: dict[str, BddStepLink]) -> list[dict[str, str | None]]:
    linked_defs: list[dict[str, str | None]] = []
    for step in steps:
        link = links.get(step.id)
        if link and link.status == BddStepLinkStatus.LINKED.value:
            linked_defs.append(
                {
                    "step": step.text,
                    "definition_path": link.definition_path,
                    "definition_name": link.definition_name,
                }
            )
    return linked_defs


def claims_from_scenario(
    *,
    feature: BddFeature,
    scenario: BddScenario,
    steps: list[BddStep],
    links: dict[str, BddStepLink],
    claim_role: str,
) -> ClaimDraft:
    givens, whens, thens = _partition_step_texts(steps)
    linked_defs = _linked_definitions(steps, links)
    claim_text = f"BDD scenario '{scenario.name}'"
    if thens:
        claim_text = f"{claim_text}: {thens[0]}"
    return ClaimDraft(
        claim_text=claim_text,
        provider_key="bdd_gherkin",
        provider_version="1.0.0",
        claim_role=claim_role,
        confidence=0.6 if linked_defs else 0.45,
        condition_text="; ".join(givens) or None,
        action_text="; ".join(whens) or None,
        result_text="; ".join(thens) or None,
        subject_text=feature.name,
        source_path=feature.source_path,
        start_line=scenario.start_line,
        evidence=[
            {
                "evidence_kind": "bdd_scenario",
                "reference_path": feature.source_path,
                "start_line": scenario.start_line,
                "excerpt": scenario.name,
                "attributes": {
                    "scenario_id": scenario.id,
                    "feature_id": feature.id,
                    "linked_definitions": linked_defs,
                    "never_auto_canonical": True,
                },
            }
        ]
        + [
            {
                "evidence_kind": "bdd_step",
                "reference_path": feature.source_path,
                "start_line": step.start_line,
                "excerpt": f"{step.keyword} {step.text}",
                "attributes": {"step_id": step.id, "link_status": step.link_status},
            }
            for step in steps
        ],
        attributes={
            "bdd_scenario_id": scenario.id,
            "bdd_feature_id": feature.id,
            "is_outline": scenario.is_outline,
            "tags": scenario.tags_json,
            "never_auto_canonical": True,
        },
    )
