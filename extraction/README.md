# ruleatlas-extraction

**Rule-candidate extraction.** Turns source files, BDD specs, comments, and docs into **candidate claims**
(never confirmed rules), each carrying evidence (path + line range + snippet) and a capped confidence.

> Status: **scaffold** — initialized and importable. The extraction logic currently lives in
> `apps/api` (`application/extraction/*`, `application/bdd/*`, `infrastructure/extraction/*`); the ORM-free
> pieces (e.g. `application/extraction/heuristic_claim_extraction.py`) are staged to move here.

## Responsibility

This is the heuristic/text-first extraction layer. Per the project's rules, AI/heuristic extraction creates
*candidate* claims that must be tied to evidence and provenance — this package owns that step.

| Belongs here | Does **not** belong here |
| --- | --- |
| Heuristic keyword/regex candidate extraction | Persisting rules/claims (DB) → `apps/api` |
| BDD (`Given/When/Then`) claim extraction | AI enrichment / synthesis → `ruleatlas-ai` |
| Comment/docstring classification | Clustering/conflict/gap analysis → `ruleatlas-claims` |
| Scaffold vs. real-logic filtering | File discovery/typing → `ruleatlas-discovery` |

## Dependency position

```
ruleatlas-contracts ─┐
ruleatlas-discovery ─┴─▶ ruleatlas-extraction ─▶ (consumed by apps/api worker)
```

**Boundary rule:** may import `ruleatlas-contracts` and `ruleatlas-discovery` only. Must not import `claims`,
`ai`, `exports`, persistence, or API code.

## Target contents (migration map)

| Target module (here) | Moves from (`apps/api/src/ruleatlas/…`) |
| --- | --- |
| `heuristic/` | `application/extraction/heuristic_claim_extraction.py`, `infrastructure/extraction/heuristic_extractor.py`, `file_reader.py` (DTO-out here; DB read stays in app) |
| `scaffold/` | now in the kernel (`ruleatlas_contracts.classification.*`) — extraction consumes it |
| `comments/` | `application/extraction/comment_classifier.py` |
| `bdd/` | `application/bdd/bdd_claims.py` (`claims_from_scenario` — pure) |
| `schemas.py` | `application/extraction/schemas.py` (`ExtractionCandidate`, `ExtractionEvidence`) |

## Multi-language extraction (worked example)

The extractor is **language-neutral text processing** plus **per-language regex catalogs** (imports, test
markers, comment styles from `ruleatlas-discovery`). The same rule — *"invoices over $10,000 require manager
approval"* — is picked up from each language and normalized to an equivalent `ClaimDraft`.

**Python** (`billing/approvals.py`):
```python
if invoice.total > 10_000:
    require_manager_approval(invoice)   # business rule: large invoices need sign-off
```
→ `ClaimDraft(condition_text="invoice total exceeds 10000", action_text="require manager approval",`
`provider_key="heuristic", claim_role="implementation", confidence≈0.42)`

**TypeScript** (`src/billing/approvals.ts`):
```typescript
if (invoice.total > 10000) requireManagerApproval(invoice); // large invoices need sign-off
```
→ structurally the **same** `ClaimDraft` (only `source_path`/`evidence` differ).

**PHP** (`src/Billing/Approvals.php`):
```php
if ($invoice->total > 10000) { requireManagerApproval($invoice); } // large invoices need sign-off
```
→ same claim shape again.

**Config** (`billing.yml`) — a different provider (`config_value`) recognizes business-relevant keys:
```yaml
invoice_approval_threshold: 10000
```
→ `ClaimDraft(provider_key="config_value", subject_text="invoice_approval_threshold", claim_role="configuration")`

**BDD / Gherkin** (`features/invoice_approval.feature`) — language-agnostic product intent:
```gherkin
Given an invoice over $10,000
When it is submitted
Then manager approval is required
```
→ `ClaimDraft(provider_key="bdd_gherkin", claim_role="product_intent", condition_text="an invoice over $10,000",`
`action_text="it is submitted", result_text="manager approval is required")`

### Why the per-language regexes matter

Only the *recognition* is language-specific (how a comment starts, how a test file is named, how imports are
written); the *output* is uniform. That means adding a language is a matter of extending the
`ruleatlas-discovery` catalogs + a small regex set here — never touching `claims`, `ai`, or `exports`.
This package is also the natural home for a future Semgrep/tree-sitter **structural** candidate provider,
which would emit the same `ClaimDraft`s from real ASTs across Python/PHP/TypeScript (see the decomposition doc).

## Public API

`ruleatlas_extraction.__all__` — the extractor entry points and candidate schemas. Scaffold exports
`__version__` only.

## Development

```bash
cd packages/extraction
uv sync --extra dev
python -m pytest && python -m mypy src && python -m ruff check src tests
```
