"""Typed persistence helpers used exclusively by deterministic demo seeding."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.orm.attributes import InstrumentedAttribute

from ruleatlas_persistence.models import (
    ClaimCluster,
    ClaimClusterMembership,
    GraphProviderRun,
    ImplementationGap,
    Rule,
    RuleConflict,
    RuleCoverageAssessment,
    SourceFile,
)

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory


class DemoQueryRepository:
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        self._session = session
        self._factory = factory

    def count_seed_clusters(self, project_id: str, canonical_keys: list[str]) -> int:
        if not canonical_keys:
            return 0
        return self._factory.claim_clusters().statement().where(
            ClaimCluster.project_id == project_id,
            ClaimCluster.canonical_key.in_(canonical_keys),
        ).count()

    def get_graph_provider_run(
        self, project_id: str, analysis_version_id: str, provider_key: str
    ) -> GraphProviderRun | None:
        return self._factory.graph_provider_runs().first(
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            provider_key=provider_key,
        )

    def get_cluster(
        self, analysis_version_id: str, canonical_key: str
    ) -> ClaimCluster | None:
        return self._factory.claim_clusters().first(
            analysis_version_id=analysis_version_id, canonical_key=canonical_key
        )

    def get_membership(
        self, claim_cluster_id: str, source_claim_id: str
    ) -> ClaimClusterMembership | None:
        return self._factory.claim_cluster_memberships().get_for_cluster_and_claim(
            claim_cluster_id, source_claim_id
        )

    def list_non_fixture_rules(
        self, project_id: str, analysis_version_id: str, stable_keys: list[str]
    ) -> list[Rule]:
        return list(
            self._factory.rules().statement().where(
                Rule.project_id == project_id,
                Rule.analysis_version_id == analysis_version_id,
                ~Rule.stable_key.in_(stable_keys),
            ).scalars().all()
        )

    def list_for_rule_ids(self, model: type[DeclarativeBase], rule_ids: list[str]) -> list[DeclarativeBase]:
        if not rule_ids:
            return []
        # Models passed here always expose a string ``rule_id`` column.
        rule_id_column = cast(InstrumentedAttribute[str], model.rule_id)  # type: ignore[attr-defined]
        return list(
            self._factory.repository(model)
            .statement()
            .where(rule_id_column.in_(rule_ids))
            .scalars()
            .all()
        )

    def get_conflict(
        self, project_id: str, analysis_version_id: str, area: str, conflict_kind: str
    ) -> RuleConflict | None:
        return self._factory.conflicts().first(
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            area=area,
            conflict_kind=conflict_kind,
        )

    def has_coverage_assessment(self, rule_id: str) -> bool:
        return self._factory.coverage_assessments().statement().where(
            RuleCoverageAssessment.rule_id == rule_id
        ).count() > 0

    def get_gap(
        self, project_id: str, analysis_version_id: str, title: str
    ) -> ImplementationGap | None:
        return self._factory.gaps().first(
            project_id=project_id, analysis_version_id=analysis_version_id, title=title
        )

    def list_source_files(self, project_id: str) -> list[SourceFile]:
        return self._factory.source_files().list_for_project(project_id)

    def snapshot_counts(
        self, project_id: str, analysis_version_id: str, stable_keys: list[str]
    ) -> dict[str, int]:
        return {
            "claims": self._factory.source_claims_structured().count_for_analysis(
                project_id, analysis_version_id
            ),
            "clusters": self._factory.claim_clusters().count_for_analysis(
                project_id, analysis_version_id
            ),
            "rules": len(self._factory.rules().list_by_stable_keys_for_project(project_id, stable_keys)),
            "traces": self._factory.ai_investigation_traces().count_for_analysis(
                project_id, analysis_version_id
            ),
            "conflicts": self._factory.conflicts().statement().where(
                RuleConflict.project_id == project_id,
                RuleConflict.analysis_version_id == analysis_version_id,
            ).count(),
            "gaps": self._factory.gaps().statement().where(
                ImplementationGap.project_id == project_id,
                ImplementationGap.analysis_version_id == analysis_version_id,
            ).count(),
        }
