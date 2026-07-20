"""Repositories for claim clusters and composite pipeline runs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    ClaimCluster,
    ClaimClusterMembership,
    ClaimEmbedding,
    CompositePipelineRun,
)

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory


class ClaimClusterRepository(BaseRepository[ClaimCluster, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(ClaimCluster, session, factory)

    def list_for_analysis_ordered_by_score(
        self, project_id: str, analysis_version_id: str
    ) -> list[ClaimCluster]:
        return list(
            self.statement()
            .where(
                ClaimCluster.project_id == project_id,
                ClaimCluster.analysis_version_id == analysis_version_id,
            )
            .order_by(ClaimCluster.score.desc())
            .scalars()
            .all()
        )

    def count_for_project(self, project_id: str) -> int:
        return self.statement().where(ClaimCluster.project_id == project_id).count()

    def list_for_canonicalization(
        self, project_id: str, analysis_version_id: str, *, exclude_status: str
    ) -> list[ClaimCluster]:
        return list(
            self.statement()
            .where(
                ClaimCluster.project_id == project_id,
                ClaimCluster.analysis_version_id == analysis_version_id,
                ClaimCluster.status != exclude_status,
            )
            .order_by(ClaimCluster.score.desc())
            .scalars()
            .all()
        )

    def list_unlocked_emit_candidates(
        self,
        project_id: str,
        analysis_version_id: str,
        *,
        cluster_roles: list[str],
        limit: int = 20,
    ) -> list[ClaimCluster]:
        return list(
            self.statement()
            .where(
                ClaimCluster.project_id == project_id,
                ClaimCluster.analysis_version_id == analysis_version_id,
                ClaimCluster.is_locked.is_(False),
                ClaimCluster.cluster_role.in_(cluster_roles),
            )
            .order_by(ClaimCluster.score.desc())
            .limit(limit)
            .scalars()
            .all()
        )

    def list_by_ids_ordered_by_score(self, cluster_ids: list[str]) -> list[ClaimCluster]:
        if not cluster_ids:
            return []
        return list(
            self.statement()
            .where(ClaimCluster.id.in_(cluster_ids))
            .order_by(ClaimCluster.score.desc())
            .scalars()
            .all()
        )

    def list_by_ids(self, cluster_ids: set[str] | list[str]) -> list[ClaimCluster]:
        if not cluster_ids:
            return []
        return list(self.statement().where(ClaimCluster.id.in_(cluster_ids)).scalars().all())

    def count_for_analysis(self, project_id: str, analysis_version_id: str) -> int:
        return (
            self.statement()
            .where(
                ClaimCluster.project_id == project_id,
                ClaimCluster.analysis_version_id == analysis_version_id,
            )
            .count()
        )

    def get_for_analysis(
        self, cluster_id: str, project_id: str, analysis_version_id: str
    ) -> ClaimCluster | None:
        return (
            self.statement()
            .where(
                ClaimCluster.id == cluster_id,
                ClaimCluster.project_id == project_id,
                ClaimCluster.analysis_version_id == analysis_version_id,
            )
            .scalars()
            .first()
        )

    def list_by_lock_state(
        self, project_id: str, analysis_version_id: str, *, is_locked: bool
    ) -> list[ClaimCluster]:
        return list(
            self.statement()
            .where(
                ClaimCluster.project_id == project_id,
                ClaimCluster.analysis_version_id == analysis_version_id,
                ClaimCluster.is_locked.is_(is_locked),
            )
            .scalars()
            .all()
        )

    def get_embedding(
        self,
        analysis_version_id: str,
        content_hash: str,
        model_key: str,
        model_version: str,
    ) -> ClaimEmbedding | None:
        return (
            self.factory.repository(ClaimEmbedding)
            .statement()
            .where(
                ClaimEmbedding.analysis_version_id == analysis_version_id,
                ClaimEmbedding.content_hash == content_hash,
                ClaimEmbedding.model_key == model_key,
                ClaimEmbedding.model_version == model_version,
            )
            .scalars()
            .first()
        )


class ClaimClusterMembershipRepository(BaseRepository[ClaimClusterMembership, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(ClaimClusterMembership, session, factory)

    def count_for_cluster(self, claim_cluster_id: str) -> int:
        return (
            self.statement()
            .where(ClaimClusterMembership.claim_cluster_id == claim_cluster_id)
            .count()
        )

    def list_for_cluster_limited(
        self, claim_cluster_id: str, *, limit: int
    ) -> list[ClaimClusterMembership]:
        return list(
            self.statement()
            .where(ClaimClusterMembership.claim_cluster_id == claim_cluster_id)
            .limit(limit)
            .scalars()
            .all()
        )

    def list_for_cluster(self, claim_cluster_id: str) -> list[ClaimClusterMembership]:
        return list(
            self.statement()
            .where(ClaimClusterMembership.claim_cluster_id == claim_cluster_id)
            .scalars()
            .all()
        )

    def list_for_claim(self, source_claim_id: str) -> list[ClaimClusterMembership]:
        return list(
            self.statement()
            .where(ClaimClusterMembership.source_claim_id == source_claim_id)
            .scalars()
            .all()
        )

    def get_for_cluster_and_claim(
        self, claim_cluster_id: str, source_claim_id: str
    ) -> ClaimClusterMembership | None:
        return (
            self.statement()
            .where(
                ClaimClusterMembership.claim_cluster_id == claim_cluster_id,
                ClaimClusterMembership.source_claim_id == source_claim_id,
            )
            .scalars()
            .first()
        )

    def list_for_cluster_claim_ids(
        self, claim_cluster_id: str, source_claim_ids: list[str]
    ) -> list[ClaimClusterMembership]:
        if not source_claim_ids:
            return []
        return list(
            self.statement()
            .where(
                ClaimClusterMembership.claim_cluster_id == claim_cluster_id,
                ClaimClusterMembership.source_claim_id.in_(source_claim_ids),
            )
            .scalars()
            .all()
        )


class CompositePipelineRunRepository(BaseRepository[CompositePipelineRun, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(CompositePipelineRun, session, factory)

    def list_for_analysis_recent(
        self, project_id: str, analysis_version_id: str, *, limit: int = 20
    ) -> list[CompositePipelineRun]:
        return list(
            self.statement()
            .where(
                CompositePipelineRun.project_id == project_id,
                CompositePipelineRun.analysis_version_id == analysis_version_id,
            )
            .order_by(CompositePipelineRun.created_at.desc())
            .limit(limit)
            .scalars()
            .all()
        )

    def get_latest_for_analysis(
        self, project_id: str, analysis_version_id: str
    ) -> CompositePipelineRun | None:
        return (
            self.statement()
            .where(
                CompositePipelineRun.project_id == project_id,
                CompositePipelineRun.analysis_version_id == analysis_version_id,
            )
            .order_by(CompositePipelineRun.created_at.desc())
            .limit(1)
            .scalars()
            .first()
        )
