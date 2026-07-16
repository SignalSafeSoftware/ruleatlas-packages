# ruleatlas-contracts

**The shared kernel.** Small, stable, dependency-free types that every other RuleAtlas package and the
`apps/api` application agree on. This is the innermost ring of the architecture: everything depends inward
on it, and it depends on nothing.

> Status: **scaffold**. The package is initialized and importable, but no symbols have been migrated in yet.
> See [the migration plan](../../docs/architecture/package-decomposition.md) for sequencing.

## Why this package exists

Today the backend is a single ~75k-LOC package. The `domain` layer is effectively empty (~65 LOC), so the
shared vocabulary (enums, provider contracts, the claim DTO) lives scattered across `application/` and is
imported in every direction. That makes a clean package split impossible — there is no stable core to
depend on. `ruleatlas-contracts` **is** that core.

## Responsibility

| Belongs here | Does **not** belong here |
| --- | --- |
| Typed enums / vocabularies (`RuleStatus`, `ClaimRole`, `ScanStage`, `GraphNodeType`, …) | SQLAlchemy models / ORM |
| Provider contracts (`NormalizedGraphNode/Edge`, `SemanticSymbol/Reference`, `ProviderCapability`) | FastAPI routes / Pydantic request-response schemas |
| The candidate-claim DTO (`ClaimDraft`) and evidence shape | Business logic / services / orchestration |
| Domain value objects (small, behavior-light) | I/O: DB, HTTP, filesystem, secrets |
| Canonical-key helpers (pure functions) | Anything that imports another `ruleatlas-*` package |

## Dependency position

```
        (nothing)
            ▲
   ┌────────┴────────┐
   │ ruleatlas-      │   ← this package
   │   contracts     │
   └────────┬────────┘
            ▼  depended on by
  discovery · extraction · claims · ai · exports · demo · apps/api
```

**Boundary rule (hard):** standard library only. No `ruleatlas-*` imports; no SQLAlchemy/FastAPI/httpx/boto3.
This rule is what keeps the whole DAG acyclic.

## Target contents (migration map)

Symbols will move here from the current backend, in this order:

| Target module (here) | Moves from (`apps/api/src/ruleatlas/…`) |
| --- | --- |
| `enums/` (split by domain) | `shared/enums.py` (904 LOC — split into `enums/rules.py`, `enums/scanning.py`, `enums/graph.py`, `enums/ai.py`, …) |
| `graph_contract.py` | `application/graph/provider_contract.py` |
| `semantic_contract.py` | `application/semantic/provider_contract.py` |
| `claims.py` (`ClaimDraft`, evidence shape) | `application/claims/claim_service.py` (DTO portion only) |
| `canonical_keys.py` | pure key helpers from `application/graph/graph_service.py` |
| `value_objects/` | `domain/` (grown out, not left empty) |

## Public API

`ruleatlas_contracts.__all__` is the contract surface. Keep it curated and additive — consumers import from
the top-level package, not deep modules. Currently exports only `__version__` (scaffold).

## Development

```bash
cd packages/contracts
uv sync --extra dev        # or: pip install -e ".[dev]"
python -m pytest
python -m mypy src
python -m ruff check src tests
python -m build            # produces a wheel/sdist
```

## Wiring into apps/api (done during extraction, not yet)

```toml
# apps/api/pyproject.toml  → [tool.poetry.dependencies]
ruleatlas-contracts = { path = "../../packages/contracts", develop = true }
```
