"""Extract structured semantics from claims/clusters for identity-based merge."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from ruleatlas_persistence.models import SourceClaim

_THRESHOLD_RE = re.compile(
    r"(?:\$\s*)?(\d[\d,]*(?:\.\d+)?)\s*(?:usd|dollars?)?|(?:threshold\s*(?:of|=|:)?\s*)(\d[\d,]*)",
    re.IGNORECASE,
)
_DAYS_RE = re.compile(r"(\d+)\s*-?\s*days?", re.IGNORECASE)
_OUTDATED_MARKERS = (
    "outdated",
    "legacy",
    "do not treat as product intent",
    "never treat",
    "superseded",
    "deprecated",
)
_IMPL_DETAIL_MARKERS = (
    "deploy",
    "ops/",
    "feature flag",
    "enablement",
    "infrastructure",
    "logging only",
)
_EXCEPTION_MARKERS = (
    "except",
    "exception",
    "admin",
    "correction workflow",
    "override",
)


@dataclass(frozen=True)
class StructuredSemantics:
    actor: str | None = None
    action: str | None = None
    action_family: str | None = None
    object: str | None = None
    condition: str | None = None
    threshold: str | None = None
    state: str | None = None
    exception: str | None = None
    outcome: str | None = None
    timing: str | None = None
    authority_status: str | None = None  # current | superseded | unknown

    def identity_key(self) -> tuple[str, str, str, str, str]:
        return (
            (self.action_family or self.action or "").strip().lower(),
            _actor_class(self.actor),
            (self.threshold or "").strip().lower(),
            (self.state or "").strip().lower(),
            (self.timing or "").strip().lower(),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _actor_class(actor: str | None) -> str:
    text = (actor or "").strip().lower()
    if not text:
        return ""
    if "admin" in text:
        return "admin"
    if any(t in text for t in ("manager", "approver")):
        return "manager"
    if any(t in text for t in ("clerk", "user", "employee")):
        return "user"
    return text


def _action_family(action: str | None, claim_text: str | None = None, subject: str | None = None) -> str:
    blob = f"{action or ''} {claim_text or ''} {subject or ''}".lower()
    if any(t in blob for t in ("delet", "remove")):
        return "delete"
    # Prefer expire over approve — "pending approval expire" must not become approve
    if any(t in blob for t in ("expir", "expiry", "expire after", "retention window")):
        return "expire"
    if any(t in blob for t in ("threshold", "require approval", "must approve", "approval required")):
        return "approve"
    if "approv" in blob and "expir" not in blob:
        return "approve"
    if any(t in blob for t in ("creat", "submit")):
        return "create"
    tokens = re.findall(r"[a-z_]{3,}", (action or "").lower())
    return tokens[0] if tokens else ""


def _extract_threshold(*texts: str | None) -> str | None:
    """Prefer money/threshold amounts; avoid capturing day counts as thresholds."""
    for text in texts:
        if not text:
            continue
        # Skip pure day-duration phrases
        if _DAYS_RE.search(text) and "threshold" not in text.lower() and "$" not in text and "usd" not in text.lower():
            # Still allow explicit threshold language alongside days
            if not re.search(r"threshold|\$|usd|dollar", text, re.I):
                continue
        match = _THRESHOLD_RE.search(text)
        if match:
            raw = match.group(1) or match.group(2)
            if raw:
                # Ignore small integers that are day counts already captured as timing
                days = _DAYS_RE.search(text)
                if days and raw == days.group(1) and "threshold" not in text.lower():
                    continue
                return raw.replace(",", "")
    return None


def _extract_timing(*texts: str | None) -> str | None:
    for text in texts:
        if not text:
            continue
        match = _DAYS_RE.search(text)
        if match:
            return f"{match.group(1)}_days"
    return None


def _authority_status(claim: SourceClaim) -> str:
    blob = " ".join(
        filter(
            None,
            [
                claim.source_path,
                claim.claim_text,
                (claim.attributes_json or {}).get("authority_note"),
            ],
        )
    ).lower()
    path = (claim.source_path or "").lower()
    if "legacy/" in path or "outdated" in path:
        return "superseded"
    if any(m in blob for m in _OUTDATED_MARKERS):
        return "superseded"
    return "current"


def extract_claim_semantics(claim: SourceClaim) -> StructuredSemantics:
    texts = (
        claim.claim_text,
        claim.condition_text,
        claim.action_text,
        claim.result_text,
        claim.exception_text,
    )
    state = None
    blob = " ".join(t for t in texts if t).lower()
    for token in ("paid", "draft", "pending", "approved", "rejected"):
        if token in blob:
            state = token
            break
    exception = claim.exception_text
    if not exception and any(m in blob for m in _EXCEPTION_MARKERS):
        # Capture short exception fragment from claim text when structured field empty
        for marker in _EXCEPTION_MARKERS:
            if marker in blob:
                exception = claim.claim_text
                break
    return StructuredSemantics(
        actor=claim.actor,
        action=claim.action_text,
        action_family=_action_family(claim.action_text, claim.claim_text, claim.subject_text),
        object=claim.subject_text,
        condition=claim.condition_text,
        threshold=_extract_threshold(*texts),
        state=state,
        exception=exception,
        outcome=claim.result_text,
        timing=_extract_timing(*texts),
        authority_status=_authority_status(claim),
    )


def merge_semantics(members: list[StructuredSemantics]) -> StructuredSemantics:
    """Prefer non-empty fields from stronger (current) members."""
    if not members:
        return StructuredSemantics()
    current = [m for m in members if m.authority_status != "superseded"] or members
    pick = current[0]

    def first(attr: str) -> Any:
        for m in current:
            val = getattr(m, attr)
            if val:
                return val
        for m in members:
            val = getattr(m, attr)
            if val:
                return val
        return None

    return StructuredSemantics(
        actor=first("actor"),
        action=first("action"),
        action_family=first("action_family") or pick.action_family,
        object=first("object"),
        condition=first("condition"),
        threshold=first("threshold"),
        state=first("state"),
        exception=first("exception"),
        outcome=first("outcome"),
        timing=first("timing"),
        authority_status="current"
        if any(m.authority_status == "current" for m in members)
        else (pick.authority_status or "unknown"),
    )


def semantics_differ_materially(a: StructuredSemantics, b: StructuredSemantics) -> bool:
    """True when merge should NOT happen."""
    if a.identity_key() != b.identity_key():
        return True
    # Same identity key already encodes threshold/state/timing/action/actor class.
    # Still refuse merge when exception presence differs on a prohibition-style family.
    a_exc = bool((a.exception or "").strip())
    b_exc = bool((b.exception or "").strip())
    if a_exc != b_exc and a.action_family in {"delete", "approve"}:
        # Exception-only cluster vs base prohibition stays separate for attachment.
        return True
    return False


def looks_implementation_detail(claim: SourceClaim) -> bool:
    blob = f"{claim.source_path or ''} {claim.claim_text or ''}".lower()
    return any(m in blob for m in _IMPL_DETAIL_MARKERS)


def looks_exception_claim(claim: SourceClaim, semantics: StructuredSemantics) -> bool:
    if claim.exception_text:
        return True
    blob = (claim.claim_text or "").lower()
    return any(m in blob for m in ("except", "exception", "correction workflow", "admin may"))
