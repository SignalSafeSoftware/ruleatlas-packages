# ruleatlas-contracts

**The shared kernel.** Small, stable, dependency-free types that every other RuleAtlas package and the
`apps/api` application agree on. This is the innermost ring of the architecture: everything depends inward
on it, and it depends on nothing.

> Status: **extracted / in use.** Enums, the `ClaimDraft` DTO, provider contracts, the classification stack,
> and authorization policy have been migrated in and are imported by `apps/api` and the other packages.

## Why this package exists

The shared vocabulary of RuleAtlas — the enums, the candidate-claim DTO, the provider contracts — is imported
in every direction. Without a stable, dependency-free core to depend on, a clean package split is impossible.
`ruleatlas-contracts` **is** that core: it defines the *language-agnostic* shapes that let providers for
Python, TypeScript, PHP, Java, C#, Go, and Ruby all speak the same "claim" language.

## Responsibility

| Belongs here | Does **not** belong here |
| --- | --- |
| Typed enums / vocabularies (`RuleStatus`, `SourceClaimRole`, `EvidenceSourceType`, `RuleCategory`, …) | SQLAlchemy models / ORM |
| The candidate-claim DTO (`ClaimDraft`) and evidence shape | FastAPI routes / Pydantic request-response schemas |
| Provider contracts (graph + semantic: `NormalizedGraphNode/Edge`, `ProviderCapability`) | Business logic / services / orchestration |
| Classification stack (scaffold detection, rule category/display — pure) | I/O: DB, HTTP, filesystem, secrets |
| Authorization policy (`ROLE_RANK`, `permission_satisfied`) + canonical-key helpers | Anything that imports another `ruleatlas-*` package |

## Dependency position

```
        (nothing)
            ▲
   ┌────────┴────────┐
   │ ruleatlas-      │   ← this package (stdlib only)
   │   contracts     │
   └────────┬────────┘
            ▼  depended on by
  discovery · extraction · claims · ai · exports · demo · apps/api
```

**Boundary rule (hard):** standard library only. No `ruleatlas-*` imports; no SQLAlchemy/FastAPI/httpx/boto3.
This rule is what keeps the whole DAG acyclic.

## Current contents

| Module | Contents |
| --- | --- |
| `enums.py` | All typed vocabularies (`RuleStatus`, `SourceClaimRole`, `EvidenceSourceType`, `RuleCategory`, `ProjectRole`, `Permission`, …) |
| `claims.py` | `ClaimDraft` — the candidate-claim DTO + evidence shape |
| `graph_contract.py` | Structural-graph provider contract (`NormalizedGraphNode/Edge`, `ProviderCapability`) |
| `semantic_contract.py` | Semantic-analysis provider contract (`SemanticSymbol/Reference`) |
| `classification/` | Pure scaffold detection + rule categorization/display (`scaffold_classify`, `scaffold_markers`, `scaffold_filter`, `rule_category`, `rule_display`) |
| `authorization.py` | Pure project-role/permission policy (`ROLE_RANK`, `PERMISSION_MIN_ROLE`, `role_satisfies`, `permission_satisfied`) |

## Why `ClaimDraft` is language-agnostic (multi-language example)

The whole point of the kernel is that a business rule extracted from **any** language collapses to the same
shape. Consider one rule — *"invoices over $10,000 require manager approval"* — expressed in several
languages:

```python
# billing/approvals.py  (Python)
def submit_invoice(invoice):
    if invoice.total > 10_000:
        require_manager_approval(invoice)
```

```typescript
// src/billing/approvals.ts  (TypeScript)
export function submitInvoice(invoice: Invoice) {
  if (invoice.total > 10000) {
    requireManagerApproval(invoice);
  }
}
```

```php
// src/Billing/Approvals.php  (PHP)
function submitInvoice(Invoice $invoice): void {
    if ($invoice->total > 10000) {
        requireManagerApproval($invoice);
    }
}
```

```gherkin
# features/invoice_approval.feature  (BDD / Gherkin — language-agnostic)
Scenario: Large invoices need manager sign-off
  Given an invoice over $10,000
  When it is submitted
  Then manager approval is required
```

Each producer emits the **same** `ClaimDraft` — only `provider_key`, `source_path`, and `evidence` differ:

```python
from ruleatlas_contracts.claims import ClaimDraft

ClaimDraft(
    claim_text="Invoices over $10,000 require manager approval",
    provider_key="heuristic",          # or "bdd_gherkin", "structural_graph", "config_value"
    provider_version="1.0.0",
    claim_role="implementation",       # SourceClaimRole; BDD would be "product_intent"
    confidence=0.42,                    # heuristic candidates are capped low on purpose
    condition_text="invoice total exceeds 10000",
    action_text="require manager approval",
    subject_text="invoice_approval",   # stable clustering key derived from the path stem
    source_path="billing/approvals.py",  # ...or approvals.ts / Approvals.php / invoice_approval.feature
    start_line=2,
    evidence=[{"evidence_kind": "source_span", "reference_path": "billing/approvals.py",
               "start_line": 2, "end_line": 3, "excerpt": "if invoice.total > 10_000: ..."}],
    attributes={"never_auto_canonical": True},
)
```

Because the shape is identical, downstream packages (`claims`, `ai`, `exports`) never branch on language —
they operate on `ClaimDraft` alone. That is the "normalize at the claim level, not the syntax-tree level"
decision (see the [UAST appendix](../../docs/architecture/package-decomposition.md#appendix-language-independent-ast)).

## Enums span languages too

`EvidenceSourceType` and `SourceClaimRole` classify evidence regardless of source language — e.g.
`BACKEND_CODE` covers `approvals.py`, `approvals.ts`, and `Approvals.php` alike, while `UNIT_TEST` covers
`test_approvals.py`, `approvals.test.ts`, `ApprovalsTest.php`, and `ApprovalsTests.cs`. The classification
stack (`classification/`) uses these language-neutral vocabularies so scaffold-vs-real-logic detection works
the same way across the whole matrix.

## Public API

`ruleatlas_contracts.__all__` is the contract surface. Keep it curated and additive — consumers import from
the documented submodules (`ruleatlas_contracts.claims`, `.enums`, `.authorization`, `.classification.*`).

## Development

```bash
cd packages/contracts
uv sync --extra dev        # or: pip install -e ".[dev]"
python -m pytest && python -m mypy src && python -m ruff check src tests
python -m build            # produces a wheel/sdist
```

## Wiring into apps/api (done)

```toml
# apps/api/pyproject.toml  → [tool.poetry.dependencies]
ruleatlas-contracts = { path = "../../packages/contracts", develop = true }
```
