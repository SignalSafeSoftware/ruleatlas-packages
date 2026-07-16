"""Repositories for BDD feature/scenario/step persistence."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import BddFeature, BddScenario, BddStep, BddStepLink

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory


class BddFeatureRepository(BaseRepository[BddFeature, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(BddFeature, session, factory)

    def list_for_analysis(self, project_id: str, analysis_version_id: str) -> list[BddFeature]:
        return list(
            self.statement()
            .where(
                BddFeature.project_id == project_id,
                BddFeature.analysis_version_id == analysis_version_id,
            )
            .scalars()
            .all()
        )

    def count_for_analysis(self, project_id: str, analysis_version_id: str) -> int:
        return (
            self.statement()
            .where(
                BddFeature.project_id == project_id,
                BddFeature.analysis_version_id == analysis_version_id,
            )
            .count()
        )

    def get_by_analysis_and_canonical_key(
        self, analysis_version_id: str, canonical_key: str
    ) -> BddFeature | None:
        return self.first(
            analysis_version_id=analysis_version_id,
            canonical_key=canonical_key,
        )

    def list_parseable_for_analysis(
        self, project_id: str, analysis_version_id: str
    ) -> list[BddFeature]:
        return list(
            self.statement()
            .where(
                BddFeature.project_id == project_id,
                BddFeature.analysis_version_id == analysis_version_id,
                BddFeature.parse_error.is_(None),
            )
            .scalars()
            .all()
        )


class BddScenarioRepository(BaseRepository[BddScenario, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(BddScenario, session, factory)

    def count_for_analysis(self, project_id: str, analysis_version_id: str) -> int:
        return (
            self.statement()
            .where(
                BddScenario.project_id == project_id,
                BddScenario.analysis_version_id == analysis_version_id,
            )
            .count()
        )

    def list_for_feature(self, bdd_feature_id: str) -> list[BddScenario]:
        return list(
            self.statement()
            .where(BddScenario.bdd_feature_id == bdd_feature_id)
            .scalars()
            .all()
        )


class BddStepLinkRepository(BaseRepository[BddStepLink, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(BddStepLink, session, factory)

    def list_for_step(self, bdd_step_id: str) -> list[BddStepLink]:
        return list(self.statement().where(BddStepLink.bdd_step_id == bdd_step_id).scalars().all())

    def list_for_steps(self, bdd_step_ids: list[str]) -> list[BddStepLink]:
        if not bdd_step_ids:
            return []
        return list(
            self.statement()
            .where(BddStepLink.bdd_step_id.in_(bdd_step_ids))
            .scalars()
            .all()
        )


class BddStepRepository(BaseRepository[BddStep, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(BddStep, session, factory)

    def list_for_scenario_ordered(self, bdd_scenario_id: str) -> list[BddStep]:
        return list(
            self.statement()
            .where(BddStep.bdd_scenario_id == bdd_scenario_id)
            .order_by(BddStep.step_order.asc())
            .scalars()
            .all()
        )

    def list_for_analysis(
        self,
        project_id: str,
        analysis_version_id: str,
        *,
        link_status: str | None = None,
        limit: int = 500,
    ) -> list[BddStep]:
        stmt = self.statement().where(
            BddStep.project_id == project_id,
            BddStep.analysis_version_id == analysis_version_id,
        )
        if link_status:
            stmt = stmt.where(BddStep.link_status == link_status)
        return list(stmt.order_by(BddStep.start_line.asc()).limit(limit).scalars().all())

    def list_all_for_analysis(self, project_id: str, analysis_version_id: str) -> list[BddStep]:
        return list(
            self.statement()
            .where(
                BddStep.project_id == project_id,
                BddStep.analysis_version_id == analysis_version_id,
            )
            .scalars()
            .all()
        )
