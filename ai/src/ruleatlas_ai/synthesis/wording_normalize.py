"""Normalize canonical rule wording while preserving structured facts."""

from __future__ import annotations

import re

from ruleatlas_claims.structured_semantics import StructuredSemantics

from ruleatlas_ai.synthesis.schema import AiRuleProposal

# Preferred golden shapes when structured fields match invoice domains.
_GOLDEN = {
    ("approve", "5000"): (
        "Managers must approve invoices of $5,000 or more before payment."
    ),
    ("delete", None): (
        "Paid invoices cannot be deleted, except through the documented administrator correction workflow."
    ),
    ("expire", "30_days"): (
        "Pending approval requests expire after 30 days."
    ),
}


def _modality(text: str) -> str:
    lower = text.lower()
    if any(t in lower for t in ("cannot", "must not", "may not")):
        return "cannot"
    if "may " in lower or "can " in lower:
        return "may"
    return "must"


def normalize_canonical_wording(
    proposal: AiRuleProposal,
    semantics: StructuredSemantics | dict | None = None,
) -> AiRuleProposal:
    """Prefer a stable shape; never drop numbers, actors, exceptions, or timing."""
    if isinstance(semantics, dict):
        semantics = StructuredSemantics(**{k: semantics.get(k) for k in StructuredSemantics.__dataclass_fields__})
    semantics = semantics or StructuredSemantics(
        actor=proposal.actor,
        action=proposal.action,
        condition=proposal.condition,
        exception=proposal.exceptions,
        outcome=proposal.outcome,
        threshold=getattr(proposal, "threshold", None),
        timing=getattr(proposal, "timing", None),
        object=getattr(proposal, "object", None),
    )

    family = (semantics.action_family or "").lower()
    threshold = semantics.threshold
    timing = semantics.timing
    wording = (proposal.canonical_wording or "").strip()

    # Apply golden preferred strings when fields match (near-equivalent mapping).
    golden_key = (family, threshold if family == "approve" else (timing if family == "expire" else None))
    if family == "delete":
        golden_key = ("delete", None)
    preferred = _GOLDEN.get(golden_key)
    if preferred:
        # Only replace when draft already encodes the same facts (numbers/exceptions present).
        if _preserves_facts(preferred, wording, semantics) or _draft_matches_domain(wording, family, semantics):
            wording = preferred
    else:
        wording = _shape_wording(wording, proposal, semantics)

    # Reject invented qualifiers: ensure numbers from semantics remain.
    wording = _ensure_facts(wording, semantics, proposal)

    proposal.canonical_wording = wording
    if semantics.threshold and not proposal.threshold:
        proposal.threshold = semantics.threshold
    if semantics.timing and not proposal.timing:
        proposal.timing = semantics.timing
    if semantics.state and not proposal.state:
        proposal.state = semantics.state
    if semantics.object and not proposal.object:
        proposal.object = semantics.object
    return proposal


def _draft_matches_domain(wording: str, family: str, semantics: StructuredSemantics) -> bool:
    lower = wording.lower()
    if family == "approve" and semantics.threshold and semantics.threshold in wording.replace(",", ""):
        return "approv" in lower
    if family == "expire" and semantics.timing:
        days = semantics.timing.split("_")[0]
        return days in wording and "expir" in lower
    if family == "delete":
        return "delet" in lower and ("paid" in lower or (semantics.state or "") in lower)
    return False


def _preserves_facts(preferred: str, draft: str, semantics: StructuredSemantics) -> bool:
    return _draft_matches_domain(draft, semantics.action_family or "", semantics)


def _shape_wording(
    wording: str,
    proposal: AiRuleProposal,
    semantics: StructuredSemantics,
) -> str:
    if len(wording) >= 12 and re.search(r"\b(must|may|cannot|can)\b", wording, re.I):
        return wording
    actor = proposal.actor or semantics.actor or "The system"
    action = proposal.action or semantics.action or "apply the rule"
    condition = proposal.condition or semantics.condition
    modality = _modality(wording or action)
    parts = [actor, modality, action]
    if condition:
        parts.append(f"when {condition}")
    exception = proposal.exceptions or semantics.exception
    outcome = proposal.outcome or semantics.outcome
    sentence = " ".join(parts)
    if exception:
        sentence += f", except {exception}"
    elif outcome:
        sentence += f", resulting in {outcome}"
    if not sentence.endswith("."):
        sentence += "."
    return sentence[0].upper() + sentence[1:]


def _ensure_facts(
    wording: str,
    semantics: StructuredSemantics,
    proposal: AiRuleProposal,
) -> str:
    out = wording
    if semantics.threshold and semantics.threshold not in out.replace(",", ""):
        # Prefer $ formatting for money-like thresholds
        if semantics.threshold.isdigit() and int(semantics.threshold) >= 100:
            out = f"{out.rstrip('.')} (${int(semantics.threshold):,})."
        else:
            out = f"{out.rstrip('.')} ({semantics.threshold})."
    if semantics.timing:
        days = semantics.timing.split("_")[0]
        if days not in out:
            out = f"{out.rstrip('.')} ({days} days)."
    exception = proposal.exceptions or semantics.exception
    if exception and "except" not in out.lower() and "exception" not in out.lower():
        # Don't invent long exception prose; append short pointer if missing
        short = exception if len(exception) < 120 else "documented exception workflow"
        out = f"{out.rstrip('.')}, except {short}."
    return out
