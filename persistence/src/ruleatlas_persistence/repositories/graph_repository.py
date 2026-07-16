"""Repositories for RuleAtlas graph persistence."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    GraphCommunity,
    GraphEdge,
    GraphHyperedge,
    GraphNode,
    GraphObservation,
    GraphProviderRun,
)

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory


class GraphProviderRunRepository(BaseRepository[GraphProviderRun, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(GraphProviderRun, session, factory)

    def list_for_analysis(self, project_id: str, analysis_version_id: str) -> list[GraphProviderRun]:
        return list(
            self.statement()
            .where(
                GraphProviderRun.project_id == project_id,
                GraphProviderRun.analysis_version_id == analysis_version_id,
            )
            .scalars()
            .all()
        )

    def list_for_analysis_ordered(
        self, project_id: str, analysis_version_id: str
    ) -> list[GraphProviderRun]:
        return list(
            self.statement()
            .where(
                GraphProviderRun.project_id == project_id,
                GraphProviderRun.analysis_version_id == analysis_version_id,
            )
            .order_by(GraphProviderRun.created_at.desc())
            .scalars()
            .all()
        )

    def get_by_payload(
        self, project_id: str, analysis_version_id: str, provider_key: str, raw_payload_hash: str
    ) -> GraphProviderRun | None:
        return self.first(
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            provider_key=provider_key,
            raw_payload_hash=raw_payload_hash,
        )


class GraphNodeRepository(BaseRepository[GraphNode, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(GraphNode, session, factory)

    def get_for_analysis(self, project_id: str, analysis_version_id: str, node_id: str) -> GraphNode | None:
        return (
            self.statement()
            .where(
                GraphNode.project_id == project_id,
                GraphNode.analysis_version_id == analysis_version_id,
                GraphNode.id == node_id,
            )
            .scalars()
            .first()
        )

    def get_by_canonical_key(
        self, analysis_version_id: str, canonical_key: str
    ) -> GraphNode | None:
        return (
            self.statement()
            .where(
                GraphNode.analysis_version_id == analysis_version_id,
                GraphNode.canonical_key == canonical_key,
            )
            .scalars()
            .first()
        )

    def get_by_display_name(
        self, project_id: str, analysis_version_id: str, display_name: str
    ) -> GraphNode | None:
        return (
            self.statement()
            .where(
                GraphNode.project_id == project_id,
                GraphNode.analysis_version_id == analysis_version_id,
                GraphNode.display_name == display_name,
            )
            .scalars()
            .first()
        )

    def list_for_analysis(self, project_id: str, analysis_version_id: str) -> list[GraphNode]:
        return list(
            self.statement()
            .where(
                GraphNode.project_id == project_id,
                GraphNode.analysis_version_id == analysis_version_id,
            )
            .scalars()
            .all()
        )

    def list_by_ids(
        self, project_id: str, analysis_version_id: str, node_ids: list[str]
    ) -> list[GraphNode]:
        if not node_ids:
            return []
        return list(
            self.statement()
            .where(
                GraphNode.project_id == project_id,
                GraphNode.analysis_version_id == analysis_version_id,
                GraphNode.id.in_(node_ids),
            )
            .scalars()
            .all()
        )

    def list_canonical_keys(self, project_id: str, analysis_version_id: str) -> list[str]:
        return [
            str(canonical_key)
            for canonical_key in (
            self.statement()
            .select_columns(GraphNode.canonical_key)
            .where(
                GraphNode.project_id == project_id,
                GraphNode.analysis_version_id == analysis_version_id,
            )
            .scalars()
            .all()
            )
        ]

    def list_by_source_path(
        self, project_id: str, analysis_version_id: str, source_path: str
    ) -> list[GraphNode]:
        return list(
            self.statement()
            .where(
                GraphNode.project_id == project_id,
                GraphNode.analysis_version_id == analysis_version_id,
                GraphNode.source_path == source_path,
            )
            .scalars()
            .all()
        )

    def get_by_source_path(
        self, project_id: str, analysis_version_id: str, source_path: str
    ) -> GraphNode | None:
        return (
            self.statement()
            .where(
                GraphNode.project_id == project_id,
                GraphNode.analysis_version_id == analysis_version_id,
                GraphNode.source_path == source_path,
            )
            .scalars()
            .first()
        )

    def list_by_canonical_key_contains(
        self, project_id: str, analysis_version_id: str, hint: str, *, limit: int = 3
    ) -> list[GraphNode]:
        return list(
            self.statement()
            .where(
                GraphNode.project_id == project_id,
                GraphNode.analysis_version_id == analysis_version_id,
                GraphNode.canonical_key.contains(f":{hint}"),
            )
            .limit(limit)
            .scalars()
            .all()
        )


class GraphEdgeRepository(BaseRepository[GraphEdge, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(GraphEdge, session, factory)

    def list_incident_limited(
        self,
        project_id: str,
        analysis_version_id: str,
        node_ids: list[str],
        *,
        edge_types: list[str] | None = None,
        limit: int,
    ) -> list[GraphEdge]:
        if not node_ids:
            return []
        stmt = self.statement().where(
            GraphEdge.project_id == project_id,
            GraphEdge.analysis_version_id == analysis_version_id,
            GraphEdge.from_node_id.in_(node_ids) | GraphEdge.to_node_id.in_(node_ids),
        )
        if edge_types:
            stmt = stmt.where(GraphEdge.edge_type.in_(edge_types))
        return list(stmt.limit(limit).scalars().all())

    def list_for_node_limited(
        self, project_id: str, analysis_version_id: str, node_id: str, *, limit: int = 20
    ) -> list[GraphEdge]:
        return list(
            self.statement()
            .where(
                GraphEdge.project_id == project_id,
                GraphEdge.analysis_version_id == analysis_version_id,
                (GraphEdge.from_node_id == node_id) | (GraphEdge.to_node_id == node_id),
            )
            .limit(limit)
            .scalars()
            .all()
        )

    def get_by_analysis_and_canonical_key(
        self, analysis_version_id: str, canonical_key: str
    ) -> GraphEdge | None:
        return self.first(
            analysis_version_id=analysis_version_id,
            canonical_key=canonical_key,
        )


class GraphObservationRepository(BaseRepository[GraphObservation, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(GraphObservation, session, factory)

    def list_for_node(self, node_id: str) -> list[GraphObservation]:
        return list(self.statement().where(GraphObservation.node_id == node_id).scalars().all())

    def get_for_provider_object(
        self, provider_run_id: str, provider_object_id: str, observation_kind: str
    ) -> GraphObservation | None:
        return self.first(
            provider_run_id=provider_run_id,
            provider_object_id=provider_object_id,
            observation_kind=observation_kind,
        )

    def list_for_node_in_analysis(
        self, project_id: str, analysis_version_id: str, node_id: str, *, limit: int = 100
    ) -> list[GraphObservation]:
        return list(
            self.statement()
            .where(
                GraphObservation.project_id == project_id,
                GraphObservation.analysis_version_id == analysis_version_id,
                GraphObservation.node_id == node_id,
            )
            .limit(limit)
            .scalars()
            .all()
        )


class GraphCommunityRepository(BaseRepository[GraphCommunity, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(GraphCommunity, session, factory)


class GraphHyperedgeRepository(BaseRepository[GraphHyperedge, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(GraphHyperedge, session, factory)
