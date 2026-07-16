# ruleatlas-claims

**The rule intermediate representation (IR).** The language-agnostic middle layer where candidate claims are
normalized, related into a graph, clustered, and reconciled (conflicts/gaps) — *before* anything becomes a
confirmed rule.

> Status: **scaffold** — initialized and importable; no logic migrated yet.

## Why this is the real "language-independent layer"

RuleAtlas already normalizes at the **claim/graph** level rather than forcing a universal syntax tree (see
[the UAST analysis](../../docs/architecture/package-decomposition.md#appendix-language-independent-ast)).
This package is the home of that IR: providers in different languages all emit claims/edges into these
shared shapes.

## Responsibility

| Belongs here | Does **not** belong here |
| --- | --- |
| Claim normalization + roles (condition/action/result/exception) | Producing raw candidates → `ruleatlas-extraction` / `ruleatlas-ai` |
| Graph model + canonical-key identity | DB persistence of graph/claims → `apps/api` |
| Clustering + canonicalization of equivalent claims | AI synthesis of clusters → `ruleatlas-ai` |
| Conflict detection + gap analysis (algorithms) | HTTP/route handling → `apps/api` |
| Confidence scoring of candidates | — |

## Dependency position

```
ruleatlas-contracts ─▶ ruleatlas-claims ─▶ consumed by ruleatlas-ai, ruleatlas-exports, apps/api
```

**Boundary rule:** imports `ruleatlas-contracts` only. Pure/algorithmic — no DB, HTTP, filesystem, or AI.

## Target contents (migration map)

| Target module (here) | Moves from (`apps/api/src/ruleatlas/…`) |
| --- | --- |
| `graph/` | `application/graph/graph_service.py` (algorithmic parts) |
| `clustering/` | `application/clustering/canonicalize.py`, clustering logic |
| `conflicts/` | `application/conflicts/*` (incl. `conflict_detection_v2.py`) |
| `gaps/` | `application/gaps/*` |
| `rules/` | `application/rules/*` (dedup, lineage, category — pure parts) |
| `scoring/` | `application/scoring/*` (`confidence_v2.py`) |

Persistence-bound code (writing `SourceClaim`, `RuleConflict`, etc.) stays in `apps/api`; this package
computes, the app persists.

## Development

```bash
cd packages/claims
uv sync --extra dev
python -m pytest && python -m mypy src && python -m ruff check src tests
```
