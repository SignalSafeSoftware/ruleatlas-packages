"""RepositoryFactory protocol alignment with sqlphilosophy >= 0.2.0."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlphilosophy.sync.repository import BaseRepository

from ruleatlas_persistence.models import Project
from ruleatlas_persistence.repositories.factory import RepositoryFactory
from ruleatlas_persistence.repositories.project_repository import ProjectRepository


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_repository_returns_base_repository_with_factory_bound() -> None:
    session = _session()
    factory = RepositoryFactory(session)

    repo = factory.repository(Project)

    assert isinstance(repo, BaseRepository)
    assert repo.model is Project
    assert repo.has_factory is True
    assert repo.maybe_factory is factory
    assert repo.factory is factory
    session.close()


def test_repository_caches_same_instance_per_model() -> None:
    session = _session()
    factory = RepositoryFactory(session)

    first = factory.repository(Project)
    second = factory.repository(Project)

    assert first is second
    session.close()


def test_get_repository_returns_typed_project_repository() -> None:
    session = _session()
    factory = RepositoryFactory(session)

    typed = factory.get_repository(ProjectRepository)
    again = factory.projects()

    assert isinstance(typed, ProjectRepository)
    assert typed is again
    assert typed.has_factory is True
    assert typed.factory is factory
    session.close()


def test_create_statement_uses_session() -> None:
    session = _session()
    factory = RepositoryFactory(session)

    builder = factory.create_statement(Project)

    assert builder is not None
    session.close()
