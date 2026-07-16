"""Repositories for normalized test evidence persistence."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import TestAssertion, TestEvidenceCase, TestFixture

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory


class TestEvidenceCaseRepository(BaseRepository[TestEvidenceCase, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(TestEvidenceCase, session, factory)

    def list_for_analysis(
        self, project_id: str, analysis_version_id: str, *, limit: int
    ) -> list[TestEvidenceCase]:
        return list(
            self.statement()
            .where(
                TestEvidenceCase.project_id == project_id,
                TestEvidenceCase.analysis_version_id == analysis_version_id,
            )
            .limit(limit)
            .scalars()
            .all()
        )

    def get_for_analysis(
        self, case_id: str, project_id: str, analysis_version_id: str
    ) -> TestEvidenceCase | None:
        return (
            self.statement()
            .where(
                TestEvidenceCase.id == case_id,
                TestEvidenceCase.project_id == project_id,
                TestEvidenceCase.analysis_version_id == analysis_version_id,
            )
            .scalars()
            .first()
        )

    def count_for_analysis(self, project_id: str, analysis_version_id: str) -> int:
        return (
            self.statement()
            .where(
                TestEvidenceCase.project_id == project_id,
                TestEvidenceCase.analysis_version_id == analysis_version_id,
            )
            .count()
        )

    def get_by_analysis_and_canonical_key(
        self, analysis_version_id: str, canonical_key: str
    ) -> TestEvidenceCase | None:
        return self.first(
            analysis_version_id=analysis_version_id,
            canonical_key=canonical_key,
        )


class TestAssertionRepository(BaseRepository[TestAssertion, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(TestAssertion, session, factory)

    def list_for_case(self, test_evidence_case_id: str) -> list[TestAssertion]:
        return list(
            self.statement()
            .where(TestAssertion.test_evidence_case_id == test_evidence_case_id)
            .scalars()
            .all()
        )

    def list_for_cases(self, case_ids: list[str]) -> list[TestAssertion]:
        if not case_ids:
            return []
        return list(
            self.statement()
            .where(TestAssertion.test_evidence_case_id.in_(case_ids))
            .scalars()
            .all()
        )


class TestFixtureRepository(BaseRepository[TestFixture, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(TestFixture, session, factory)

    def get_by_analysis_and_canonical_key(
        self, analysis_version_id: str, canonical_key: str
    ) -> TestFixture | None:
        return self.first(
            analysis_version_id=analysis_version_id,
            canonical_key=canonical_key,
        )

