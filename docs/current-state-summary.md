# RuleAtlas packages current-state summary

**Authority date:** 2026-07-28  
**Audit:** [audit-findings-2026-07-28.md](audit-findings-2026-07-28.md)  
**AST/MCP/AI plan:** [ast-mcp-ai-rule-discovery-plan.md](ast-mcp-ai-rule-discovery-plan.md)

## Purpose

This repository contains the reusable, typed Python packages consumed by the RuleAtlas API. It
owns stable contracts, persistence, discovery utilities, claims, AI validation, exports,
provider-neutral extraction schemas, and a dev-only demo leaf. Application orchestration,
tree-sitter runtime construction, MCP transport, provider credentials, FastAPI, RQ, and Alembic
remain in the monorepo.

## Package status

All eight packages are extracted and independently buildable:

- `ruleatlas-contracts`
- `ruleatlas-discovery`
- `ruleatlas-persistence`
- `ruleatlas-extraction`
- `ruleatlas-claims`
- `ruleatlas-ai`
- `ruleatlas-exports`
- `ruleatlas-demo` (development-only leaf)

AST DTOs and citations, MCP tool contracts, investigation budgets/outcomes, AST persistence
models/repositories/lifecycle, proposal validation, and claim normalization are implemented.
Heuristic business-rule generation has been removed from the package boundary.

## Dependency direction

The package DAG is acyclic and enforced by import-linter. `contracts` is the shared kernel;
`persistence` is the shared ORM layer; `demo` may depend on the production packages, while no
production package may depend on `demo`.

## Validation snapshot

The 2026-07-28 isolated `uv` matrix passed for every package:

| Gate | Observed result |
| --- | --- |
| Ruff / strict mypy | All eight packages clean |
| Pytest | 229 tests |
| Build | 8 wheels and 8 sdists |
| Import contract | 1 kept; 0 broken |
| Twine | All 16 artifacts valid |
| Dependency audit | No known vulnerabilities |
| Consumer smoke | Built wheels installed in a fresh environment; README examples passed |
| Release workflow | Pinned actions, package-tag validation, and pre-publish gates |

Current package repository commit consumed by the monorepo:
`f0e3beee27dfbca651d64b700f3315a0bc8bcf80`.

## Development

```bash
cd packages/<name>
uv sync --all-extras
uv run --all-extras ruff check src tests
uv run --all-extras mypy src
uv run --all-extras pytest
uv build
```

## Readiness

The packages are release-ready at the repository boundary. Customer-production readiness still
depends on application-level production-scale evaluation, live-provider evidence, and operational
sign-off in the RuleAtlas monorepo.
