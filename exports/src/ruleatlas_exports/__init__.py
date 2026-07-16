"""RuleAtlas exports: report and artifact builders.

Pure rendering of analysis outputs into user-facing artifacts — Markdown/CSV/JSON reports for discovery
inventories, analysis results, and version comparisons. Given already-computed data (from ``apps/api``),
this package formats it; it does not query the database or call services itself.

Security note: CSV/spreadsheet outputs go through formula-injection sanitization (the ``sanitize_csv_cell``
helper) — that safety utility moves here with the builders.

Boundary: depends only on ``ruleatlas-contracts``. No DB, HTTP, or other ``ruleatlas-*`` packages.

Status: SCAFFOLD. See ``README.md`` and ``docs/architecture/package-decomposition.md``.
"""

from __future__ import annotations

from ruleatlas_exports.version import __version__

__all__: list[str] = ["__version__"]
