"""Repositories for AI provider connections and model catalog."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy import delete, or_
from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    AiModelCatalogEntry,
    AiModelCompatibilityTest,
    AiProviderConnection,
    ProjectAiConfiguration,
)


class AiProviderConnectionRepository(BaseRepository[AiProviderConnection, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(AiProviderConnection, session, factory)

    def list_for_organization(self, organization_id: str) -> list[AiProviderConnection]:
        return list(
            self.statement()
            .where(AiProviderConnection.organization_id == organization_id)
            .order_by(AiProviderConnection.name.asc())
            .scalars()
            .all()
        )

    def list_enabled_for_organization(self, organization_id: str) -> list[AiProviderConnection]:
        return list(
            self.statement()
            .where(
                AiProviderConnection.organization_id == organization_id,
                AiProviderConnection.enabled.is_(True),
            )
            .scalars()
            .all()
        )

    def get_for_organization(
        self, organization_id: str, connection_id: str
    ) -> AiProviderConnection | None:
        return (
            self.statement()
            .where(
                AiProviderConnection.organization_id == organization_id,
                AiProviderConnection.id == connection_id,
            )
            .scalars()
            .first()
        )

    def get_by_org_and_name(self, organization_id: str, name: str) -> AiProviderConnection | None:
        return self.first(organization_id=organization_id, name=name)

    def get_environment_openai_bootstrap(self, organization_id: str) -> AiProviderConnection | None:
        """Earliest OpenAI connection bound to OPENAI_API_KEY for an organization."""
        return (
            self.statement()
            .where(
                AiProviderConnection.organization_id == organization_id,
                AiProviderConnection.provider_type == "openai",
                AiProviderConnection.environment_variable_name == "OPENAI_API_KEY",
            )
            .order_by(AiProviderConnection.created_at.asc())
            .scalars()
            .first()
        )

    def list_all_ordered_by_org(self) -> list[AiProviderConnection]:
        return list(
            self.statement()
            .order_by(AiProviderConnection.organization_id, AiProviderConnection.created_at)
            .scalars()
            .all()
        )


class AiModelCatalogEntryRepository(BaseRepository[AiModelCatalogEntry, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(AiModelCatalogEntry, session, factory)

    def list_for_connection(self, connection_id: str) -> list[AiModelCatalogEntry]:
        return list(
            self.statement()
            .where(AiModelCatalogEntry.connection_id == connection_id)
            .order_by(AiModelCatalogEntry.display_name.asc())
            .scalars()
            .all()
        )

    def list_for_organization(self, organization_id: str) -> list[AiModelCatalogEntry]:
        return list(
            self.statement()
            .where(AiModelCatalogEntry.organization_id == organization_id)
            .order_by(AiModelCatalogEntry.display_name.asc())
            .scalars()
            .all()
        )

    def get_for_organization(
        self, organization_id: str, catalog_entry_id: str
    ) -> AiModelCatalogEntry | None:
        return (
            self.statement()
            .where(
                AiModelCatalogEntry.organization_id == organization_id,
                AiModelCatalogEntry.id == catalog_entry_id,
            )
            .scalars()
            .first()
        )

    def get_by_connection_and_model(
        self, connection_id: str, provider_model_id: str
    ) -> AiModelCatalogEntry | None:
        return self.first(connection_id=connection_id, provider_model_id=provider_model_id)

    def list_ids_for_connection(self, connection_id: str) -> list[str]:
        return cast(
            list[str],
            self.statement()
            .select_columns(AiModelCatalogEntry.id)
            .where(AiModelCatalogEntry.connection_id == connection_id)
            .scalars()
            .all(),
        )

    def delete_for_connection(self, connection_id: str) -> None:
        self._session.execute(
            delete(AiModelCatalogEntry).where(AiModelCatalogEntry.connection_id == connection_id)
        )

    def count_enabled_compatible_for_organization(
        self,
        organization_id: str,
        *,
        availability_status: str,
    ) -> int:
        return (
            self.statement()
            .where(
                AiModelCatalogEntry.organization_id == organization_id,
                AiModelCatalogEntry.enabled_for_selection.is_(True),
                AiModelCatalogEntry.availability_status == availability_status,
                AiModelCatalogEntry.ruleatlas_compatible.is_(True),
            )
            .count()
        )

    def get_latest_compatible_for_connection(
        self,
        connection_id: str,
        *,
        availability_status: str,
        compatibility_status: str,
    ) -> AiModelCatalogEntry | None:
        return (
            self.statement()
            .where(
                AiModelCatalogEntry.connection_id == connection_id,
                AiModelCatalogEntry.enabled_for_selection.is_(True),
                AiModelCatalogEntry.ruleatlas_compatible.is_(True),
                AiModelCatalogEntry.availability_status == availability_status,
                AiModelCatalogEntry.compatibility_status == compatibility_status,
            )
            .order_by(AiModelCatalogEntry.updated_at.desc())
            .limit(1)
            .scalars()
            .first()
        )


class AiModelCompatibilityTestRepository(
    BaseRepository[AiModelCompatibilityTest, "RepositoryFactory"]
):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(AiModelCompatibilityTest, session, factory)

    def list_for_catalog_entry(self, catalog_entry_id: str, *, limit: int = 20) -> list[AiModelCompatibilityTest]:
        return list(
            self.statement()
            .where(AiModelCompatibilityTest.catalog_entry_id == catalog_entry_id)
            .order_by(AiModelCompatibilityTest.tested_at.desc())
            .limit(limit)
            .scalars()
            .all()
        )

    def delete_for_connection_or_catalog_entries(
        self, connection_id: str, catalog_entry_ids: list[str]
    ) -> None:
        predicate = AiModelCompatibilityTest.connection_id == connection_id
        if catalog_entry_ids:
            predicate = or_(
                predicate,
                AiModelCompatibilityTest.catalog_entry_id.in_(catalog_entry_ids),
            )
        self._session.execute(delete(AiModelCompatibilityTest).where(predicate))


class ProjectAiConfigurationRepository(BaseRepository[ProjectAiConfiguration, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(ProjectAiConfiguration, session, factory)

    def get_for_project(self, project_id: str) -> ProjectAiConfiguration | None:
        return self.first(project_id=project_id)

    def delete_for_project(self, project_id: str) -> None:
        self._session.execute(delete(ProjectAiConfiguration).where(ProjectAiConfiguration.project_id == project_id))

    def list_using_connection(self, connection_id: str) -> list[ProjectAiConfiguration]:
        return list(
            self.statement()
            .where(
                (ProjectAiConfiguration.connection_id == connection_id)
                | (ProjectAiConfiguration.fallback_connection_id == connection_id)
            )
            .scalars()
            .all()
        )

    def list_using_model(self, catalog_entry_id: str) -> list[ProjectAiConfiguration]:
        return self.list_using_models([catalog_entry_id])

    def list_using_models(self, catalog_entry_ids: list[str]) -> list[ProjectAiConfiguration]:
        if not catalog_entry_ids:
            return []
        return list(
            self.statement()
            .where(
                (ProjectAiConfiguration.synthesis_model_id.in_(catalog_entry_ids))
                | (ProjectAiConfiguration.embedding_model_id.in_(catalog_entry_ids))
                | (ProjectAiConfiguration.fallback_model_id.in_(catalog_entry_ids))
            )
            .scalars()
            .all()
        )
