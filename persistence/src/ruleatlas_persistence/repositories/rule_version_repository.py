"""Domain repositories for sqlPhilosophy slices 2-8."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    RuleVersion,
)


class RuleVersionRepository(BaseRepository[RuleVersion, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(RuleVersion, session, factory)

    def list_for_rule(self, rule_id: str) -> list[RuleVersion]:
        return list(
            self.statement()
            .where(RuleVersion.rule_id == rule_id)
            .order_by(RuleVersion.version_number.desc())
            .scalars()
            .all()
        )

    def map_rule_id_for_scan_run(self, scan_run_id: str) -> dict[str, RuleVersion]:
        return {row.rule_id: row for row in self.list_for_scan_run(scan_run_id)}

    def list_for_scan_run(self, scan_run_id: str) -> list[RuleVersion]:
        return list(self.statement().where(RuleVersion.scan_run_id == scan_run_id).scalars().all())

    def count_for_rule(self, rule_id: str) -> int:
        return self.statement().where(RuleVersion.rule_id == rule_id).count()

    def count_for_scan_run(self, scan_run_id: str) -> int:
        return self.statement().where(RuleVersion.scan_run_id == scan_run_id).count()

    def get_latest_for_rule(self, rule_id: str) -> RuleVersion | None:
        return (
            self.statement()
            .where(RuleVersion.rule_id == rule_id)
            .order_by(RuleVersion.version_number.desc())
            .limit(1)
            .scalars()
            .first()
        )

    def max_version_number_for_rule(self, rule_id: str) -> int | None:
        return (
            self.statement()
            .select_columns(func.max(RuleVersion.version_number))
            .where(RuleVersion.rule_id == rule_id)
            .scalar()
        )

    def map_by_ids(self, version_ids: set[str]) -> dict[str, RuleVersion]:
        if not version_ids:
            return {}
        rows = list(self.statement().where(RuleVersion.id.in_(version_ids)).scalars().all())
        return {row.id: row for row in rows}
