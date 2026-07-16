"""Batch-friendly helpers for rule version text and display titles."""

from __future__ import annotations

from ruleatlas_contracts.classification.rule_display import build_rule_display_title
from ruleatlas_persistence.models import Rule, RuleVersion
from ruleatlas_persistence.repositories import RepositoryFactory
from sqlalchemy.orm import Session


def load_rule_versions_by_id(session: Session, version_ids: set[str]) -> dict[str, RuleVersion]:
    return RepositoryFactory(session).rule_versions().map_by_ids(version_ids)


def rule_business_rule(
    rule: Rule,
    *,
    versions_by_id: dict[str, RuleVersion] | None = None,
    session: Session | None = None,
) -> str:
    if rule.current_version_id:
        version: RuleVersion | None = None
        if versions_by_id is not None:
            version = versions_by_id.get(rule.current_version_id)
        elif session is not None:
            version = RepositoryFactory(session).rule_versions().get_by_id(rule.current_version_id)
        if version is not None:
            return version.business_rule
    return rule.name


def rule_business_rule_or_none(
    rule: Rule,
    *,
    versions_by_id: dict[str, RuleVersion] | None = None,
    session: Session | None = None,
) -> str | None:
    if not rule.current_version_id:
        return None
    if versions_by_id is not None:
        version = versions_by_id.get(rule.current_version_id)
    elif session is not None:
        version = RepositoryFactory(session).rule_versions().get_by_id(rule.current_version_id)
    else:
        return None
    if version is None:
        return None
    return version.business_rule


def rule_display_title(
    rule: Rule,
    *,
    versions_by_id: dict[str, RuleVersion] | None = None,
    session: Session | None = None,
) -> str:
    return build_rule_display_title(
        name=rule.name,
        business_rule=rule_business_rule(rule, versions_by_id=versions_by_id, session=session),
    )


def load_rules_by_id(session: Session, rule_ids: set[str]) -> dict[str, Rule]:
    return RepositoryFactory(session).rules().map_by_id(rule_ids)


def build_rule_titles(
    session: Session,
    rule_ids: set[str],
) -> dict[str, str]:
    """Return display titles keyed by rule id."""
    rules = load_rules_by_id(session, rule_ids)
    version_ids = {rule.current_version_id for rule in rules.values() if rule.current_version_id}
    versions = load_rule_versions_by_id(session, version_ids)
    titles: dict[str, str] = {}
    for rule_id, rule in rules.items():
        titles[rule_id] = rule_display_title(rule, versions_by_id=versions)
    for rule_id in rule_ids:
        titles.setdefault(rule_id, rule_id)
    return titles
