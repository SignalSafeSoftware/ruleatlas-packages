# ruleatlas-persistence

**The database ring.** SQLAlchemy ORM models, the declarative `Base`, column/mixin helpers, and the
`sqlphilosophy`-based repositories — the single shared persistence layer that every context reads and writes
through. It exists so the context packages depend on *one* persistence package instead of reaching back into
`apps/api`.

> Status: **fully migrated** (verified: package standalone ruff + mypy 76 files + pytest; apps/api mypy 446 +
> import-linter 5/0; full suite 1319 passed; docker image builds; container resolves 85 tables). In: the
> declarative `Base`, `mixins`, `enum_column`, **all ORM models** (85 tables), `append_only`, the
> `inventory_keyword` query helper, and **all ~55 `repositories/` + `RepositoryFactory`**. Back-compat shims
> remain at `ruleatlas.infrastructure.db.*` (models, repositories, base, mixins, enum_column, append_only) and
> `ruleatlas.shared.enum_utils` so existing importers keep working until the Phase-5 shim sweep. See
> [`docs/architecture/package-decomposition.md`](../../docs/architecture/package-decomposition.md).

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

| Target (here) | Moved from (`apps/api/src/ruleatlas/…`) | Status |
| --- | --- | --- |
| `base.py` | `infrastructure/db/base.py` (declarative `Base`) | ✅ |
| `mixins.py`, `enum_column.py` | `infrastructure/db/mixins.py`, `enum_column.py` | ✅ |
| `models/` | `infrastructure/db/models/` (`_base`, `core`, `scanning`, `rules`, `ai`, `graph_claims`, `tickets`) | ✅ |
| `repositories/` | `infrastructure/db/repositories/` (~55 repos + `factory.py` + `export_report`/`discovery_inventory` query builders) | ✅ |
| `append_only.py` | `infrastructure/db/append_only.py` | ✅ |
| `inventory_keyword.py` | `application/scanning/discovery_inventory_keyword.py` (a `SourceFile` query helper) | ✅ |

`enum_value` (a pure enum→str coercion helper the repositories used) moved to the kernel at
`ruleatlas_contracts.enum_utils` (shim left at `ruleatlas.shared.enum_utils`).

**Stays in `apps/api`:** `session.py` (engine/`SessionLocal`), `alembic/` (env + versions), and
`analysis_version_compare_query_builder` (it flattens the app-level `AnalysisVersionCompareResult` DTO into
export rows in 5 methods — an app/export concern, not a pure repository, so it moved to
`application/analysis/` instead of into this package).

### Back-edges resolved during the move

- `session → application.audit.append_only` — ✅ fixed (`append_only` lives in this package).
- `discovery_inventory_query_builder → application.scanning.discovery_inventory_keyword` — ✅ the keyword helper is a
  `SourceFile`/SQLAlchemy query concern and moved **into** this package (`inventory_keyword.py`).
- `analysis_version_compare_query_builder → application.analysis` — ✅ removed by keeping that builder in the app
  (it's app-DTO-coupled), so no db→app edge remains.

Result: the package imports **only** `ruleatlas-contracts` + SQLAlchemy + `sqlphilosophy` — verified by the
package's own CI job (`uv run mypy src`, which fails on any leaked `ruleatlas.application`/`ruleatlas.api` import).
`sqlphilosophy` is pinned `>=0.1.8,<0.2.0` to match `apps/api` (0.2.0 changed the `RepositoryFactory` protocol).

### How the move stayed safe

The models + repositories relocated **together** (so the SQLAlchemy registry + relationships stay intact), enum
imports repointed to `ruleatlas_contracts.enums`, and **back-compat shims** remain at
`ruleatlas.infrastructure.db.*` so the hundreds of existing importers keep working. Alembic's `env.py` imports
`Base` (via the shim) so `Base.metadata` still sees every table. Verified with the full backend suite (1319
passed) + a docker image build + a container smoke resolving all 85 tables before the Phase-5 shim removal.

## Development

```bash
cd packages/persistence
uv sync --extra dev
python -m pytest && python -m mypy src && python -m ruff check src tests
```
