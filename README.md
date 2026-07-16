# RuleAtlas packages

Installable packages extracted from the `apps/api` backend to make the codebase maintainable via small,
enforceable, acyclic boundaries. Full plan: [`docs/architecture/package-decomposition.md`](../docs/architecture/package-decomposition.md).

## Status

| Package | State |
| --- | --- |
| `contracts` | **extracted / in use** — enums, `ClaimDraft`, provider contracts, classification, authorization |
| `discovery-core` | **extracted / in use** — file typing, globbing, metrics, dir tree |
| `persistence` | **partially migrated** — `Base` + mixins + `enum_column` + all ORM models + `append_only` extracted (verified); `repositories/` + `RepositoryFactory` pending (Step 3) |
| `exports` | **partially migrated** — pure core (`csv_safety`, `export_labels`, `markdown_builder`, `report_types`) extracted; ORM builders pending persistence |
| `claims` | **partially migrated** — ORM-free logic (`confidence_scorer`, `relationship_suggester`, `text_normalize`) extracted; ORM parts pending persistence |
| `extraction` · `ai` · `demo` | **scaffold** — initialized/importable; migration pending persistence |

## Layout

```
packages/
├── contracts/       ruleatlas-contracts   — shared kernel (enums, value objects, provider/claim contracts)
├── discovery-core/  ruleatlas-discovery   — file typing, globbing, line metrics, dir tree
├── persistence/     ruleatlas-persistence — SQLAlchemy models, repositories, Base (the shared DB layer)
├── extraction/      ruleatlas-extraction  — heuristic/BDD/comment candidate extraction
├── claims/          ruleatlas-claims      — rule IR: claims, graph, clustering, conflicts, gaps
├── ai/              ruleatlas-ai          — AI providers, governance, cluster→candidate-rule synthesis
├── exports/         ruleatlas-exports     — report/CSV/artifact builders
└── demo/            ruleatlas-demo        — dev-only demo/seed generators (nothing depends on it)
```

## Dependency direction (no cycles)

```
apps/api ─▶ {ai, extraction, claims, exports, discovery, persistence} ─▶ contracts   (kernel: no deps)
{claims, ai, extraction, exports, demo} ─▶ persistence   (shared ORM layer; session/config stays in apps/api)
demo ─▶ everything ; nothing ─▶ demo
```

## The multi-language thread

RuleAtlas scans codebases in **Python, TypeScript/TSX, PHP, Java, C#, Go, and Ruby** (plus language-agnostic
BDD/Gherkin and config files). The packages are split so that **only the edges know about languages** and the
core is language-neutral:

- **`discovery`** knows file extensions, test-name patterns, and comment styles per language.
- **`extraction`** has per-language recognition regexes but emits a uniform `ClaimDraft`.
- **`contracts`** defines that `ClaimDraft` — the point where language differences disappear.
- **`claims`** clusters/reconciles claims across languages without branching on language at all.
- **`ai`**, **`exports`** operate purely on claims/clusters — never on source syntax.

A single worked rule — *"invoices over $10,000 require manager approval"* — is threaded through every package
README to show this: it is recognized in Python/TS/PHP/PHPUnit/Gherkin, normalized to one shape, clustered
into one canonical rule, synthesized once, and reported with cross-language evidence. Adding a new language is
a `discovery` + `extraction` change only; `contracts`/`claims`/`ai`/`exports` are untouched. See the
[UAST appendix](../docs/architecture/package-decomposition.md#appendix-language-independent-ast) for why this
claim-level normalization is preferred over a universal syntax tree.

## Conventions

- Standalone **hatchling** packages, `src/ruleatlas_<name>/` layout, PEP 561 typed (`py.typed`).
- Managed with **uv** for standalone dev; consumed by `apps/api` as Poetry editable path deps.
- Python ≥ 3.12, ruff (line-length 120), mypy strict, pytest.
- Each package: `pyproject.toml`, `src/`, `README.md` (responsibility + module map + boundary rules + language
  examples where relevant), `tests/`.

## Working on a package

```bash
cd packages/<name>
uv sync --extra dev
python -m pytest && python -m mypy src && python -m ruff check src tests
```
