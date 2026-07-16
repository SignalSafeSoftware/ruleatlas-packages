"""Pure rule-text normalization for clustering / dedup / similarity (claims IR, ORM-free).

Language-agnostic: it lowercases, strips punctuation, and drops stopwords so that the same rule expressed in
Python, TypeScript, PHP, etc. normalizes to the same token bag for clustering.
"""

from __future__ import annotations

import re

__all__ = ["normalize_rule_text"]

_STOPWORDS = {"the", "a", "an", "must", "should", "may", "can", "will", "to", "for", "of", "in", "on", "and", "or"}


def normalize_rule_text(text: str) -> str:
    lowered = text.lower().strip()
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    tokens = [token for token in lowered.split() if token and token not in _STOPWORDS]
    return " ".join(tokens)
