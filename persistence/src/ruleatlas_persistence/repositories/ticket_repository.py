"""Repositories for ticket sync and webhook delivery persistence."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import (
    ExternalTicket,
    TicketConnection,
    TicketRevision,
    TicketSyncCursor,
    TicketWebhookDelivery,
)

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory


class TicketWebhookDeliveryRepository(BaseRepository[TicketWebhookDelivery, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(TicketWebhookDelivery, session, factory)

    def list_retryable_for_connection(
        self, connection_id: str, *, statuses: list[str], limit: int = 50
    ) -> list[TicketWebhookDelivery]:
        return list(
            self.statement()
            .where(
                TicketWebhookDelivery.connection_id == connection_id,
                TicketWebhookDelivery.status.in_(statuses),
            )
            .limit(limit)
            .scalars()
            .all()
        )

    def count_for_connection_and_status(self, connection_id: str, status: str) -> int:
        return (
            self.statement()
            .where(
                TicketWebhookDelivery.connection_id == connection_id,
                TicketWebhookDelivery.status == status,
            )
            .count()
        )


class TicketConnectionRepository(BaseRepository[TicketConnection, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(TicketConnection, session, factory)

    def get_for_organization(
        self, connection_id: str, organization_id: str, *, provider_key: str | None = None
    ) -> TicketConnection | None:
        stmt = self.statement().where(
            TicketConnection.id == connection_id,
            TicketConnection.organization_id == organization_id,
        )
        if provider_key:
            stmt = stmt.where(TicketConnection.provider_key == provider_key)
        return stmt.scalars().first()

    def list_for_project(
        self, project_id: str, *, provider_key: str | None = None
    ) -> list[TicketConnection]:
        stmt = self.statement().where(TicketConnection.project_id == project_id)
        if provider_key:
            stmt = stmt.where(TicketConnection.provider_key == provider_key)
        return list(stmt.scalars().all())

    def get_first_for_organization(
        self, organization_id: str, *, provider_key: str
    ) -> TicketConnection | None:
        return (
            self.statement()
            .where(
                TicketConnection.organization_id == organization_id,
                TicketConnection.provider_key == provider_key,
            )
            .scalars()
            .first()
        )

    def get_by_organization_provider_and_name(
        self, organization_id: str, provider_key: str, name: str
    ) -> TicketConnection | None:
        return (
            self.statement()
            .where(
                TicketConnection.organization_id == organization_id,
                TicketConnection.provider_key == provider_key,
                TicketConnection.name == name,
            )
            .scalars()
            .first()
        )

    def list_for_organization_and_provider(
        self, organization_id: str, provider_key: str
    ) -> list[TicketConnection]:
        return list(
            self.statement()
            .where(
                TicketConnection.organization_id == organization_id,
                TicketConnection.provider_key == provider_key,
            )
            .scalars()
            .all()
        )


class TicketRevisionRepository(BaseRepository[TicketRevision, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(TicketRevision, session, factory)

    def count_for_connection(self, connection_id: str) -> int:
        return (
            self.statement()
            .join(ExternalTicket, ExternalTicket.id == TicketRevision.external_ticket_id)
            .where(ExternalTicket.connection_id == connection_id)
            .count()
        )

    def get_for_ticket_and_hash(self, external_ticket_id: str, revision_hash: str) -> TicketRevision | None:
        return self.first(external_ticket_id=external_ticket_id, revision_hash=revision_hash)


class ExternalTicketRepository(BaseRepository[ExternalTicket, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(ExternalTicket, session, factory)

    def get_for_connection_and_external_id(
        self, connection_id: str, external_id: str
    ) -> ExternalTicket | None:
        return self.first(connection_id=connection_id, external_id=external_id)

    def list_active_for_connection(self, connection_id: str) -> list[ExternalTicket]:
        return list(
            self.statement()
            .where(
                ExternalTicket.connection_id == connection_id,
                ExternalTicket.is_deleted.is_(False),
            )
            .scalars()
            .all()
        )

    def list_active_for_project(
        self,
        project_id: str,
        *,
        connection_id: str | None = None,
        provider_key: str | None = None,
    ) -> list[ExternalTicket]:
        stmt = self.statement().where(
            ExternalTicket.project_id == project_id,
            ExternalTicket.is_deleted.is_(False),
        )
        if connection_id:
            stmt = stmt.where(ExternalTicket.connection_id == connection_id)
        if provider_key:
            stmt = stmt.where(ExternalTicket.provider_key == provider_key)
        return list(stmt.scalars().all())

    def count_active_for_connection(self, connection_id: str) -> int:
        return (
            self.statement()
            .where(
                ExternalTicket.connection_id == connection_id,
                ExternalTicket.is_deleted.is_(False),
            )
            .count()
        )


class TicketSyncCursorRepository(BaseRepository[TicketSyncCursor, "RepositoryFactory"]):
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        super().__init__(TicketSyncCursor, session, factory)

    def get_for_connection(self, connection_id: str) -> TicketSyncCursor | None:
        return self.first(connection_id=connection_id)
