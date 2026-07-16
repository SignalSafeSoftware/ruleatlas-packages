# ruleatlas-discovery

**Database-agnostic discovery scanning primitives.** File-type mapping, glob matching, line-count/comment
metrics, and directory-tree construction — the first pass that turns a checked-out repository into a typed,
classified inventory. Extracted from [RuleAtlas](https://github.com/ruleatlas/ruleatlas) for reuse; it
contains **no** auth, tenancy, scan lifecycle, or API-route logic.

> Status: **extracted / in use** — the original discovery package (already migrated) that set the convention
> the other packages follow.

## Responsibility

| Belongs here | Does **not** belong here |
| --- | --- |
| Extension → language/type mapping (`.py` → Python, `.ts` → TypeScript, …) | DB persistence of scan runs / files → `apps/api` |
| Test/scaffold/vendor glob classification (`test_*.py`, `*.test.ts`, …) | Scan orchestration, tenancy, auth → `apps/api` |
| Line-count, comment-style, and blank-line metrics | Rule/claim extraction → `ruleatlas-extraction` |
| Directory-tree + top-directory aggregation | HTTP routes → `apps/api` |

## Dependency position

```
ruleatlas-contracts ─▶ ruleatlas-discovery ─▶ consumed by extraction, exports, apps/api
```

**Boundary rule:** imports `ruleatlas-contracts` + stdlib only. No DB, HTTP, or other `ruleatlas-*` packages.

## Multi-language file typing

Discovery is where language awareness lives. The built-in mapping table (`builtin_mappings.py`) classifies
source, test, config, and generated/vendor files across the supported matrix. Examples:

| File | Language | `display_type` | Classification |
| --- | --- | --- | --- |
| `billing/approvals.py` | Python | Python source | backend code |
| `src/billing/approvals.ts` | TypeScript | TypeScript source | backend/frontend code |
| `src/components/Invoice.tsx` | TSX | React TSX | frontend code |
| `src/Billing/Approvals.php` | PHP | PHP source | backend code |
| `com/acme/Approvals.java` | Java | Java source | backend code |
| `Billing/Approvals.cs` | C# | C# source | backend code |
| `billing/approvals.go` | Go | Go source | backend code |
| `app/models/invoice.rb` | Ruby | Ruby source | backend code |

**Test detection is per-language** (so tests become `UNIT_TEST` evidence, not "product intent"):

| Pattern | Language | Meaning |
| --- | --- | --- |
| `test_*.py` / `*_test.py` | Python | pytest/unittest |
| `*.test.ts` / `*.spec.ts` | TypeScript | Jest/Vitest |
| `*.test.tsx` / `*.spec.tsx` | TSX | React component tests |
| `*Test.php` | PHP | PHPUnit |
| `*Tests.cs` / `*.Tests.cs` | C# | xUnit/NUnit |

**Comment style is per-language** too (used downstream by comment classification): `#` for Python/Ruby,
`//` + `/* */` for TypeScript/PHP/Java/C#/Go. This lets a single comment-classifier treat
`# invoices over 10k need approval` (Python) and `// invoices over 10k need approval` (TypeScript)
identically.

```python
from ruleatlas_discovery import classify_file  # illustrative; see __all__ for exact surface

classify_file("src/billing/approvals.ts")
# → language="TypeScript", display_type="TypeScript source", is_test=False, is_generated=False
classify_file("src/billing/approvals.test.ts")
# → language="TypeScript", is_test=True   → downstream evidence = UNIT_TEST
```

## Public API

See `ruleatlas_discovery.__all__` and `docs/architecture/discovery-package-extraction.md`.

## Development

```bash
cd packages/discovery-core
pip install -e ".[dev]"      # or: uv sync --extra dev
python -m pytest && python -m mypy src && python -m ruff check src tests
python -m build
```
