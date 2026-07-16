from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from ruleatlas_contracts.enums import RuleStatus
from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlphilosophy.sorting import ListQuery
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    Rule,
)


class RuleRepository(BaseRepository[Rule, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(Rule, session, factory)

    def get_first_for_project(self, project_id: str) -> Rule | None:
        return self.statement().where(Rule.project_id == project_id).limit(1).scalars().first()

    def get_first_for_analysis_version(self, analysis_version_id: str) -> Rule | None:
        return self.statement().where(Rule.analysis_version_id == analysis_version_id).limit(1).scalars().first()

    def list_for_project(
        self, project_id: str, query: ListQuery | None = None, *, analysis_version_id: str | None = None
    ) -> list[Rule]:
        stmt = self.statement().where(Rule.project_id == project_id)
        if analysis_version_id:
            stmt = stmt.where(Rule.analysis_version_id == analysis_version_id)
        if query is None:
            return list(stmt.order_by(Rule.updated_at.desc()).scalars().all())
        return list(
            stmt.order_by(Rule.updated_at.desc())
            .offset(query.offset)
            .limit(query.limit)
            .scalars()
            .all()
        )

    def get_for_project_version(self, rule_id: str, project_id: str, analysis_version_id: str) -> Rule | None:
        rule = self.get_by_id(rule_id)
        if rule is None or rule.project_id != project_id:
            return None
        if rule.analysis_version_id != analysis_version_id:
            return None
        return rule

    def get_for_project(self, rule_id: str, project_id: str) -> Rule | None:
        rule = self.get_by_id(rule_id)
        if rule is None or rule.project_id != project_id:
            return None
        return rule

    def map_by_id_for_version(self, project_id: str, analysis_version_id: str) -> dict[str, Rule]:
        rules = self.list_for_project(project_id, analysis_version_id=analysis_version_id)
        return {rule.id: rule for rule in rules}

    def list_ids_for_analysis_version(self, analysis_version_id: str) -> list[str]:
        return cast(
            list[str],
            self.statement()
            .select_columns(Rule.id)
            .where(Rule.analysis_version_id == analysis_version_id)
            .scalars()
            .all(),
        )

    def list_for_analysis_version(self, analysis_version_id: str) -> list[Rule]:
        return list(self.statement().where(Rule.analysis_version_id == analysis_version_id).scalars().all())

    def list_for_project_version_limited(
        self, project_id: str, analysis_version_id: str, *, limit: int = 500
    ) -> list[Rule]:
        return list(
            self.statement()
            .where(Rule.project_id == project_id, Rule.analysis_version_id == analysis_version_id)
            .limit(limit)
            .scalars()
            .all()
        )

    def list_by_statuses(self, project_id: str, statuses: list) -> list[Rule]:
        return list(self.statement().where(Rule.project_id == project_id, Rule.status.in_(statuses)).scalars().all())

    def map_by_id(self, rule_ids: set[str]) -> dict[str, Rule]:
        if not rule_ids:
            return {}
        rules = list(self.statement().where(Rule.id.in_(rule_ids)).scalars().all())
        return {rule.id: rule for rule in rules}

    def list_ids_for_project_version(self, project_id: str, analysis_version_id: str) -> list[str]:
        return cast(
            list[str],
            self.statement()
            .select_columns(Rule.id)
            .where(
                Rule.project_id == project_id,
                Rule.analysis_version_id == analysis_version_id,
            )
            .scalars()
            .all(),
        )

    def get_by_stable_key_for_version(self, project_id: str, stable_key: str, analysis_version_id: str) -> Rule | None:
        return self.first(
            project_id=project_id,
            stable_key=stable_key,
            analysis_version_id=analysis_version_id,
        )

    def get_by_identity_key(
        self, project_id: str, analysis_version_id: str, identity_key: str
    ) -> Rule | None:
        return (
            self.statement()
            .where(
                Rule.project_id == project_id,
                Rule.analysis_version_id == analysis_version_id,
                Rule.identity_key == identity_key,
            )
            .scalars()
            .first()
        )

    def list_unlabeled_for_project(self, project_id: str) -> list[Rule]:
        return list(
            self.statement()
            .where(
                Rule.project_id == project_id,
                or_(Rule.workflow_group.is_(None), Rule.workflow_group == ""),
            )
            .scalars()
            .all()
        )

    def list_by_workflow_group_for_project(self, project_id: str, workflow_group: str) -> list[Rule]:
        return list(
            self.statement()
            .where(
                Rule.project_id == project_id,
                Rule.workflow_group == workflow_group,
            )
            .scalars()
            .all()
        )

    def list_children_by_parent_id(self, parent_rule_id: str) -> list[Rule]:
        return list(self.statement().where(Rule.parent_rule_id == parent_rule_id).scalars().all())

    def list_siblings_by_workflow_group(self, project_id: str, workflow_group: str, except_rule_id: str) -> list[Rule]:
        return list(
            self.statement()
            .where(
                Rule.project_id == project_id,
                Rule.workflow_group == workflow_group,
                Rule.id != except_rule_id,
            )
            .scalars()
            .all()
        )

    def list_for_project_by_name(self, project_id: str, *, analysis_version_id: str | None = None) -> list[Rule]:
        stmt = self.statement().where(Rule.project_id == project_id)
        if analysis_version_id:
            stmt = stmt.where(Rule.analysis_version_id == analysis_version_id)
        return list(stmt.order_by(Rule.name.asc()).scalars().all())

    def ids_for_project(self, project_id: str) -> list[str]:
        return cast(
            list[str],
            self.statement().select_columns(Rule.id).where(Rule.project_id == project_id).scalars().all(),
        )

    def count_for_project(self, project_id: str) -> int:
        return self.statement().where(Rule.project_id == project_id).count()

    def list_by_stable_keys_for_project(
        self, project_id: str, stable_keys: list[str]
    ) -> list[Rule]:
        if not stable_keys:
            return []
        return list(
            self.statement()
            .where(Rule.project_id == project_id, Rule.stable_key.in_(stable_keys))
            .scalars()
            .all()
        )

    def count_by_stable_keys_and_status(
        self, project_id: str, stable_keys: list[str], status: str
    ) -> int:
        if not stable_keys:
            return 0
        return (
            self.statement()
            .where(
                Rule.project_id == project_id,
                Rule.stable_key.in_(stable_keys),
                Rule.status == status,
            )
            .count()
        )

    def list_for_dedup_candidates(self, project_id: str) -> list[Rule]:
        return list(
            self.statement()
            .where(
                Rule.project_id == project_id,
                Rule.status.in_([RuleStatus.CANDIDATE, RuleStatus.NEEDS_REVIEW]),
                Rule.deprecated_at.is_(None),
            )
            .scalars()
            .all()
        )

    def list_for_reclassify(self, project_id: str | None = None) -> list[Rule]:
        stmt = self.statement()
        if project_id:
            stmt = stmt.where(Rule.project_id == project_id)
        return list(stmt.scalars().all())

    def list_for_workflow_analysis(
        self,
        project_id: str,
        *,
        analysis_version_id: str | None,
        statuses: list,
    ) -> list[Rule]:
        stmt = self.statement().where(
            Rule.project_id == project_id,
            Rule.deprecated_at.is_(None),
            Rule.status.in_(statuses),
        )
        if analysis_version_id:
            stmt = stmt.where(Rule.analysis_version_id == analysis_version_id)
        return list(stmt.scalars().all())
