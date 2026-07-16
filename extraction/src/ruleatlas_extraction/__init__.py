"""RuleAtlas rule-candidate extraction.

Turns source files (and BDD specs, comments, docs) into **candidate claims** — never confirmed rules. This
is the heuristic/text-first extraction layer: it reads file text, applies keyword/regex/structural
heuristics, and emits ``ClaimDraft``-shaped candidates with evidence spans (path + line range + snippet)
and a capped confidence.

Boundary: depends on ``ruleatlas-contracts`` (claim/enum types) and ``ruleatlas-discovery`` (file typing).
It must not import persistence, API, or AI packages — extraction produces candidates; storing them and
enriching them with AI happen downstream (``apps/api`` + ``ruleatlas-ai``).

Status: SCAFFOLD. See ``README.md`` and ``docs/architecture/package-decomposition.md``.
"""

from __future__ import annotations

from ruleatlas_extraction.version import __version__

__all__: list[str] = ["__version__"]
