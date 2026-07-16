# ruleatlas-demo

**Demo / seed data generators — development only.** Depends on everything; **nothing depends on it**.
Intended to be installed only as an optional dev/demo extra of `apps/api`, never in a production image.

> Status: **scaffold** — initialized and importable; no logic migrated yet.

## Why isolate this first

`application/demo/` is ~5,088 LOC today — the single biggest non-runtime chunk in the core package
(`seed_invoice_analysis.py` alone is 1,082 LOC). Because no runtime code depends on it, extracting it is the
**lowest-risk, highest-relief** move in the whole decomposition: it shrinks the production surface with zero
behavior change.

## Responsibility

| Belongs here | Does **not** belong here |
| --- | --- |
| Demo/sample project seeding | Anything imported by the running app at request/scan time |
| Demo org/user/AI-provider seeding | Test fixtures required by unit tests (keep with their tests) |
| Seed orchestration | Migrations (Alembic) → `apps/api` |

## Dependency position

```
contracts · discovery · extraction · claims · ai · exports
                         │ (all)
                         ▼
                   ruleatlas-demo        ← nothing imports this
                         │
                         ▼ (optional extra only)
                     apps/api[demo]
```

**Boundary rule:** may import any `ruleatlas-*` package. The inverse is forbidden — a CI guard should fail if
any runtime package imports `ruleatlas_demo`.

## What the seed demonstrates (multi-language on purpose)

The invoice-analysis demo seeds a **deliberately multi-language** sample project so reviewers can see the
whole pipeline light up: the *"invoices over $10,000 require manager approval"* rule is planted as Python and
TypeScript implementation, a PHP service, a PHPUnit test, and a Gherkin feature. Seeding that spread is what
exercises cross-language clustering (`ruleatlas-claims`), conflict/gap detection (e.g. a seeded threshold
mismatch across languages), and synthesis (`ruleatlas-ai`) end-to-end — offline, with no network or AI
credentials required by default.

## Target contents (migration map)

| Target module (here) | Moves from (`apps/api/src/ruleatlas/application/demo/…`) |
| --- | --- |
| `seed_orchestrator.py` | `seed_demo_orchestrator.py` |
| `invoice_analysis.py` | `seed_invoice_analysis.py` |
| `ai_providers.py` | `seed_demo_ai_providers.py` |
| `auth_seed.py` | `demo_auth_seed.py` |
| … | remaining `application/demo/*` |

DB writes performed by seeding stay behind interfaces provided by `apps/api` (this package builds the data;
the app commits it), so `ruleatlas-demo` itself stays free of a hard SQLAlchemy dependency where practical.

## Development

```bash
cd packages/demo
uv sync --extra dev
python -m pytest && python -m mypy src && python -m ruff check src tests
```
