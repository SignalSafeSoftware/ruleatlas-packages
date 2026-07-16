"""Additional domain repositories for full sqlPhilosophy query-boundary coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    Rule,
    RuleEvidence,
)


class RuleEvidenceRepository(BaseRepository[RuleEvidence, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(RuleEvidence, session, factory)

    def list_for_rule_ordered(self, rule_id: str) -> list[RuleEvidence]:
        return list(
            self.statement()
            .where(RuleEvidence.rule_id == rule_id)
            .order_by(RuleEvidence.created_at.desc())
            .scalars()
            .all()
        )

    def get_latest_for_rule(self, rule_id: str) -> RuleEvidence | None:
        return (
            self.statement()
            .where(RuleEvidence.rule_id == rule_id)
            .order_by(RuleEvidence.created_at.desc())
            .limit(1)
            .scalars()
            .first()
        )

    def list_for_rule(self, rule_id: str) -> list[RuleEvidence]:
        return list(self.statement().where(RuleEvidence.rule_id == rule_id).scalars().all())

    def count_for_rule(self, rule_id: str) -> int:
        return self.statement().where(RuleEvidence.rule_id == rule_id).count()

    def list_for_scan_run(self, scan_run_id: str) -> list[RuleEvidence]:
        return list(self.statement().where(RuleEvidence.scan_run_id == scan_run_id).scalars().all())

    def count_for_scan_run(self, scan_run_id: str) -> int:
        return self.statement().where(RuleEvidence.scan_run_id == scan_run_id).count()

    def list_for_rule_limited(self, rule_id: str, *, limit: int) -> list[RuleEvidence]:
        return list(self.statement().where(RuleEvidence.rule_id == rule_id).limit(limit).scalars().all())

    def list_for_rule_ids(self, rule_ids: list[str]) -> list[RuleEvidence]:
        if not rule_ids:
            return []
        return list(self.statement().where(RuleEvidence.rule_id.in_(rule_ids)).scalars().all())

    def list_for_project(
        self,
        project_id: str,
        *,
        analysis_version_id: str | None = None,
        order_by_path: bool = False,
    ) -> list[RuleEvidence]:
        stmt = self.statement().join(Rule, RuleEvidence.rule_id == Rule.id).where(Rule.project_id == project_id)
        if analysis_version_id:
            stmt = stmt.where(Rule.analysis_version_id == analysis_version_id)
        if order_by_path:
            stmt = stmt.order_by(RuleEvidence.reference_path.asc(), RuleEvidence.start_line.asc())
        return list(stmt.scalars().all())

    def top_rules_by_evidence_count(self, project_id: str, *, limit: int = 5) -> list[tuple[str, int]]:
        rows = (
            self.statement()
            .select_columns(Rule.id, func.count(RuleEvidence.id).label("evidence_count"))
            .join(Rule, RuleEvidence.rule_id == Rule.id)
            .where(Rule.project_id == project_id)
            .group_by(Rule.id)
            .order_by(func.count(RuleEvidence.id).desc())
            .limit(limit)
            .mappings()
            .all()
        )
        return [(str(row["id"]), int(cast(str | int, row["evidence_count"]))) for row in rows]

    def count_for_project(self, project_id: str) -> int:
        return self.statement().join(Rule, RuleEvidence.rule_id == Rule.id).where(Rule.project_id == project_id).count()

    def list_for_line_with_rule(
        self,
        project_id: str,
        source_file_id: str,
        line_number: int,
        *,
        analysis_version_id: str | None = None,
    ) -> list[RuleEvidence]:
        stmt = (
            self.statement()
            .join(Rule, RuleEvidence.rule_id == Rule.id)
            .where(
                Rule.project_id == project_id,
                RuleEvidence.source_file_id == source_file_id,
                RuleEvidence.start_line <= line_number,
                RuleEvidence.end_line >= line_number,
            )
        )
        if analysis_version_id:
            stmt = stmt.where(Rule.analysis_version_id == analysis_version_id)
        return list(stmt.scalars().all())

    def list_for_symbol_with_rule(
        self,
        project_id: str,
        source_file_id: str,
        start_line: int,
        end_line: int,
        *,
        analysis_version_id: str | None = None,
    ) -> list[RuleEvidence]:
        stmt = (
            self.statement()
            .join(Rule, RuleEvidence.rule_id == Rule.id)
            .where(
                Rule.project_id == project_id,
                RuleEvidence.source_file_id == source_file_id,
                RuleEvidence.start_line >= start_line,
                RuleEvidence.end_line <= end_line,
            )
        )
        if analysis_version_id:
            stmt = stmt.where(Rule.analysis_version_id == analysis_version_id)
        return list(stmt.scalars().all())

    def list_for_analysis_version(self, analysis_version_id: str) -> list[RuleEvidence]:
        return list(
            self.statement()
            .join(Rule, RuleEvidence.rule_id == Rule.id)
            .where(Rule.analysis_version_id == analysis_version_id)
            .scalars()
            .all()
        )

    def list_for_project_joined_rules(
        self,
        project_id: str,
        *,
        analysis_version_id: str | None = None,
        order_by_path: bool = False,
    ) -> list[tuple[RuleEvidence, Rule]]:
        stmt = (
            self.statement()
            .select_columns(RuleEvidence, Rule)
            .join(Rule, RuleEvidence.rule_id == Rule.id)
            .where(Rule.project_id == project_id)
        )
        if analysis_version_id:
            stmt = stmt.where(Rule.analysis_version_id == analysis_version_id)
        if order_by_path:
            stmt = stmt.order_by(RuleEvidence.reference_path.asc())
        return cast(list[tuple[RuleEvidence, Rule]], self._session.execute(stmt.build_select()).all())

    def count_by_reference_path_for_project(self, project_id: str) -> dict[str, int]:
        rows = (
            self.statement()
            .select_columns(RuleEvidence.reference_path, func.count().label("count"))
            .join(Rule, Rule.id == RuleEvidence.rule_id)
            .where(Rule.project_id == project_id)
            .group_by(RuleEvidence.reference_path)
            .mappings()
            .all()
        )
        return {
            str(row["reference_path"]): int(cast(str | int, row["count"]))
            for row in rows
            if row["reference_path"]
        }

    def list_overlapping_line_for_source_file(
        self, project_id: str, source_file_id: str, line_number: int
    ) -> list[tuple[RuleEvidence, Rule]]:
        return cast(
            list[tuple[RuleEvidence, Rule]],
            self._session.execute(
                self.statement()
                .select_columns(RuleEvidence, Rule)
                .join(Rule, RuleEvidence.rule_id == Rule.id)
                .where(
                    Rule.project_id == project_id,
                    RuleEvidence.source_file_id == source_file_id,
                    RuleEvidence.start_line <= line_number,
                    RuleEvidence.end_line >= line_number,
                )
                .build_select()
            ).all(),
        )

    def get_by_dedup_key(
        self,
        rule_id: str,
        scan_run_id: str,
        source_file_id: str,
        start_line: int | None,
        end_line: int | None,
        claim_text: str,
    ) -> RuleEvidence | None:
        return (
            self.statement()
            .where(
                RuleEvidence.rule_id == rule_id,
                RuleEvidence.scan_run_id == scan_run_id,
                RuleEvidence.source_file_id == source_file_id,
                RuleEvidence.start_line == start_line,
                RuleEvidence.end_line == end_line,
                RuleEvidence.claim_text == claim_text,
            )
            .scalars()
            .first()
        )
