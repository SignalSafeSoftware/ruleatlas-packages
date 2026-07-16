"""Assign primary rule_category and optional workflow_group (P1-B / P1-G).

Categories describe the *kind* of finding. They never approve rules.
Source roles (backend_code, unit_test, …) remain separate evidence metadata.
"""

from __future__ import annotations

import re

from ruleatlas_contracts.classification.scaffold_filter import is_scaffold_evidence_text
from ruleatlas_contracts.classification.rule_display import is_non_rule_claim
from ruleatlas_contracts.enums import RuleCategory

# Prefer unknown over a wrong business/security label for identifier-like claims.
_PLUMBING_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bMSG_[A-Z0-9_]+\b"),
    re.compile(r"^[A-Z][A-Z0-9_]*(?:_DETAIL|_MESSAGE|_ERROR|_MSG)\s*="),
    re.compile(r"\b\w+Dep\b"),
    re.compile(r"\bTrusted\w+\b"),
    re.compile(r"\bAPIRouter\b"),
    re.compile(r"@router\."),
    re.compile(r"\bas\s+\w+Queries\b", re.I),
    re.compile(r"^\s*class\s+\w+\s*\("),
    re.compile(r'^\s*[A-Z_][A-Z0-9_]*\s*=\s*["\']'),
)
_SIMPLE_ANNOTATION_TYPES = frozenset(("int", "str", "bool", "float", "uuid"))

_PRODUCT_BEHAVIOR = re.compile(
    r"\b(?:must not|must|cannot|can't|should|allow|deny|list|create|update|delete|purge|"
    r"approve|reject|expire|retain|assign|enroll|send|require|prevent|block)\b",
    re.I,
)

# Strong multi-word / phrase rules, evaluated in order (first match wins).
_STRONG_CATEGORY_PHRASES: list[tuple[RuleCategory, tuple[str, ...]]] = [
    (
        RuleCategory.TEST_COVERAGE,
        ("test execution", "execution evidence", "coverage is", "coverage evidence"),
    ),
    (
        RuleCategory.RUNTIME_OBSERVATION,
        ("observed behavior", "runtime log", "runtime evidence"),
    ),
    (
        RuleCategory.AI_GOVERNANCE,
        ("candidate-only", "auto-approve", "human review is required", "ai candidate"),
    ),
    (
        RuleCategory.DEVELOPMENT_POLICY,
        (
            "code change without docs",
            "documentation practice",
            "docs are incomplete",
            "must not depend on",
            "checklist",
        ),
    ),
    (
        RuleCategory.ARCHITECTURE,
        (
            "must import",
            "must not import",
            "import boundaries",
            "thin routes",
            "sqlphilosophy",
            "stay free of",
        ),
    ),
    (
        RuleCategory.CONFIGURATION,
        (
            "postgresql only",
            "postgresql is the only",
            "environment variable",
            "must be configured",
            "runtime database",
        ),
    ),
    (
        RuleCategory.WORKFLOW_LIFECYCLE,
        (
            "retention",
            "purge",
            "expire",
            "expires after",
            "expired data",
            "lifecycle",
            "status must",
            "full scan must",
        ),
    ),
    (
        RuleCategory.VALIDATION,
        (
            "must not be empty",
            "cannot be empty",
            "is required",
            "validation",
            "invalid treespec",
            "reject invalid",
        ),
    ),
]

_AUTHZ_BEHAVIOR = (
    "permission",
    "authorize",
    "authorization",
    "deny",
    "denied",
    "forbidden",
    "unauthenticated",
    "403",
    "401",
    "cannot delete",
    "can delete",
    "must not delete",
    "prevents users from deleting",
    "list/retrieve",
    "404 vs 403",
    "staff denied",
)
_AUTHZ_ACTOR = ("admin", "manager", "staff", "owner", "role")
_AUTHZ_MODAL = ("allow", "deny", "can ", "cannot", "must not", "must ", "permission", "access")

