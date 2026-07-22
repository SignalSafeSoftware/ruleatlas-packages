"""Database models for the core domain."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ruleatlas_contracts.enums import OrganizationRole, ProjectRole

from ._base import (
    FK_ORGANIZATIONS_ID,
    FK_PROJECTS_ID,
    FK_USERS_ID,
    JSON,
    STR_ENUM_COLUMN_KW,
    Base,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Mapped,
    String,
    Text,
    TimestampMixin,
    UniqueConstraint,
    datetime,
    mapped_column,
    now_utc,
    relationship,
    uuid_str,
)

if TYPE_CHECKING:
    from .rules import Rule
    from .scanning import AnalysisVersion, ClassificationOverride, ScanConfig, ScanRun, SourceLocation


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    # SSO/AI placeholders; managed via org settings API (Gate 2).
    settings_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    users: Mapped[list[User]] = relationship(back_populates="organization")
    projects: Mapped[list[Project]] = relationship(back_populates="organization")
    memberships: Mapped[list[OrganizationMembership]] = relationship(back_populates="organization")
    invites: Mapped[list[UserInvite]] = relationship(back_populates="organization")


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    organization_id: Mapped[str] = mapped_column(ForeignKey(FK_ORGANIZATIONS_ID), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    organization: Mapped[Organization] = relationship(back_populates="users")
    sessions: Mapped[list[UserSession]] = relationship(back_populates="user")
    api_tokens: Mapped[list[ApiToken]] = relationship(back_populates="user")
    organization_memberships: Mapped[list[OrganizationMembership]] = relationship(back_populates="user")
    password_reset_tokens: Mapped[list[PasswordResetToken]] = relationship(back_populates="user")
    project_memberships: Mapped[list[ProjectMembership]] = relationship(back_populates="user")
    external_identities: Mapped[list[ExternalIdentity]] = relationship(back_populates="user")
    sent_invites: Mapped[list[UserInvite]] = relationship(
        back_populates="invited_by",
        foreign_keys="UserInvite.invited_by_user_id",
    )
    notification_preferences: Mapped[UserNotificationPreferences | None] = relationship(
        back_populates="user",
        uselist=False,
    )


class UserNotificationPreferences(Base, TimestampMixin):
    __tablename__ = "user_notification_preferences"

    user_id: Mapped[str] = mapped_column(ForeignKey(FK_USERS_ID, ondelete="CASCADE"), primary_key=True)
    email_scan_completed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_review_queue: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_weekly_digest: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship(back_populates="notification_preferences")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(ForeignKey(FK_USERS_ID), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    ip_address: Mapped[str | None] = mapped_column(String(64))

    user: Mapped[User] = relationship(back_populates="sessions")


class ExternalIdentity(Base, TimestampMixin):
    """Links a RuleAtlas user to an external OAuth identity (e.g. GitHub login)."""

    __tablename__ = "external_identities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_external_identities_provider_subject"),
        UniqueConstraint("provider", "user_id", name="uq_external_identities_provider_user"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(ForeignKey(FK_USERS_ID, ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_login: Mapped[str | None] = mapped_column(String(200))
    provider_email: Mapped[str | None] = mapped_column(String(320))

    user: Mapped[User] = relationship(back_populates="external_identities")


class ApiToken(Base):
    __tablename__ = "api_tokens"
    __table_args__ = (UniqueConstraint("token_hash", name="uq_api_tokens_token_hash"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(ForeignKey(FK_USERS_ID), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    token_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    scopes: Mapped[str] = mapped_column(String(128), default="api", nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

    user: Mapped[User] = relationship(back_populates="api_tokens")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (UniqueConstraint("token_hash", name="uq_password_reset_tokens_token_hash"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(ForeignKey(FK_USERS_ID), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

    user: Mapped[User] = relationship(back_populates="password_reset_tokens")


class UserInvite(Base, TimestampMixin):
    __tablename__ = "user_invites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    organization_id: Mapped[str] = mapped_column(ForeignKey(FK_ORGANIZATIONS_ID), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    # RA-01-003: RBAC roles persisted as typed enums (native_enum=False -> VARCHAR + values_callable).
    role: Mapped[OrganizationRole] = mapped_column(Enum(OrganizationRole, **STR_ENUM_COLUMN_KW), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invited_by_user_id: Mapped[str] = mapped_column(ForeignKey(FK_USERS_ID), nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="invites")
    invited_by: Mapped[User] = relationship(
        back_populates="sent_invites",
        foreign_keys=[invited_by_user_id],
    )


class OrganizationMembership(Base, TimestampMixin):
    __tablename__ = "organization_memberships"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_org_membership"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    organization_id: Mapped[str] = mapped_column(ForeignKey(FK_ORGANIZATIONS_ID), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey(FK_USERS_ID), nullable=False)
    role: Mapped[OrganizationRole] = mapped_column(Enum(OrganizationRole, **STR_ENUM_COLUMN_KW), nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="organization_memberships")


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    organization_id: Mapped[str] = mapped_column(ForeignKey(FK_ORGANIZATIONS_ID), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    repository_url: Mapped[str | None] = mapped_column(Text)
    default_branch: Mapped[str | None] = mapped_column(String(200))
    settings_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # RA-01-006: typed FK pointer to the active analysis version (supersedes the settings_json entry).
    # use_alter avoids create/drop ordering issues from the projects<->analysis_versions FK cycle.
    active_analysis_version_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "analysis_versions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_projects_active_analysis_version",
        ),
        nullable=True,
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    organization: Mapped[Organization] = relationship(back_populates="projects")
    memberships: Mapped[list[ProjectMembership]] = relationship(back_populates="project")
    scan_configs: Mapped[list[ScanConfig]] = relationship(back_populates="project")
    source_locations: Mapped[list[SourceLocation]] = relationship(back_populates="project")
    scan_runs: Mapped[list[ScanRun]] = relationship(back_populates="project")
    rules: Mapped[list[Rule]] = relationship(back_populates="project")
    # foreign_keys disambiguates from the RA-01-006 projects.active_analysis_version_id FK.
    analysis_versions: Mapped[list[AnalysisVersion]] = relationship(
        back_populates="project", foreign_keys="AnalysisVersion.project_id"
    )
    classification_overrides: Mapped[list[ClassificationOverride]] = relationship(back_populates="project")


class ProjectMembership(Base, TimestampMixin):
    __tablename__ = "project_memberships"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_membership"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey(FK_PROJECTS_ID), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey(FK_USERS_ID), nullable=False, index=True)
    role: Mapped[ProjectRole] = mapped_column(Enum(ProjectRole, **STR_ENUM_COLUMN_KW), nullable=False)

    project: Mapped[Project] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="project_memberships")
