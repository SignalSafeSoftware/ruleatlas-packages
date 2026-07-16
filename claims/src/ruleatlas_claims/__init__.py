"""RuleAtlas rule intermediate representation (claims IR).

The language-agnostic middle layer where candidate claims from many providers (heuristic extraction,
Semgrep, semantic providers) are normalized, related, clustered, and reconciled *before* they become rules:

- **Claims**: normalized candidate assertions with role, condition/action/result, provenance, evidence.
- **Graph**: normalized nodes/edges + canonical-key identity across providers.
- **Clustering / canonicalization**: grouping equivalent claims into canonical candidates.
- **Conflicts / gaps**: detecting contradictions and missing coverage across claims.

This is the correct place to normalize for business-rule extraction — you normalize *claims and
relationships*, not raw syntax. It is deliberately pure/algorithmic: no DB, HTTP, or AI calls.

Boundary: depends only on ``ruleatlas-contracts``. Persistence lives in ``apps/api``; AI synthesis of
clusters into candidate rules lives in ``ruleatlas-ai``.

Status: SCAFFOLD. See ``README.md`` and ``docs/architecture/package-decomposition.md``.
"""

from __future__ import annotations

from ruleatlas_claims.version import __version__

__all__: list[str] = ["__version__"]
