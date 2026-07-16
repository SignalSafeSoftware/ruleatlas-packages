"""Reclassify existing rules' category and workflow_group without changing status."""

from __future__ import annotations

from ruleatlas_contracts.classification.rule_category import (
    classify_rule_category,
    classify_workflow_group,
)
from ruleatlas_persistence.models import Rule
from ruleatlas_persistence.repositories import RepositoryFactory
from sqlalchemy.orm import Session


def _business_rule_text(session: Session, rule: Rule) -> str:
    if rule.current_version_id:
        version = RepositoryFactory(session).rule_versions().get_by_id(rule.current_version_id)
        if version is not None and version.business_rule:
            return version.business_rule
    latest = RepositoryFactory(session).rule_versions().get_latest_for_rule(rule.id)
    if latest is not None and latest.business_rule:
        return latest.business_rule
    return rule.name


def reclassify_project_rules(session: Session, project_id: str | None = None) -> dict[str, int]:
    """Recompute category/workflow for rules. Never changes status or approval."""
    rules = RepositoryFactory(session).rules().list_for_reclassify(project_id)
    updated = 0
    for rule in rules:
        text = _business_rule_text(session, rule)
        category = classify_rule_category(text)
        workflow = classify_workflow_group(text)
        if rule.rule_category != category or rule.workflow_group != workflow:
            rule.rule_category = category
            rule.workflow_group = workflow
            session.add(rule)
            updated += 1
    session.commit()
    return {"rules_seen": len(rules), "rules_updated": updated}
