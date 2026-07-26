"""Bootstrap connection lookup helpers on AiProviderConnectionRepository."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import ruleatlas_persistence.models as _models  # noqa: F401
from ruleatlas_persistence.base import Base
from ruleatlas_persistence.models import AiProviderConnection
from ruleatlas_persistence.repositories.ai_provider_repository import (
    OPENAI_ENVIRONMENT_BOOTSTRAP_NAME,
    OPENAI_ENVIRONMENT_BOOTSTRAP_VAR,
    AiProviderConnectionRepository,
)
from ruleatlas_persistence.repositories.factory import RepositoryFactory


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_get_environment_openai_bootstrap_matches_canonical_name_without_env_var() -> None:
    session = _session()
    factory = RepositoryFactory(session)
    repo = factory.get_repository(AiProviderConnectionRepository)

    session.add(
        AiProviderConnection(
            id="conn-1",
            organization_id="org-1",
            name=OPENAI_ENVIRONMENT_BOOTSTRAP_NAME,
            provider_type="openai",
            credential_source="ssm_secure_string",
            environment_variable_name=None,
            enabled=False,
            status="untested",
            created_by="tester",
            updated_by="tester",
            attributes_json={"bootstrap": True},
        )
    )
    session.commit()

    found = repo.get_environment_openai_bootstrap("org-1")
    assert found is not None
    assert found.id == "conn-1"
    assert found.environment_variable_name is None
    session.close()


def test_get_environment_openai_bootstrap_matches_env_var_binding() -> None:
    session = _session()
    factory = RepositoryFactory(session)
    repo = factory.get_repository(AiProviderConnectionRepository)

    session.add(
        AiProviderConnection(
            id="conn-2",
            organization_id="org-1",
            name="Custom OpenAI",
            provider_type="openai",
            credential_source="environment_variable",
            environment_variable_name=OPENAI_ENVIRONMENT_BOOTSTRAP_VAR,
            enabled=True,
            status="untested",
            created_by="tester",
            updated_by="tester",
            attributes_json={},
        )
    )
    session.commit()

    found = repo.get_environment_openai_bootstrap("org-1")
    assert found is not None
    assert found.id == "conn-2"
    session.close()
