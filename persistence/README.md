# ruleatlas-persistence

**The database ring.** SQLAlchemy ORM models, the declarative `Base`, column/mixin helpers, and the
`sqlphilosophy`-based repositories — the single shared persistence layer that every context reads and writes
through. It exists so the context packages depend on *one* persistence package instead of reaching back into
`apps/api`.

> Status: **partially migrated.** In (verified: full suite 1319, docker builds): the declarative `Base`,
> `mixins`, `enum_column`, **all ORM models** (85 tables), and `append_only`. Pending: the `repositories/` +
> `RepositoryFactory` (Step 3). Back-compat shims remain at `ruleatlas.infrastructure.db.*`. See the migration
> plan below and [`docs/architecture/package-decomposition.md`](../../docs/architecture/package-decomposition.md).

## Why this package exists (the enabler)

Every remaining un-extracted context — `ai`, `extraction`, `demo`, `discovery`, and the ORM-coupled remainder
of `claims`/`exports` — imports `infrastructure.db.models` (ORM types) and `infrastructure.db.repositories`
(the `RepositoryFactory`). A context can't move into a package while that import points at `apps/api`, because
the package would then depend on the app (a cycle). Extracting the ORM layer into `ruleatlas-persistence`
gives those contexts a **package** to depend on, which unblocks moving all of them. It is the last structural
prerequisite for "filling the packages."

## Responsibility

| Belongs here | Does **not** belong here |
| --- | --- |
| SQLAlchemy declarative `Base` + registry | Engine / `SessionLocal` wiring (needs app config → stays in `apps/api`) |
| All ORM models (`core`, `scanning`, `rules`, `ai`, `graph_claims`, `tickets`) | Business logic / services / orchestration → context packages / `apps/api` |
| `enum_column` helpers, `TimestampMixin`, `now_utc`/`uuid_str` | FastAPI routes, request/response schemas → `apps/api` |
| `sqlphilosophy` repositories + `RepositoryFactory` | Alembic migrations (env + versions) → stay in `apps/api` |
| Append-only audit event listeners | Anything that imports an `application`/`api` module |

### Why `session` stays in `apps/api`

`session.py` builds the engine from `settings.database_url` (application configuration) and owns the
FastAPI request-scoped `get_session`. Those are composition-root concerns, so the session module stays in the
app and imports `Base`/models from this package — not the other way around.

## Dependency position

```
ruleatlas-contracts ─▶ ruleatlas-persistence ─▶ consumed by claims · ai · extraction · exports · discovery · demo · apps/api
                        (+ SQLAlchemy, sqlphilosophy)
```

**Boundary rule (hard):** imports `ruleatlas-contracts` + SQLAlchemy + `sqlphilosophy` only. It must never
import `ruleatlas.application.*` or `ruleatlas.api.*`. Two current db→app back-edges are resolved as part of
the migration (see below) so this rule holds.

## The schema is source-language-agnostic

A `Rule`, `SourceClaim`, or `RuleEvidence` row is identical whether the evidence came from Python, TypeScript,
PHP, Java, C#, Go, Ruby, or a Gherkin feature — the language only survives as data (`source_path`,
`EvidenceSourceType`), never as schema. That is what lets a single persistence layer back every language RuleAtlas
scans. Example: the "invoices over $10,000 require manager approval" rule is one `Rule` row with several
`RuleEvidence` rows (`billing/approvals.py`, `approvals.ts`, `Approvals.php`, `ApprovalsTest.php`,
`invoice_approval.feature`) — the table shape doesn't change per language.

## Migration map (what moves in)

| Target (here) | Moves from (`apps/api/src/ruleatlas/infrastructure/db/…`) |
| --- | --- |
| `base.py` | `base.py` (declarative `Base`) |
| `mixins.py`, `enum_column.py` | `mixins.py`, `enum_column.py` |
| `models/` | `models/` (`_base`, `core`, `scanning`, `rules`, `ai`, `graph_claims`, `tickets`) |
| `repositories/` | `repositories/` (~55 repos + `factory.py`) |
| `append_only.py` | `append_only.py` (already relocated into the db layer) |
| `query/inventory_keyword.py` | `application/scanning/discovery_inventory_keyword.py` (it's a `SourceFile` query helper) |

**Stays in `apps/api`:** `session.py` (engine/`SessionLocal`), `alembic/` (env + versions).

### Back-edges resolved during the move

- `session → application.audit.append_only` — ✅ already fixed (`append_only` now lives in the db layer).
- `discovery_inventory_query_builder → application.scanning.discovery_inventory_keyword` — the keyword helper is a
  `SourceFile`/SQLAlchemy query concern and moves **into** this package.
- `analysis_version_compare_query_builder → application.analysis` — a **type-only** (`TYPE_CHECKING`) import;
  resolved with a forward-ref / kernel DTO.

### How the move stays safe

The models/repositories relocate together (so the SQLAlchemy registry + relationships stay intact), enum
imports repoint to `ruleatlas_contracts.enums`, and **back-compat shims** are left at
`ruleatlas.infrastructure.db.*` so the hundreds of existing importers keep working. Alembic's `env.py` imports
`Base` (via the shim) so `Base.metadata` still sees every table. Verification: full backend suite + a docker
image build before the shims are later removed.

## Development

```bash
cd packages/persistence
uv sync --extra dev
python -m pytest && python -m mypy src && python -m ruff check src tests
```
