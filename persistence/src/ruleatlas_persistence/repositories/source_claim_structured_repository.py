"""Repositories for structured SourceClaim (distinct from legacy RuleSourceClaim)."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import SourceClaim, SourceClaimEvidence

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory


class SourceClaimStructuredRepository(BaseRepository[SourceClaim, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(SourceClaim, session, factory)

    def list_for_analysis(
        self,
        project_id: str,
        analysis_version_id: str,
        *,
        provider_key: str | None = None,
        limit: int = 200,
    ) -> list[SourceClaim]:
        stmt = self.statement().where(
            SourceClaim.project_id == project_id,
            SourceClaim.analysis_version_id == analysis_version_id,
        )
        if provider_key:
            stmt = stmt.where(SourceClaim.provider_key == provider_key)
        return list(stmt.limit(min(limit, 500)).scalars().all())

    def list_all_for_analysis(self, project_id: str, analysis_version_id: str) -> list[SourceClaim]:
        return list(
            self.statement()
            .where(
                SourceClaim.project_id == project_id,
                SourceClaim.analysis_version_id == analysis_version_id,
            )
            .scalars()
            .all()
        )

    def list_for_analysis_ordered(
        self, project_id: str, analysis_version_id: str
    ) -> list[SourceClaim]:
        return list(
            self.statement()
            .where(
                SourceClaim.project_id == project_id,
                SourceClaim.analysis_version_id == analysis_version_id,
            )
            .order_by(SourceClaim.created_at.asc(), SourceClaim.id.asc())
            .scalars()
            .all()
        )

    def search_for_analysis(
        self,
        project_id: str,
        analysis_version_id: str,
        *,
        query: str = "",
        limit: int = 20,
    ) -> list[SourceClaim]:
        stmt = self.statement().where(
            SourceClaim.project_id == project_id,
            SourceClaim.analysis_version_id == analysis_version_id,
        )
        if query:
            stmt = stmt.where(SourceClaim.claim_text.ilike(f"%{query}%"))
        return list(stmt.limit(limit).scalars().all())

    def list_for_analysis_ordered_by_id(
        self, project_id: str, analysis_version_id: str
    ) -> list[SourceClaim]:
        return list(
            self.statement()
            .where(
                SourceClaim.project_id == project_id,
                SourceClaim.analysis_version_id == analysis_version_id,
            )
            .order_by(SourceClaim.id.asc())
            .scalars()
            .all()
        )

    def list_by_ids(self, claim_ids: list[str]) -> list[SourceClaim]:
        if not claim_ids:
            return []
        return list(self.statement().where(SourceClaim.id.in_(claim_ids)).scalars().all())

    def list_for_project(self, project_id: str) -> list[SourceClaim]:
        return list(self.statement().where(SourceClaim.project_id == project_id).scalars().all())

    def count_for_project(self, project_id: str) -> int:
        return self.statement().where(SourceClaim.project_id == project_id).count()

    def list_roles_for_analysis(self, project_id: str, analysis_version_id: str) -> list[str]:
        return cast(
            list[str],
            self.statement()
            .select_columns(SourceClaim.claim_role)
            .where(
                SourceClaim.project_id == project_id,
                SourceClaim.analysis_version_id == analysis_version_id,
            )
            .scalars()
            .all(),
        )

    def count_for_analysis(self, project_id: str, analysis_version_id: str) -> int:
        return (
            self.statement()
            .where(
                SourceClaim.project_id == project_id,
                SourceClaim.analysis_version_id == analysis_version_id,
            )
            .count()
        )

    def count_for_analysis_version(self, analysis_version_id: str) -> int:
        return self.statement().where(SourceClaim.analysis_version_id == analysis_version_id).count()

    def list_for_analysis_by_provider(
        self, project_id: str, analysis_version_id: str, provider_key: str
    ) -> list[SourceClaim]:
        return list(
            self.statement()
            .where(
                SourceClaim.project_id == project_id,
                SourceClaim.analysis_version_id == analysis_version_id,
                SourceClaim.provider_key == provider_key,
            )
            .scalars()
            .all()
        )

    def list_for_analysis_by_role(
        self, project_id: str, analysis_version_id: str, claim_role: str
    ) -> list[SourceClaim]:
        return list(
            self.statement()
            .where(
                SourceClaim.project_id == project_id,
                SourceClaim.analysis_version_id == analysis_version_id,
                SourceClaim.claim_role == claim_role,
            )
            .scalars()
            .all()
        )

    def get_for_analysis(
        self, claim_id: str, project_id: str, analysis_version_id: str
    ) -> SourceClaim | None:
        return (
            self.statement()
            .where(
                SourceClaim.id == claim_id,
                SourceClaim.project_id == project_id,
                SourceClaim.analysis_version_id == analysis_version_id,
            )
            .scalars()
            .first()
        )

    def get_by_canonical_key(self, analysis_version_id: str, canonical_key: str) -> SourceClaim | None:
        return (
            self.statement()
            .where(
                SourceClaim.analysis_version_id == analysis_version_id,
                SourceClaim.canonical_key == canonical_key,
            )
            .scalars()
            .first()
        )


class SourceClaimEvidenceRepository(BaseRepository[SourceClaimEvidence, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(SourceClaimEvidence, session, factory)

    def list_for_claim(self, source_claim_id: str) -> list[SourceClaimEvidence]:
        return list(
            self.statement().where(SourceClaimEvidence.source_claim_id == source_claim_id).scalars().all()
        )