_BUSINESS_STRONG = (
    "refund",
    "assignment",
    "assignments",
    "enroll",
    "enrollment",
    "campaign",
    "signup",
    "sign-up",
    "verification email",
    "temporary password",
    "password policy",
    "create account",
    "pending account",
    "list lessons",
    "list scenarios",
    "list companies",
    "list users",
    "content library",
)


def _is_plumbing_claim(text: str) -> bool:
    if is_non_rule_claim(text) or is_scaffold_evidence_text(text):
        return True
    stripped = text.strip()
    if _is_simple_type_annotation(stripped) or any(
        pattern.search(stripped) for pattern in _PLUMBING_PATTERNS
    ):
        return True
    # Identifier-like fragments without product behavior verbs.
    return bool(
        not _PRODUCT_BEHAVIOR.search(stripped)
        and (
            re.search("[{}=<>]|^\\s*(return|raise|import|from)\\b", stripped)
            or re.search("\\b(Queries|Repository|Response|Request|Dep)\\b", stripped)
        )
    )


def _is_simple_type_annotation(text: str) -> bool:
    """Recognize simple field annotations without a backtracking regex."""
    annotation = text.strip()
    if annotation.endswith(","):
        annotation = annotation[:-1].rstrip()
    name, separator, type_name = annotation.partition(":")
    return bool(
        separator
        and ":" not in type_name
        and name.strip()
        and all(character == "_" or character.isalnum() for character in name.strip())
        and type_name.strip().lower() in _SIMPLE_ANNOTATION_TYPES
    )


def _has_authz_behavior(lowered: str) -> bool:
    if any(marker in lowered for marker in _AUTHZ_BEHAVIOR):
        return True
    return bool(any(actor in lowered for actor in _AUTHZ_ACTOR) and any(modal in lowered for modal in _AUTHZ_MODAL))


def _has_business_behavior(lowered: str) -> bool:
    return any(marker in lowered for marker in _BUSINESS_STRONG)


def classify_rule_category(text: str | None) -> RuleCategory:
    """Return a single primary category. Prefer unknown over a wrong label."""
    if not text or not text.strip():
        return RuleCategory.UNKNOWN
    if _is_plumbing_claim(text):
        return RuleCategory.UNKNOWN

    lowered = text.lower()

    for category, phrases in _STRONG_CATEGORY_PHRASES:
        if any(phrase in lowered for phrase in phrases):
            return category

    # Product money/commerce before role-noun authz (managers approve refunds).
    if "refund" in lowered or "approve refunds" in lowered:
        return RuleCategory.BUSINESS

    if _has_authz_behavior(lowered):
        return RuleCategory.SECURITY_AUTHORIZATION

    if _has_business_behavior(lowered):
        return RuleCategory.BUSINESS

    return RuleCategory.UNKNOWN


def classify_workflow_group(text: str | None) -> str | None:
    """Optional soft grouping label. Prefer None over a wrong label."""
    if not text or not text.strip():
        return None
    if _is_plumbing_claim(text):
        return None

    lowered = text.lower()

    # Product workflows before authorization.
    if any(m in lowered for m in ("assignment", "assignments", "assign users")):
        return "assignment"
    if any(m in lowered for m in ("retention", "purge", "expire", "expires after", "expired data")):
        return "retention"
    if any(m in lowered for m in ("signup", "sign-up", "register", "create account", "verification email")):
        return "signup"
    if any(m in lowered for m in ("list lessons", "list scenarios", "content library")):
        return "content"
    if any(m in lowered for m in ("list companies", "list users", "list attempts", "staff can list")):
        return "administration"
    if "refund" in lowered:
        return "refunds"

    # Authorization only with real authz behavior (not bare admin/staff/role).
    if _has_authz_behavior(lowered):
        return "authorization"

    if any(m in lowered for m in ("full scan", "extraction", "inventorying", "scan must")):
        return "scan_lifecycle"

    return None


__all__ = [
    "classify_rule_category",
    "classify_workflow_group",
]
