"""RuleAtlas AI: providers, connections, governance, and synthesis.

Everything AI-facing, kept isolated so the core scan/extraction path never hard-depends on it:

- **Providers / connections**: OpenAI-compatible client, connection config, capability probing, secure
  credential handling (delegated to the app's secret store), SSRF-guarded ``base_url`` validation.
- **Governance**: local-only / budget / allowed-model / license enforcement — AI calls are gated.
- **Synthesis**: turn candidate-claim *clusters* into **candidate rules** (always ``NEEDS_REVIEW``; never
  auto-confirmed). Structural provider adapters (Semgrep / semantic) that emit claims live here too.

Invariants (from the project rules): AI extraction creates candidate claims, not confirmed business rules;
MCP is optional and must not be required for core scanning. This package must be safely omittable — the
scan/extraction path degrades rather than fails when AI is unavailable.

Boundary: depends on ``ruleatlas-contracts`` and ``ruleatlas-claims`` (+ ``httpx``). Persistence and route
wiring stay in ``apps/api``.

Status: SCAFFOLD. See ``README.md`` and ``docs/architecture/package-decomposition.md``.
"""

from __future__ import annotations

from ruleatlas_ai.version import __version__

__all__: list[str] = ["__version__"]
