"""Semantic rule identity and lineage (rename/merge/split/supersession)."""

from __future__ import annotations

import hashlib
import re

from ruleatlas_contracts.enums import AuditEntityType, AuditEventType, RuleLineageRelation, RuleStatus
from ruleatlas_persistence.audit import record_audit_event
from ruleatlas_persistence.models import Rule, RuleLineage
from ruleatlas_persistence.repositories import RepositoryFactory
from sqlalchemy.orm import Session


def normalize_identity_text(text: str) -> str:
    t = (text or "").lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def compute_identity_key(*, domain: str | None, actor: str | None, action: str | None, subject: str | None) -> str:
    """Identity independent of exact wording — actor/action/subject/domain."""
    payload = "|".join(
        [
            normalize_identity_text(domain or ""),
            normalize_identity_text(actor or ""),
            normalize_identity_text(action or ""),
            normalize_identity_text(subject or ""),
        ]
    )
    return "id:" + hashlib.sha256(payload.encode()).hexdigest()[:24]


def material_evidence_changed(rule: Rule, new_fingerprint: str) -> bool:
    prior = getattr(rule, "evidence_fingerprint", None) or ""
    return bool(prior) and prior != new_fingerprint


def should_carry_forward_review(rule: Rule, new_fingerprint: str) -> bool:
    """Stale reviews must not carry when evidence changed materially."""
    if material_evidence_changed(rule, new_fingerprint):
        return False
    return rule.status in {RuleStatus.APPROVED, RuleStatus.NEEDS_REVIEW}


def record_lineage(
    session: Session,
    *,
    project_id: str,
    from_rule_id: str,
    to_rule_id: str,
    relation: str,
    actor: str,
    note: str | None = None,
) -> RuleLineage:
    row = RuleLineage(
        project_id=project_id,
        from_rule_id=from_rule_id,
        to_rule_id=to_rule_id,
        relation=relation,
        note=note or "",
        attributes_json={},
    )
    session.add(row)
    session.flush()
    record_audit_event(
        session,
        event_type=AuditEventType.RULE_EDITED,
        summary=f"Rule lineage {relation}: {from_rule_id} → {to_rule_id}",
        project_id=project_id,
        entity_type=AuditEntityType.RULE,
        entity_id=to_rule_id,
        actor=actor,
        metadata={"from_rule_id": from_rule_id, "to_rule_id": to_rule_id, "relation": relation},
    )
    session.commit()
    session.refresh(row)
    return row


def merge_rules(
    session: Session,
    *,
    target_rule_id: str,
    source_rule_id: str,
    actor: str,
) -> Rule:
    rules = RepositoryFactory(session).rules()
    target = rules.get_by_id(target_rule_id)
    source = rules.get_by_id(source_rule_id)
    if target is None or source is None:
        raise LookupError("Rule not found")
    if target.project_id != source.project_id:
        raise ValueError("Rules must share project")
    source.parent_rule_id = target.id
    source.status = RuleStatus.DEPRECATED
    session.add(source)
    record_lineage(
        session,
        project_id=target.project_id,
        from_rule_id=source.id,
        to_rule_id=target.id,
        relation=RuleLineageRelation.MERGED_INTO.value,
        actor=actor,
        note="Manual merge",
    )
    session.refresh(target)
    return target


def supersede_rule(
    session: Session,
    *,
    old_rule_id: str,
    new_rule_id: str,
    actor: str,
) -> Rule:
    rules = RepositoryFactory(session).rules()
    old = rules.get_by_id(old_rule_id)
    new = rules.get_by_id(new_rule_id)
    if old is None or new is None:
        raise LookupError("Rule not found")
    old.status = RuleStatus.DEPRECATED
    new.parent_rule_id = old.id
    session.add(old)
    session.add(new)
    record_lineage(
        session,
        project_id=new.project_id,
        from_rule_id=old.id,
        to_rule_id=new.id,
        relation=RuleLineageRelation.SUPERSEDES.value,
        actor=actor,
    )
    session.refresh(new)
    return new


def find_by_identity(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
    identity_key: str,
) -> Rule | None:
    return RepositoryFactory(session).rules().get_by_identity_key(
        project_id, analysis_version_id, identity_key
    )
