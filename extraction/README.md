# ruleatlas-extraction

Provider-neutral extraction contracts and BDD ingestion for RuleAtlas.

Business-rule generation is intentionally absent. RuleAtlas builds and persists
tree-sitter ASTs, exposes bounded investigation tools, and asks the configured AI
provider to propose cited candidate rules. Human review remains mandatory.

## Responsibility

| Belongs here | Does **not** belong here |
| --- | --- |
| Candidate and evidence transfer schemas | Source-pattern or comment-pattern rule generation |
| BDD/Gherkin parsing and step linking | AST persistence and MCP investigation tools |
| BDD claim normalization | AI provider calls and governance |
| Provider-neutral validation | Database orchestration and review workflows |

## Development

```bash
cd extraction
uv sync --extra dev
python -m pytest
python -m mypy src
python -m ruff check src tests
```
