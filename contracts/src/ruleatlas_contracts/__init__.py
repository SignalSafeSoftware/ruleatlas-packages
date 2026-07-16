"""RuleAtlas shared kernel (contracts).

This is the innermost package in the RuleAtlas decomposition: the *shared kernel*. It holds the small,
stable, dependency-free types that every other package and the ``apps/api`` app agree on:

- **Enums / vocabularies** — the typed string enums currently in ``ruleatlas.shared.enums`` (rule status,
  claim role, scan stage/status/type, source-location type, graph node/edge types, provider status, ...).
- **Provider contracts** — the language-agnostic normalization interfaces currently in
  ``ruleatlas.application.graph.provider_contract`` and ``ruleatlas.application.semantic.provider_contract``
  (``NormalizedGraphNode``/``NormalizedGraphEdge``/``StructuralAnalysisResult``, ``SemanticSymbol``/
  ``SemanticReference``/``SemanticAnalysisResult``, ``ProviderCapability``).
- **Claim DTO** — the transport shape of a candidate claim (``ClaimDraft``) shared between extraction, AI
  synthesis, and persistence.
- **Domain value objects** — small, behavior-light types that model the business vocabulary.

BOUNDARY RULE (enforced during migration): this package must depend on the Python standard library only.
It must never import SQLAlchemy, FastAPI, httpx, boto3, or any other RuleAtlas package. Everything depends
inward on the kernel; the kernel depends on nothing.

Status: SCAFFOLD. No symbols have been migrated in yet — see ``README.md`` and
``docs/architecture/package-decomposition.md`` for the target module map and migration phases.
"""

from __future__ import annotations

from ruleatlas_contracts.version import __version__

__all__: list[str] = ["__version__"]
