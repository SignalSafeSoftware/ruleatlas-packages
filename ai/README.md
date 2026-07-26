# ruleatlas-ai

**Everything AI-facing, isolated.** Providers/connections, governance enforcement, and claim-cluster
synthesis — kept in one package so the core scan/extraction path never hard-depends on AI and can degrade
gracefully when AI is unavailable.

> Status: **extracted / in use** — the pure AI domain lives here: `budget`, `providers/` (probe
> parsing/diagnostics/payloads/sanitization, `protocols`, `credential_validation`, `connection_errors`,
> `recommendations`), and `synthesis/` (`schema`, `proposal_validation`, `synthesis_wording`, `wording_normalize`).
> The app keeps the provider *adapters* (`openai_adapter`, `openai_compatibility_probe`), governance (audit),
> connection/catalog/compatibility services, and the synthesis workflow/rule-persistence orchestrators — they wire
> providers, config, and the request-scoped service factory. Verified standalone (ruff + mypy + pytest) and in CI.

## Invariants (from the project rules)

- **AI extraction creates candidate claims, not confirmed rules.** Synthesized rules persist as
  `NEEDS_REVIEW`.
- **MCP is optional and must not be required for core scanning.** This whole package must be omittable; the
  pipeline degrades, not fails, without it.
- Outbound URLs (provider `base_url`, etc.) are SSRF-guarded; secrets are never logged.

## AST investigation contracts

`ruleatlas_ai.investigation` defines the provider-neutral state exchanged by a bounded AI
investigation orchestrator:

- repository orientation and prioritized target selection;
- model-authored AST tool requests with trusted scope fields forbidden;
- correlated tool-result, trace, error, and budget envelopes;
- continue, propose-rule, no-rule, and stop decisions;
- cited conclusive no-rule results that remain distinct from insufficient evidence.

These are pure contracts, not an agent loop or MCP transport. A `propose_rule` decision does not
persist or approve anything; it only hands control to the separately validated proposal pipeline.

AST investigations emit the frozen `AstRuleProposal` schema version `2.0.0`. It requires canonical
rule text, observed behavior, separately classified product intent, structured rule facts, AST and
exact-source citations, confidence/uncertainty, and provider/model/prompt provenance. Extra fields
are forbidden, so approval state cannot be expressed by model output. Legacy `1.0.0`
`AiRuleProposal` remains available to existing claim-cluster synthesis and can be migrated only when
the caller supplies AST evidence, provider provenance, observed behavior, and all missing structured
facts explicitly.

Supporting citations carry an explicit implementation, product-intent, verification, exception, or
counterevidence role plus the proposal fields they support. The pure validator rejects duplicate or
cross-scope citations, disallowed roles, incomplete field coverage, missing implementation evidence,
unsupported observed-intent claims, and AI assertions that a candidate has already been reviewed or
approved. It performs no database or authorization checks; those remain at the application boundary.

`ruleatlas_ai.providers.ast_agent_capabilities` describes model suitability independently of any
provider SDK. It covers structured-output strength, serial and parallel tool calls, context/output
limits, deterministic temperature, streaming, local/remote execution governance, and comparable
cost metadata. Compatibility evaluation treats unknown required capabilities as blockers, enforces
local-only and cost policies, and never upgrades discovery hints into unprobed capabilities.

The AI-to-claims adapter reruns pure citation validation before producing a
`ValidatedAstProposalInput`. It adds a deterministic proposal fingerprint and validator identity;
the claims package then normalizes it without importing the AI package, preserving the dependency
direction.

## Responsibility

| Belongs here | Does **not** belong here |
| --- | --- |
| OpenAI-compatible client + retries | Persisting connections/secrets (DB/SSM) → `apps/api` |
| Connection config, capability probing | Route handlers → `apps/api` |
| AI governance (local-only/budget/allowed-models/license) | Producing heuristic candidates → `ruleatlas-extraction` |
| Claim-cluster → candidate-rule synthesis | Clustering/graph algorithms → `ruleatlas-claims` |
| Structural provider adapters (Semgrep, semantic) that emit claims | — |

## Dependency position

```
ruleatlas-contracts ─┐
ruleatlas-claims ────┴─▶ ruleatlas-ai  (+ httpx) ─▶ consumed by apps/api
```

**Boundary rule:** imports `ruleatlas-contracts`, `ruleatlas-claims`, and `httpx`. The **secret store** and
DB persistence are injected by `apps/api` (this package defines interfaces, the app supplies SSM/vault).

## Target contents (migration map)

| Target module (here) | Moves from (`apps/api/src/ruleatlas/…`) |
| --- | --- |
| `client/` | `application/ai/openai_client.py`, `budget.py` |
| `governance.py` | `application/ai/governance.py` |
| `connections/` | `application/ai_providers/*` (`connection_service.py`, `connection_*`, `openai_compatibility_probe.py`, `openai_adapter.py`) |
| `synthesis/` | `application/ai_synthesis/*` (`workflow.py`, `rule_persistence.py`, `synthesis_wording.py`) — note `structured_semantics.py` moved to `ruleatlas-claims` |
| `providers/` | `infrastructure/providers/semgrep_adapter.py`, `semantic_providers.py` |
| `net/url_guard.py` | `infrastructure/net/url_guard.py` (SSRF guard; shared — may instead live in `contracts`) |

The former 795-LOC `connection_service.py` and 965-LOC `openai_compatibility_probe.py` have already been
split (into `connection_bootstrap.py`, `openai_probe_payloads.py`, `openai_probe_diagnostics.py`, etc.) and
move in as the smaller modules.

## Synthesis is language-agnostic (multi-language example)

AI synthesis consumes **claim clusters** (from `ruleatlas-claims`), not source code — so it never sees a
language. Given the canonical cluster for *"invoices over $10,000 require manager approval"* (built from
Python + TypeScript + PHP implementation claims, a PHPUnit test, and a Gherkin scenario), synthesis produces
**one** candidate rule that cites all of them as evidence:

```text
Synthesized rule (status = NEEDS_REVIEW):
  "An invoice whose total exceeds $10,000 must receive manager approval before it can be submitted."
  evidence: billing/approvals.py:2, src/billing/approvals.ts:3, src/Billing/Approvals.php:4,
            tests/ApprovalsTest.php (verification), features/invoice_approval.feature (product intent)
```

The cross-language corroboration *raises reviewer confidence* but never auto-approves — synthesized rules
always land as `NEEDS_REVIEW`. Structural provider adapters (Semgrep, GA for Python/PHP/TypeScript) that live
here emit the same `ClaimDraft` shape, so adding a language means adding a provider, not changing synthesis.

## Development

```bash
cd packages/ai
uv sync --extra dev
python -m pytest && python -m mypy src && python -m ruff check src tests
```
