"""Language-agnostic rule-text normalization used for clustering/dedup."""

from __future__ import annotations

from ruleatlas_claims.text_normalize import normalize_rule_text


def test_lowercases_and_drops_stopwords() -> None:
    assert normalize_rule_text("The Invoice") == "invoice"
    assert normalize_rule_text("An APPROVAL") == "approval"


def test_strips_punctuation_and_symbols() -> None:
    assert normalize_rule_text("Invoices over $10,000!") == "invoices over 10 000"


def test_modal_verbs_are_stopwords() -> None:
    # "must" is a stopword; "be"/"approved"/"invoice" survive.
    assert normalize_rule_text("Invoice must be approved.") == "invoice be approved"


def test_blank_is_empty() -> None:
    assert normalize_rule_text("   ") == ""
