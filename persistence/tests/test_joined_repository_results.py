"""Exercise real ORM result shapes through repository mapping terminals."""

from collections.abc import Iterator

import pytest
from ruleatlas_contracts.enums import ProjectRole
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ruleatlas_persistence.base import Base
from ruleatlas_persistence.models import (
    Organization,
    Project,
    ProjectMembership,
    Rule,
    RuleCoverageAssessment,
    User,
)
from ruleatlas_persistence.repositories.factory import RepositoryFactory
from ruleatlas_persistence.repositories.permission_repository import PermissionRepository
from ruleatlas_persistence.repositories.rule_coverage_assessment_repository import (
    RuleCoverageAssessmentRepository,
)


@pytest.fixture
def repository_session() -> Iterator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Organization(id="org", name="Demo", slug="demo"))
        session.flush()
        session.add_all(
            [
                Project(id="project", organization_id="org", name="Project", slug="project"),
                Project(id="other", organization_id="org", name="Other", slug="other"),
            ]
        )
        session.flush()
        yield session
    engine.dispose()


def test_joined_assessments_preserve_models_and_project_filters(repository_session: Session) -> None:
    session = repository_session
    first = Rule(id="first", project_id="project", stable_key="first", name="Alpha")
    second = Rule(id="second", project_id="other", stable_key="second", name="Other")
    session.add_all([first, second])
    session.flush()
    assessment = RuleCoverageAssessment(rule_id=first.id, assessment_summary="Covered")
    session.add_all([assessment, RuleCoverageAssessment(rule_id=second.id, assessment_summary="Other")])
    session.flush()
    repository = RuleCoverageAssessmentRepository(session, RepositoryFactory(session))

    assert repository.list_with_rules_for_project("project") == [(assessment, first)]
    assert repository.list_for_project_joined_rules("project") == [(assessment, first)]
    assert repository.list_with_rules_for_project("project", rule_id="second") == []
    assert repository.list_for_project_joined_rules("missing") == []


def test_joined_members_preserve_user_role_order_and_project_filter(repository_session: Session) -> None:
    session = repository_session
    first = User(id="first", organization_id="org", email="first@example.test", display_name="Alpha")
    second = User(id="second", organization_id="org", email="second@example.test", display_name="Zulu")
    session.add_all([second, first])
    session.flush()
    session.add_all(
        [
            ProjectMembership(project_id="project", user_id=second.id, role=ProjectRole.VIEWER),
            ProjectMembership(project_id="project", user_id=first.id, role=ProjectRole.ADMIN),
            ProjectMembership(project_id="other", user_id=first.id, role=ProjectRole.VIEWER),
        ]
    )
    session.flush()
    repository = PermissionRepository(session, RepositoryFactory(session))

    assert repository.list_members_with_user("project") == [
        (first, ProjectRole.ADMIN),
        (second, ProjectRole.VIEWER),
    ]
    assert repository.list_members_with_user("missing") == []
