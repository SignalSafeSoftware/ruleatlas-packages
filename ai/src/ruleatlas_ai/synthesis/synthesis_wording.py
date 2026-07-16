"""Deterministic wording + JSON-extraction helpers for AI synthesis.

Extracted from ``ai_synthesis.workflow`` (god-module split). Pure text/selection logic over already-loaded
claim dicts — no DB, HTTP, or provider calls.
"""

from __future__ import annotations

import json

from ruleatlas_contracts.enums import SourceClaimRole


def _normalize_provider(raw: str | None) -> str:
    value = (raw or "").strip().lower()
    if value in {"openai", "chatgpt", "openai_remote"}:
        return "openai_remote"
    return value


def _strip_markdown_code_fence(text: str) -> str:
    """Remove optional ``` / ```json fences without regex backtracking."""
    cleaned = text.strip()
    if not cleaned.startswith("```"):
        return cleaned
    body = cleaned[3:]
    if body[:4].lower() == "json":
        body = body[4:]
    body = body.lstrip("\n\r")
    if body.endswith("```"):
        body = body[:-3]
    return body.strip()


def _extract_json_object(text: str) -> dict:
    cleaned = _strip_markdown_code_fence(text)
    try:
        payload = json.loads(cleaned)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("OpenAI response did not contain a JSON object")
    payload = json.loads(cleaned[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("OpenAI JSON payload must be an object")
    return payload


def _pick_intent_claim(*, subject: str, intents: list[dict]) -> dict | None:
    bdd_intents = [c for c in intents if "bdd scenario" in (c.get("claim_text") or "").lower()]
    if bdd_intents:
        return bdd_intents[0]
    for candidate in intents:
        path = (candidate.get("source_path") or "").lower()
        text = (candidate.get("claim_text") or "").lower()
        if subject and (subject in path or subject.replace("_", " ") in text):
            return candidate
    return intents[0] if intents else None


def _wording_from_seed(
    *,
    seed: dict,
    impl: dict | None,
    intent: dict | None,
    verify: dict | None,
    cluster_label: str | None,
) -> str:
    wording = str(seed.get("claim_text") or cluster_label or "")
    if intent and intent.get("result_text"):
        return str(intent["result_text"])
    if intent and intent.get("claim_text"):
        text = str(intent["claim_text"])
        return text.split(": ", 1)[1] if ": " in text and text.lower().startswith("bdd scenario") else text
    if verify and verify.get("claim_text") and seed is impl:
        return f"{wording} (verified by: {verify['claim_text'][:120]})"
    return wording


def _resolve_configuration_wording(
    *,
    wording: str,
    intent: dict | None,
    impl: dict | None,
) -> tuple[str, str | None]:
    if not wording.lower().startswith("configuration value"):
        return wording, None
    if intent and intent.get("claim_text") and not str(intent["claim_text"]).lower().startswith("configuration"):
        return str(intent["claim_text"]), None
    if impl and impl.get("claim_text") and not str(impl.get("claim_text") or "").lower().startswith("configuration"):
        return str(impl["claim_text"]), None
    return wording, "configuration-only cluster"


def _deterministic_wording(
    *,
    cluster_label: str | None,
    claims_detail: list[dict],
) -> tuple[dict | None, str, str | None]:
    """Build deterministic wording. Returns (seed, wording, skip_reason)."""
    impl = next((c for c in claims_detail if c.get("claim_role") == SourceClaimRole.IMPLEMENTATION.value), None)
    intents = [c for c in claims_detail if c.get("claim_role") == SourceClaimRole.PRODUCT_INTENT.value]
    verify = next(
        (c for c in claims_detail if c.get("claim_role") == SourceClaimRole.VERIFICATION.value),
        None,
    )
    subject = (cluster_label or "").lower()
    intent = _pick_intent_claim(subject=subject, intents=intents)

    seed = intent or impl or (claims_detail[0] if claims_detail else None)
    if seed is None:
        raise ValueError("Cluster has no claims")

    wording = _wording_from_seed(
        seed=seed,
        impl=impl,
        intent=intent,
        verify=verify,
        cluster_label=cluster_label,
    )
    wording, skip_reason = _resolve_configuration_wording(wording=wording, intent=intent, impl=impl)
    return seed, wording, skip_reason
