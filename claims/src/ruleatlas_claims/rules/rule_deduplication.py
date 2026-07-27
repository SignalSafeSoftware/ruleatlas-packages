from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from ruleatlas_contracts.enums import RuleLineageRelation, RuleStatus
from ruleatlas_persistence.models import Rule, RuleLineage, RuleVersion
from ruleatlas_persistence.repositories import RepositoryFactory
from sqlalchemy.orm import Session

from ruleatlas_claims.text_normalize import normalize_rule_text as normalize_rule_text


def similarity_score(left: str, right: str) -> float:
    return _normalized_similarity(normalize_rule_text(left), normalize_rule_text(right))


def _normalized_similarity(left_norm: str, right_norm: str) -> float:
    if not left_norm or not right_norm:
        return 0.0
    if left_norm == right_norm:
        return 1.0
    left_tokens = set(left_norm.split())
    right_tokens = set(right_norm.split())
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    return overlap / union if union else 0.0


@dataclass(frozen=True)
class DuplicateGroup:
    primary_rule_id: str
    rule_ids: list[str]
    similarity: float
    label: str


def _rule_text(rule: Rule, versions_by_id: dict[str, RuleVersion]) -> str:
    if rule.current_version_id and (version := versions_by_id.get(rule.current_version_id)):
        return version.business_rule
    return rule.name


def _normalized_rule_texts(session: Session, rules: list[Rule]) -> dict[str, str]:
    version_ids = {rule.current_version_id for rule in rules if rule.current_version_id}
    versions_by_id = RepositoryFactory(session).rule_versions().map_by_ids(version_ids)
    return {
        rule.id: normalize_rule_text(_rule_text(rule, versions_by_id))
        for rule in rules
    }


def _duplicate_members_for_primary(
    rules: list[Rule],
    *,
    start_index: int,
    normalized_texts: dict[str, str],
    min_similarity: float,
    seen: set[str],
) -> tuple[list[str], float]:
    primary = rules[start_index]
    primary_text = normalized_texts[primary.id]
    members = [primary.id]
    max_similarity = 0.0
    for other in rules[start_index + 1 :]:
        if other.id in seen:
            continue
        score = _normalized_similarity(primary_text, normalized_texts[other.id])
        if score >= min_similarity:
            members.append(other.id)
            max_similarity = max(max_similarity, score)
    return members, max_similarity


def find_duplicate_groups(
    session: Session,
    project_id: str,
    *,
    min_similarity: float = 0.72,
) -> list[DuplicateGroup]:
    rules = RepositoryFactory(session).rules().list_for_dedup_candidates(project_id)
    normalized_texts = _normalized_rule_texts(session, rules)
    groups: list[DuplicateGroup] = []
    seen: set[str] = set()

    for index, primary in enumerate(rules):
        if primary.id in seen:
            continue
        members, max_similarity = _duplicate_members_for_primary(
            rules,
            start_index=index,
            normalized_texts=normalized_texts,
            min_similarity=min_similarity,
            seen=seen,
        )
        if len(members) > 1:
            seen.update(members)
            groups.append(
                DuplicateGroup(
                    primary_rule_id=primary.id,
                    rule_ids=members,
                    similarity=max_similarity,
                    label=primary.name,
                )
            )
    return groups


def find_duplicate_groups_for_rule(
    session: Session,
    project_id: str,
    rule_id: str,
    *,
    min_similarity: float = 0.72,
) -> list[DuplicateGroup]:
    """Return duplicate candidates for one rule without project-wide pairwise grouping."""
    rules = RepositoryFactory(session).rules().list_for_dedup_candidates(project_id)
    primary = next((rule for rule in rules if rule.id == rule_id), None)
    if primary is None:
        return []

    normalized_texts = _normalized_rule_texts(session, rules)
    primary_text = normalized_texts[primary.id]
    members = [primary.id]
    max_similarity = 0.0
    for other in rules:
        if other.id == primary.id:
            continue
        score = _normalized_similarity(primary_text, normalized_texts[other.id])
        if score >= min_similarity:
            members.append(other.id)
            max_similarity = max(max_similarity, score)

    if len(members) == 1:
        return []
    return [
        DuplicateGroup(
            primary_rule_id=primary.id,
            rule_ids=members,
            similarity=max_similarity,
            label=primary.name,
        )
    ]


def merge_rules(
    session: Session,
    project_id: str,
    primary_rule_id: str,
    duplicate_rule_ids: list[str],
) -> Rule:
    repos = RepositoryFactory(session)
    primary = repos.rules().get_for_project(primary_rule_id, project_id)
    if primary is None:
        raise LookupError(f"Primary rule not found: {primary_rule_id}")

    duplicate_ids = [rule_id for rule_id in duplicate_rule_ids if rule_id != primary_rule_id]
    for duplicate_id in duplicate_ids:
        duplicate = repos.rules().get_for_project(duplicate_id, project_id)
        if duplicate is None:
            raise LookupError(f"Duplicate rule not found: {duplicate_id}")

        evidence_rows = RepositoryFactory(session).rule_evidence().list_for_rule(duplicate_id)
        for evidence in evidence_rows:
            evidence.rule_id = primary.id
            session.add(evidence)

        duplicate.status = RuleStatus.DEPRECATED
        duplicate.deprecated_at = datetime.now(UTC)
        duplicate.review_note = f"Merged into rule {primary.id}"
        session.add(duplicate)
        # RA-04-002: record structured lineage for the merge (not just a review note).
        session.add(
            RuleLineage(
                project_id=project_id,
                from_rule_id=duplicate.id,
                to_rule_id=primary.id,
                relation=RuleLineageRelation.MERGED_INTO.value,
                note=f"Merged into rule {primary.id}",
            )
        )

    session.commit()
    session.refresh(primary)
    return primary
