"""Pure authorization policy: project-role ranking + permission thresholds.

Kernel-grade shared foundation — depends only on enums. No ORM, no FastAPI, no session, so any package
(or the app's ORM adapter) can evaluate authorization without importing the composition root.
"""

from __future__ import annotations

from ruleatlas_contracts.enums import Permission, ProjectRole

__all__ = [
    "PERMISSION_MIN_ROLE",
    "ROLE_RANK",
    "permission_satisfied",
    "role_satisfies",
]

ROLE_RANK: dict[ProjectRole, int] = {
    ProjectRole.VIEWER: 1,
    ProjectRole.EDITOR: 2,
    ProjectRole.APPROVER: 3,
    ProjectRole.ADMIN: 4,
}

PERMISSION_MIN_ROLE: dict[Permission, ProjectRole] = {
    Permission.VIEW: ProjectRole.VIEWER,
    Permission.EXPORT: ProjectRole.VIEWER,
    Permission.EDIT: ProjectRole.EDITOR,
    Permission.SCAN: ProjectRole.EDITOR,
    Permission.APPROVE: ProjectRole.APPROVER,
    Permission.ADMIN: ProjectRole.ADMIN,
}


def role_satisfies(role: ProjectRole, minimum: ProjectRole) -> bool:
    """True when ``role`` ranks at or above ``minimum``."""
    return ROLE_RANK[role] >= ROLE_RANK[minimum]


def permission_satisfied(role: ProjectRole, permission: Permission) -> bool:
    """True when ``role`` meets the minimum role required for ``permission``."""
    return role_satisfies(role, PERMISSION_MIN_ROLE[permission])
