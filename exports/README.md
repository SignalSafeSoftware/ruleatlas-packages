# ruleatlas-exports

**Report and artifact builders.** Pure rendering of already-computed analysis data into user-facing
artifacts: Markdown/CSV/JSON reports for discovery inventories, analysis results, and comparisons.

> Status: **partially migrated** — the pure core is extracted and in use: `csv_safety`, `export_labels`,
> `markdown_builder`, and `report_types` now live here (wired into `apps/api` via Poetry path dep +
> Dockerfile; back-compat shims remain at the old `ruleatlas.infrastructure.exports.*` paths). The
> ORM-coupled builders still live in `apps/api` and move here after Phase-3 inversion.

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

## Current contents (extracted)

| Module | Contents |
| --- | --- |
| `csv_safety.py` | `sanitize_csv_cell` — neutralizes spreadsheet formula-injection (`= + - @`, tab, CR) |
| `export_labels.py` | Human labels + evidence-strength text keyed on `EvidenceSourceType` (kernel enum) |
| `markdown_builder.py` | `report_header`, `section`, `table`, `bullet_list`, `utc_timestamp_label` |
| `report_types.py` | `ExportReportSlug`, `EXPORT_REPORT_METADATA`, scoping sets |

## Target contents (still in apps/api, pending Phase-3 inversion)

| Target module (here) | Moves from (`apps/api/src/ruleatlas/infrastructure/exports/…`) |
| --- | --- |
| `discovery/` | `discovery_report_builder.py`, `discovery_inventory_builder.py` |
| `analysis/` | `analysis_structured_export_builder.py`, `report_generators.py` |
| `compare/` | `compare_export_builder.py` |

These are ORM + discovery-service orchestrators today; extracting them requires the app to pre-fetch and pass
DTOs (Phase 3) so the builders become pure.

## Multi-language output

Exports are language-agnostic by construction (they render kernel/claims data), but the *content* naturally
spans languages because a single rule's evidence does. A business-rules Markdown row for our running example
cites evidence from every layer/language at once:

```markdown
| Rule | Status | Evidence |
| --- | --- | --- |
| Invoices over $10,000 require manager approval | Needs review | `billing/approvals.py:2` (backend), `src/billing/approvals.ts:3` (frontend), `src/Billing/Approvals.php:4` (backend), `tests/ApprovalsTest.php` (test), `features/invoice_approval.feature` (product intent) |
```

`export_labels` maps each `EvidenceSourceType` to a trust label ("Strong implementation evidence",
"Expected-behavior evidence", "Product-intent evidence") the same way regardless of source language, and
`csv_safety` neutralizes attacker-controlled paths/snippets from any language before they reach a spreadsheet.

## Development

```bash
cd packages/exports
uv sync --extra dev
python -m pytest && python -m mypy src && python -m ruff check src tests
```
