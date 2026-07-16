# ruleatlas-exports

**Report and artifact builders.** Pure rendering of already-computed analysis data into user-facing
artifacts: Markdown/CSV/JSON reports for discovery inventories, analysis results, and comparisons.

> Status: **scaffold** — initialized and importable; no logic migrated yet.

## Responsibility

| Belongs here | Does **not** belong here |
| --- | --- |
| Report generators (Markdown/JSON) | Querying the DB for the data → `apps/api` |
| CSV builders + formula-injection sanitization | Route/streaming/download plumbing → `apps/api` |
| Comparison/diff export formatting | Business logic that *computes* results → `claims`/`ai` |

Rule of thumb: `apps/api` gathers the data and hands it in; this package turns it into bytes. That keeps
exports free of DB/session coupling and trivially unit-testable.

## Dependency position

```
ruleatlas-contracts ─▶ ruleatlas-exports ─▶ consumed by apps/api (routes stream the bytes)
```

**Boundary rule:** imports `ruleatlas-contracts` only.

## Target contents (migration map)

| Target module (here) | Moves from (`apps/api/src/ruleatlas/infrastructure/exports/…`) |
| --- | --- |
| `discovery/` | `discovery_report_builder.py`, `discovery_inventory_builder.py` |
| `analysis/` | `analysis_structured_export_builder.py`, `report_generators.py` |
| `compare/` | `compare_export_builder.py` |
| `csv_safety.py` | `csv_safety.py` (`sanitize_csv_cell`) |

## Development

```bash
cd packages/exports
uv sync --extra dev
python -m pytest && python -m mypy src && python -m ruff check src tests
```
