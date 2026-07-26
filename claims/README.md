# ruleatlas-claims

**The rule intermediate representation (IR).** The language-agnostic middle layer where candidate claims are
normalized, related into a graph, clustered, and reconciled (conflicts/gaps) — *before* anything becomes a
confirmed rule.

> Status: **partially migrated (extraction started).** Three ORM-free modules are now **in this package** and
> imported by `apps/api`: `confidence_scorer` (pure scoring), `relationship_suggester` (pure heuristics + DTOs),
> and `text_normalize` (`normalize_rule_text`). Wired via Poetry path dep + Dockerfile; verified end-to-end
> (mypy 525, full suite 1319, image builds). The ORM-coupled modules (clustering/conflict persistence,
> `structured_semantics` which uses the `SourceClaim` model) await Phase-3 dependency inversion before they move.

## Current contents (extracted)

| Module | Contents |
| --- | --- |
| `confidence_scorer.py` | Model-free confidence scoring: DTOs (`RuleConfidenceInputs`, `EvidenceView`) + `score_rule_confidence` (kernel deps only). Static-analysis evidence is a weighted corroborating source (below code/tests; never confirming alone). |
| `ast_evidence.py` | Cited AST observation inputs and deterministic implementation-confidence scoring with resolution, parse-quality, and parser-error dampening |
| `relationship_suggester.py` | Pure relationship heuristics + DTOs (`RuleView`, `EvidenceView`, `SuggestionCandidate`, `suggest_deterministic_relationships`, `filter_best_candidates`) |
| `text_normalize.py` | `normalize_rule_text` — language-agnostic token normalization for clustering/dedup |
| `ast_normalization.py` | Pure normalization of citation-validated AST proposals into implementation/product-intent `ClaimDraft`s with stable citation IDs, origin metadata, and behavior-sensitive deduplication |

AST normalization never promotes inferred intent into a product-intent claim. Inferred intent remains
labeled metadata on the implementation observation; a separate product-intent claim is emitted only
for observed intent with product-intent evidence. Equivalent claims merge citation and origin sets,
but proposals with distinct observed behavior retain distinct deduplication identities.

AST confidence is a separately reported, capped implementation signal. Extracted, resolved, inferred,
and ambiguous observations receive decreasing weight; partial parses and parser errors reduce it
further. AST evidence never contributes to product-intent confidence. Numeric confidence also remains
separate from authority: an approved status affects the authority boundary only when an explicit
human approval record is present.

## Why this is the real "language-independent layer"

RuleAtlas normalizes at the **claim/graph** level rather than forcing a universal syntax tree (see
[the UAST analysis](https://github.com/SignalSafeSoftware/ruleatlas/blob/main/docs/architecture/package-decomposition.md#appendix-language-independent-ast)).
This package is the home of that IR: providers in different languages all emit `ClaimDraft`s (from the
kernel), and this layer relates and de-duplicates them **without knowing or caring what language they came
from**.

## Responsibility

| Belongs here | Does **not** belong here |
| --- | --- |
| Claim normalization + roles (condition/action/result/exception) | Producing raw candidates → `ruleatlas-extraction` / `ruleatlas-ai` |
| Graph model + canonical-key identity | DB persistence of graph/claims → `apps/api` |
| Clustering + canonicalization of equivalent claims | AI synthesis of clusters → `ruleatlas-ai` |
| Conflict detection + gap analysis (algorithms) | HTTP/route handling → `apps/api` |
| Confidence scoring + relationship suggestion (pure) | — |

## Dependency position

```
ruleatlas-contracts ─▶ ruleatlas-claims ─▶ consumed by ruleatlas-ai, ruleatlas-exports, apps/api
```

**Boundary rule:** imports `ruleatlas-contracts` only. Pure/algorithmic — no DB, HTTP, filesystem, or AI.

## Cross-language clustering (the payoff)

This is where the multi-language design pays off. Recall the single rule *"invoices over $10,000 require
manager approval."* In a real codebase it shows up as **five independent claims** from five providers:

| # | Source | `provider_key` | `claim_role` | `source_path` |
| --- | --- | --- | --- | --- |
| 1 | Python backend | `heuristic` | `implementation` | `billing/approvals.py` |
| 2 | TypeScript frontend | `heuristic` | `implementation` | `src/billing/approvals.ts` |
| 3 | PHP service | `heuristic` | `implementation` | `src/Billing/Approvals.php` |
| 4 | PHPUnit test | `heuristic` | `verification` | `tests/ApprovalsTest.php` |
| 5 | Gherkin feature | `bdd_gherkin` | `product_intent` | `features/invoice_approval.feature` |

Clustering keys on the **normalized subject + action family** (`invoice_approval` / `approve`), *not* on
syntax, so all five collapse into **one canonical cluster**:

```
ClaimCluster "invoice_approval / approve"
├── canonical:   #1 Python implementation        (highest authority: backend code)
├── supporting:  #2 TypeScript, #3 PHP            (same rule, other layers → supporting evidence)
├── verification:#4 PHPUnit test                  (expected-behavior evidence)
└── product_intent: #5 Gherkin scenario           (what the business asked for)
```

If the PHP service instead used `> 5000`, this layer flags a **conflict** (same subject/action, different
threshold) across languages — exactly the kind of cross-language drift RuleAtlas exists to surface. If the
Gherkin scenario exists but no implementation claim does, it's a **gap** (product intent with no code).

None of `canonicalize`, `conflict_detection`, or `gap analysis` branches on language — they operate purely on
the kernel's `ClaimDraft`/cluster shapes. Adding Ruby or Go support adds providers upstream; this package is
untouched.

## Target contents (migration map)

| Target module (here) | Moves from (`apps/api/src/ruleatlas/…`) |
| --- | --- |
| `graph/` | `application/graph/graph_service.py` (algorithmic parts) |
| `clustering/` | `application/clustering/canonicalize.py`, `cluster_service.py` |
| `conflicts/` | `application/conflicts/*` (incl. `conflict_detection_v2.py`) |
| `gaps/` | `application/gaps/*` |
| `rules/` | `application/rules/*` (`relationship_suggester.py`, dedup, category — pure parts) |
| `scoring/` | `application/scoring/confidence_scorer.py`, `confidence_v2.py` |
| `semantics/` | `application/claims/structured_semantics.py` |

Persistence-bound code (writing `SourceClaim`, `RuleConflict`, etc.) stays in `apps/api`; this package
computes, the app persists.

## Development

```bash
cd packages/claims
uv sync --extra dev
python -m pytest && python -m mypy src && python -m ruff check src tests
```
