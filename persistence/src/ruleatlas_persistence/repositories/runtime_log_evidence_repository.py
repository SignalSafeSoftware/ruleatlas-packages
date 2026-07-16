"""Additional domain repositories for full sqlPhilosophy query-boundary coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    Rule,
    RuntimeEvidenceImport,
    RuntimeLogEvidence,
)

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory


class RuntimeLogEvidenceRepository(BaseRepository[RuntimeLogEvidence, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(RuntimeLogEvidence, session, factory)
        self._rules = factory.rules()
        self._imports = factory.runtime_evidence_imports()

    def list_for_project(
        self,
        project_id: str,
        *,
        analysis_version_id: str | None = None,
        rule_id: str | None = None,
        import_id: str | None = None,
        source_type: str | None = None,
        order_asc: bool = False,
    ) -> list[RuntimeLogEvidence]:
        stmt = self.statement().where(RuntimeLogEvidence.project_id == project_id)
        if analysis_version_id:
            rule_ids = (
                self._rules.statement()
                .select_columns(Rule.id)
                .where(
                    Rule.project_id == project_id,
                    Rule.analysis_version_id == analysis_version_id,
                )
            )
            import_ids = (
                self._imports.statement()
                .select_columns(RuntimeEvidenceImport.id)
                .where(
                    RuntimeEvidenceImport.project_id == project_id,
                    RuntimeEvidenceImport.analysis_version_id == analysis_version_id,
                )
            )
            stmt = stmt.where(
                or_(
                    RuntimeLogEvidence.rule_id.in_(rule_ids.build_select()),
                    RuntimeLogEvidence.import_id.in_(import_ids.build_select()),
                )
            )
        if rule_id:
            stmt = stmt.where(RuntimeLogEvidence.rule_id == rule_id)
        if import_id:
            stmt = stmt.where(RuntimeLogEvidence.import_id == import_id)
        if source_type:
            stmt = stmt.where(RuntimeLogEvidence.source_type == source_type)
        order = RuntimeLogEvidence.created_at.asc() if order_asc else RuntimeLogEvidence.created_at.desc()
        return list(stmt.order_by(order).scalars().all())

    def get_first_for_project(self, project_id: str) -> RuntimeLogEvidence | None:
        return self.statement().where(RuntimeLogEvidence.project_id == project_id).limit(1).scalars().first()

    def count_for_project(self, project_id: str) -> int:
        return self.statement().where(RuntimeLogEvidence.project_id == project_id).count()

    def exists_for_project(self, project_id: str) -> bool:
        return (
            self.statement()
            .select_columns(RuntimeLogEvidence.id)
            .where(RuntimeLogEvidence.project_id == project_id)
            .limit(1)
            .scalars()
            .first()
            is not None
        )

    def exists_for_import_ids(self, project_id: str, import_ids: list[str]) -> bool:
        if not import_ids:
            return False
        return (
            self.statement()
            .select_columns(RuntimeLogEvidence.id)
            .where(
                RuntimeLogEvidence.project_id == project_id,
                RuntimeLogEvidence.import_id.in_(import_ids),
            )
            .limit(1)
            .scalars()
            .first()
            is not None
        )

    def list_for_rule(self, rule_id: str) -> list[RuntimeLogEvidence]:
        return list(self.statement().where(RuntimeLogEvidence.rule_id == rule_id).scalars().all())
