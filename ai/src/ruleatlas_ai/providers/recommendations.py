"""Recommendation labels only — never replaces dynamic discovery."""

from __future__ import annotations

# Display/ordering hints only. Catalog must come from provider list_models().
OPENAI_RECOMMENDATION_METADATA: dict[str, dict[str, object]] = {
    "gpt-4o-mini": {
        "display_name": "GPT-4o mini",
        "recommended_use": "Default synthesis; low cost",
        "ordering": 10,
        "hint_tool_calling": True,
        "hint_structured_output": True,
    },
    "gpt-4o": {
        "display_name": "GPT-4o",
        "recommended_use": "Higher-quality synthesis",
        "ordering": 20,
        "hint_tool_calling": True,
        "hint_structured_output": True,
    },
    "gpt-4.1-mini": {
        "display_name": "GPT-4.1 mini",
        "recommended_use": "Fast synthesis candidate",
        "ordering": 15,
        "hint_tool_calling": True,
        "hint_structured_output": True,
    },
}


def recommendation_for(model_id: str) -> dict[str, object] | None:
    return OPENAI_RECOMMENDATION_METADATA.get(model_id)
