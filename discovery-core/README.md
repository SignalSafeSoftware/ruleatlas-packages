# ruleatlas-discovery

Database-agnostic Python helpers for discovery scanning: file type mapping, glob matching, line-count aggregation, and directory tree construction.

This package is extracted from [RuleAtlas](https://github.com/ruleatlas/ruleatlas) for reuse in other tools. It does **not** include auth, tenancy, scan lifecycle, or API route logic.

## Install (monorepo path)

```bash
cd apps/api && poetry install
```

## Standalone development

```bash
cd packages/discovery-core
pip install -e ".[dev]"
python -m pytest
python -m build
```

## Public API

See `ruleatlas_discovery.__all__` and `docs/architecture/discovery-package-extraction.md`.
