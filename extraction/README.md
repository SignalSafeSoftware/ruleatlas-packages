# ruleatlas-extraction

**Rule-candidate extraction.** Turns source files, BDD specs, comments, and docs into **candidate claims**
(never confirmed rules), each carrying evidence (path + line range + snippet) and a capped confidence.

> Status: **scaffold** — initialized and importable; no logic migrated yet.

## Responsibility

This is the heuristic/text-first extraction layer. Per the project's rules, AI/heuristic extraction creates
*candidate* claims that must be tied to evidence and provenance — this package owns that step.

| Belongs here | Does **not** belong here |
| --- | --- |
| Heuristic keyword/regex candidate extraction | Persisting rules/claims (DB) → `apps/api` |
| BDD (`Given/When/Then`) claim extraction | AI enrichment / synthesis → `ruleatlas-ai` |
| Comment/docstring classification | Clustering/conflict/gap analysis → `ruleatlas-claims` |
| Scaffold vs. real-logic filtering | File discovery/typing → `ruleatlas-discovery` |

## Dependency position

```
ruleatlas-contracts ─┐
ruleatlas-discovery ─┴─▶ ruleatlas-extraction ─▶ (consumed by apps/api worker)
```

**Boundary rule:** may import `ruleatlas-contracts` and `ruleatlas-discovery` only. Must not import `claims`,
`ai`, `exports`, persistence, or API code.

## Target contents (migration map)

| Target module (here) | Moves from (`apps/api/src/ruleatlas/…`) |
| --- | --- |
| `heuristic/` | `infrastructure/extraction/heuristic_extractor.py`, `file_reader.py`, `service.py`, `rule_writer.py` (writer split: DTO-out here, DB-write stays in app) |
| `scaffold/` | `application/extraction/scaffold_classify.py`, `scaffold_markers.py`, `scaffold_filter.py` |
| `comments/` | `application/extraction/comment_classifier.py` |
| `bdd/` | `application/bdd/bdd_claims.py` |
| `schemas.py` | `application/extraction/schemas.py` (`ExtractionCandidate`, `ExtractionEvidence`) |

Note: the current extractor is language-neutral text processing plus per-language import/test regexes; those
regex catalogs move here intact. This package is the natural home for a future Semgrep/tree-sitter structural
candidate provider (see the decomposition doc).

## Public API

`ruleatlas_extraction.__all__` — the extractor entry points and candidate schemas. Scaffold exports
`__version__` only.

## Development

```bash
cd packages/extraction
uv sync --extra dev
python -m pytest && python -m mypy src && python -m ruff check src tests
```
