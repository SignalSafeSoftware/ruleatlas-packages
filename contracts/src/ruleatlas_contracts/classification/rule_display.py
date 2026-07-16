from __future__ import annotations

import re

from ruleatlas_contracts.classification.scaffold_filter import is_scaffold_evidence_text

_WHITESPACE = re.compile(r"\s+")
MAX_DISPLAY_TITLE_LEN = 120


def build_rule_display_title(
    *,
    name: str,
    business_rule: str | None = None,
    claim_text: str | None = None,
) -> str:
    """Deterministic claim-first label for UI/exports. Never invents wording."""
    for candidate in (business_rule, claim_text):
        title = _normalize_title(candidate)
        if title and not is_scaffold_evidence_text(title):
            return title
    for candidate in (business_rule, claim_text):
        title = _normalize_title(candidate)
        if title:
            return title
    return _normalize_title(name) or "Untitled rule"


def _normalize_title(text: str | None) -> str:
    if not text:
        return ""
    collapsed = _WHITESPACE.sub(" ", text.strip())
    if not collapsed:
        return ""
    if len(collapsed) <= MAX_DISPLAY_TITLE_LEN:
        return collapsed
    truncated = collapsed[: MAX_DISPLAY_TITLE_LEN - 1].rstrip(" ,;:-")
    return f"{truncated}…"


def is_signature_like_claim(text: str | None) -> bool:
    """True when claim text is non-rule signature/plumbing/scaffold."""
    return is_non_rule_claim(text)


def is_non_rule_claim(text: str | None) -> bool:
    """True when claim text is non-rule scaffold (signatures, JSX, hooks, health smoke, etc.)."""
    if not text or not text.strip():
        return False
    return is_scaffold_evidence_text(text)


__all__ = [
    "MAX_DISPLAY_TITLE_LEN",
    "build_rule_display_title",
    "is_non_rule_claim",
    "is_signature_like_claim",
]
