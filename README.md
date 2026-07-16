# RuleAtlas packages

Installable packages extracted from the `apps/api` backend to make the codebase maintainable via small,
enforceable, acyclic boundaries. Full plan: [`docs/architecture/package-decomposition.md`](../docs/architecture/package-decomposition.md).

> Status: **scaffolding**. The packages below (except `discovery-core`) are initialized shells — importable
> and buildable, but no production code has moved into them yet.

## Layout

```
packages/
├── contracts/       ruleatlas-contracts   — shared kernel (enums, value objects, provider/claim contracts)
├── discovery-core/  ruleatlas-discovery   — file typing, globbing, line metrics, dir tree  (already extracted)
├── extraction/      ruleatlas-extraction  — heuristic/BDD/comment candidate extraction
├── claims/          ruleatlas-claims      — rule IR: claims, graph, clustering, conflicts, gaps
├── ai/              ruleatlas-ai          — AI providers, governance, cluster→candidate-rule synthesis
├── exports/         ruleatlas-exports     — report/CSV/artifact builders
└── demo/            ruleatlas-demo        — dev-only demo/seed generators (nothing depends on it)
```

## Dependency direction (no cycles)

```
apps/api ─▶ {ai, extraction, claims, exports, discovery} ─▶ contracts   (kernel: no deps)
demo ─▶ everything ; nothing ─▶ demo
```

## Conventions

- Standalone **hatchling** packages, `src/ruleatlas_<name>/` layout, PEP 561 typed (`py.typed`).
- Managed with **uv** for standalone dev; consumed by `apps/api` as Poetry editable path deps.
- Python ≥ 3.12, ruff (line-length 120), mypy strict, pytest.
- Each package: `pyproject.toml`, `src/`, `README.md` (responsibility + module map + boundary rules), `tests/`.

## Working on a package

```bash
cd packages/<name>
uv sync --extra dev
python -m pytest && python -m mypy src && python -m ruff check src tests
```
