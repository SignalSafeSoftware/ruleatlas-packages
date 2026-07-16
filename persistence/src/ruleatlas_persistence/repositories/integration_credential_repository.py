"""Additional domain repositories for full sqlPhilosophy query-boundary coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    IntegrationCredential,
)


class IntegrationCredentialRepository(BaseRepository[IntegrationCredential, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(IntegrationCredential, session, factory)

    def get_for_organization(self, organization_id: str, credential_id: str) -> Any:
        return (
            self.statement()
            .where(
                IntegrationCredential.organization_id == organization_id,
                IntegrationCredential.id == credential_id,
            )
            .scalars()
            .first()
        )

    def get_for_organization_and_type(
        self,
        organization_id: str,
        credential_id: str,
        integration_type: str,
    ) -> IntegrationCredential | None:
        return (
            self.statement()
            .where(
                IntegrationCredential.organization_id == organization_id,
                IntegrationCredential.id == credential_id,
                IntegrationCredential.integration_type == integration_type,
            )
            .scalars()
            .first()
        )

    def list_for_organization(self, organization_id: str) -> list[IntegrationCredential]:
        return list(
            self.statement()
            .where(IntegrationCredential.organization_id == organization_id)
            .order_by(IntegrationCredential.integration_type, IntegrationCredential.name)
            .scalars()
            .all()
        )

    def get_by_org_type_and_name(
        self,
        organization_id: str,
        integration_type: str,
        name: str,
    ) -> IntegrationCredential | None:
        return self.first(
            organization_id=organization_id,
            integration_type=integration_type,
            name=name,
        )
