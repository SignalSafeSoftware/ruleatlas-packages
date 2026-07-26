# Package plan for AST/MCP/AI business-rule discovery

Status: proposed  
Primary repository: `ruleatlas-packages`  
Companion application plan: `ruleatlas/docs/roadmap/ast-mcp-ai-rule-discovery-plan.md`

## Progress

| Work item | Status | Validation |
| --- | --- | --- |
| `PKG-AST-001` AST enums and source ranges | Complete | Ruff, formatting, strict mypy, pytest, and package build passed |
| `PKG-AST-002` normalized AST records | Complete | Included in the same 42-test contracts gate |
| `PKG-AST-003` versioned AST citations | Complete | Included in the 56-test contracts gate |
| `PKG-AST-004` AST persistence models | Complete | Ruff, strict mypy, 15 persistence tests, and package build passed |
| `PKG-AST-005` AST write repositories | Complete | Ruff, strict mypy, 21 persistence tests, and package build passed |
| `PKG-AST-006` scoped AST read repositories | Complete | Ruff, strict mypy, 30 persistence tests, and package build passed |
| `PKG-AST-007` AST lifecycle and retention | Complete | Ruff, strict mypy, 34 persistence tests, and package build passed |
| `PKG-MCP-001` AST MCP tool schemas | Complete | Ruff, strict mypy, 63 contracts tests, and package build passed |
| `PKG-MCP-002` investigation budgets and outcomes | Complete | Ruff, strict mypy, 75 contracts tests, and package build passed |
| `PKG-AI-001` AST investigation step contracts | Complete | Ruff, strict mypy, 21 AI tests, and package build passed |
| `PKG-AI-002` AST-cited rule proposal schema | Complete | Ruff, strict mypy, 33 AI tests, and package build passed |
| `PKG-AI-003` pure AST proposal citation validation | Complete | Ruff, strict mypy, 43 AI tests, and package build passed |
| `PKG-AI-004` AST agent provider capabilities | Complete | Ruff, strict mypy, 52 AI tests, and package build passed |
| `PKG-CLAIMS-001` normalize validated AST proposals | Complete | Ruff, strict mypy, 15 claims tests, 53 AI tests, and both package builds passed |
| `PKG-CLAIMS-002` score AST-backed evidence | Complete | Ruff, strict mypy, 26 claims tests, and package build passed |
| `PKG-CLEAN-001` remove heuristic generation | Gated | Do not start until application comparison, scale, security, and rollback gates pass |

## 1. Purpose

This plan defines the reusable package work required for RuleAtlas to replace heuristic business-rule
generation with AI investigation of persisted tree-sitter ASTs through MCP.

The package repository owns stable contracts, persistence structures, repositories, provider-neutral
AI contracts, and validation logic. The application repository owns tree-sitter runtime integration,
worker orchestration, MCP transport, provider execution, APIs, and UI.

## 2. Package ownership boundaries

### `contracts`

Own:

- normalized AST DTOs and enums;
- parse outcome and capability contracts;
- AST citation and source-range contracts;
- MCP tool input/output DTOs that must be provider neutral;
- extraction mode and outcome vocabulary where shared.

Must not own:

- SQLAlchemy;
- tree-sitter runtime objects;
- FastAPI;
- worker/job implementation;
- provider credentials.

### `persistence`

Own:

- AST ORM models;
- AST repositories and query primitives;
- scoped lifecycle/delete operations;
- indexes and repository-level pagination;
- links between AST nodes, source files, graph nodes, evidence, and analysis versions.

Must not own:

- Alembic migration files;
- tree-sitter parser invocation;
- MCP transport;
- provider calls.

### `ai`

Own:

- investigation step and result schemas;
- provider-neutral tool-call contracts;
- citation-backed rule proposal schema;
- proposal and citation validation primitives;
- prompt/version metadata contracts;
- model capability requirements for AST tool use.

Must not own:

- organization secret resolution;
- HTTP route authentication;
- project database authorization;
- scan orchestration.

### `claims`

Own:

- deterministic normalization and deduplication of validated proposals;
- claim/rule comparison helpers;
- confidence inputs for AST-backed evidence;
- graph/claim utilities that are independent of application services.

Must not generate business rules from heuristic source patterns after migration.

### `extraction`

Transition options:

1. Rename/reframe as a parser-neutral extraction-contract package; or
2. Deprecate it after AST and AI contracts move to `contracts` and `ai`.

Recommended: retain BDD/Gherkin ingestion and generic candidate interfaces only if they remain
provider-neutral evidence ingestion. Remove heuristic rule generation and comment-pattern
classification.

## 3. Dependency rules

Target import direction:

```text
contracts
  <- persistence
  <- claims
  <- ai

extraction (if retained)
  -> contracts only
```

Additional rules:

- `contracts` remains dependency-light and model-free.
- `persistence` may import contracts but not AI provider implementations.
- `ai` may import contracts and pure proposal-validation helpers.
- `claims` must not import application services.
- No package imports from the `ruleatlas` monorepo.
- AST DTOs must not expose tree-sitter `Node`, `Tree`, or `Language` objects.

## 4. Shared AST model

### AST parse run

Required fields:

- ID;
- project ID;
- analysis version ID;
- scan run ID;
- provider/parser key and version;
- status;
- files attempted/succeeded/failed/unsupported/reused;
- node count;
- error count;
- start/end timestamps;
- summary metadata.

### AST document

Required fields:

- ID;
- project ID;
- analysis version ID;
- scan run ID;
- source file ID;
- normalized path;
- language key;
- grammar key/version;
- content hash;
- root node ID;
- node count;
- parse/error status;
- source byte count;
- parse duration;
- created timestamp.

Uniqueness:

- one authoritative document per source file and analysis version;
- content hash may be shared for reuse, but tenant/version ownership remains explicit.

### AST node

Required fields:

- ID;
- AST document ID;
- parent node ID;
- sibling ordinal;
- tree-sitter raw node type;
- normalized category, when available;
- field name;
- named, extra, error, missing, and changed flags where supported;
- start/end byte;
- start/end row and column;
- subtree hash;
- optional display/name hint;
- compact attributes JSON for language-specific metadata.

Do not store source text on every node.

### AST link

Optional but recommended fields:

- AST node ID;
- graph node ID, source symbol ID, evidence ID, or another AST node ID;
- link type;
- resolution type;
- confidence;
- resolver key/version;
- attributes.

## 5. Work items and commits

Each item is a bounded implementation prompt and normally one commit.

### Package phase 1 — contracts

#### PKG-AST-001 — Define AST enums and source ranges

Add:

- parse statuses;
- node flags/categories;
- link and resolution types;
- immutable byte/point/source-range DTOs;
- validation for ordered ranges and non-negative offsets.

Likely files:

- `contracts/src/ruleatlas_contracts/ast/`
- `contracts/tests/`
- package exports and README

Estimate:

- 5–7 files;
- 350–550 lines.

Acceptance:

- DTOs serialize deterministically.
- Invalid ranges fail with stable errors.
- No parser/runtime dependency is introduced.

Commit: `feat(contracts): define normalized AST primitives`

#### PKG-AST-002 — Define normalized AST records

Add:

- parse-run record;
- document record;
- node record;
- link record;
- structural capability and parse-summary contracts.

Estimate:

- 4–6 files;
- 350–600 lines.

Acceptance:

- Records can represent all currently supported tree-sitter grammars.
- Raw language-specific node types remain available.
- Contracts do not claim semantic resolution that tree-sitter did not provide.

Commit: `feat(contracts): define normalized syntax tree records`

#### PKG-AST-003 — Define AST citations

Add:

- document/node citation;
- exact source citation;
- content and subtree hash;
- analysis-version ownership;
- citation validation result vocabulary.

Estimate:

- 4–6 files;
- 250–450 lines.

Acceptance:

- A citation identifies one immutable source region.
- Cross-version identity cannot be ambiguous.

Commit: `feat(contracts): define versioned AST citations`

### Package phase 2 — persistence

#### PKG-AST-004 — Add AST ORM models

Add models for:

- parse runs;
- documents;
- nodes;
- links.

Likely files:

- `persistence/src/ruleatlas_persistence/models/ast.py`
- model exports;
- model metadata tests.

Estimate:

- 4–6 files;
- 500–800 lines.

Acceptance:

- Foreign keys preserve project/analysis/source relationships.
- Required indexes and uniqueness constraints are declared.
- Large node attributes use compact JSON and sane defaults.

Commit: `feat(persistence): add AST models`

#### PKG-AST-005 — Add AST write repositories

Operations:

- create/complete/fail parse run;
- add document;
- bulk insert nodes;
- assign root;
- replace document;
- add links;
- delete by document/version/project according to explicit scope.

Estimate:

- 5–8 files;
- 550–900 lines.

Acceptance:

- Bulk operations avoid one statement per node.
- All destructive operations require narrow explicit identifiers.
- Repository methods do not commit implicitly unless package convention requires it.

Commit: `feat(persistence): add AST write repositories`

#### PKG-AST-006 — Add AST read repositories

Operations:

- document lookup by project/version/file;
- node lookup in scope;
- parent/children pagination;
- bounded descendants;
- nodes by type/range;
- containing node;
- definitions and normalized categories;
- links by node and relationship.

Estimate:

- 6–9 files;
- 700–1,100 lines.

Acceptance:

- Queries are tenant/version scoped.
- Child ordering is stable.
- No recursive query can return unbounded rows.
- Query-count tests cover navigation and search.

Commit: `feat(persistence): add scoped AST queries`

#### PKG-AST-007 — Add lifecycle and retention operations

Operations:

- count and size by analysis version;
- delete expired versions;
- reuse metadata for unchanged content;
- preserve documents referenced by retained provenance;
- report orphaned links.

Estimate:

- 4–6 files;
- 350–600 lines.

Commit: `feat(persistence): manage AST lifecycle`

### Package phase 3 — MCP contracts

#### PKG-MCP-001 — Define AST MCP tool schemas

Define provider-neutral input/output schemas for:

- list files;
- get document;
- find nodes;
- get node;
- list children;
- get subtree;
- get symbol AST;
- source excerpt;
- callers/callees;
- conditions/assignments;
- related tests and BDD evidence.

Estimate:

- 6–10 files;
- 600–1,000 lines.

Acceptance:

- Every list response supports cursor pagination.
- Every response reports truncation.
- Scope is supplied by trusted context, not tool arguments.

Commit: `feat(contracts): define AST MCP schemas`

#### PKG-MCP-002 — Define investigation budgets and outcomes

Add:

- budget limits and consumption;
- partial/truncated/blocked/cancelled outcomes;
- tool error taxonomy;
- retryability;
- trace-safe result metadata.

Estimate:

- 4–6 files;
- 300–500 lines.

Commit: `feat(contracts): define MCP investigation budgets`

### Package phase 4 — AI investigation and proposals

#### PKG-AI-001 — Define investigation step contracts

Add:

- orientation result;
- target selection;
- model tool request;
- tool result envelope;
- investigation decision;
- stop reason;
- no-rule result.

Estimate:

- 5–8 files;
- 450–750 lines.

Commit: `feat(ai): define AST investigation contracts`

#### PKG-AI-002 — Extend the rule proposal schema

Require:

- canonical rule text;
- observed behavior;
- inferred product intent clearly distinguished;
- actor/condition/action/result/exception fields;
- AST citations;
- supporting evidence citations;
- confidence and uncertainty;
- provider/model/prompt schema versions.

Estimate:

- 4–7 files;
- 350–650 lines.

Acceptance:

- Legacy proposals can be migrated or versioned explicitly.
- Citation-free proposals fail validation.
- Auto-approval remains impossible in the schema.

Commit: `feat(ai): require AST-cited rule proposals`

#### PKG-AI-003 — Add pure citation validation

Validate:

- required fields;
- duplicate citations;
- range ordering;
- citation scope metadata;
- allowed evidence roles;
- proposal-to-citation completeness;
- unsupported claims such as approval assertions.

Database existence and tenant checks remain in the application layer.

Estimate:

- 5–8 files;
- 500–800 lines.

Commit: `feat(ai): validate AST-backed proposals`

#### PKG-AI-004 — Add provider capability requirements

Add capability vocabulary for:

- structured output;
- tool calls;
- parallel tool calls if permitted;
- maximum context/output;
- deterministic temperature support;
- streaming;
- local/remote governance;
- cost metadata.

Estimate:

- 3–5 files;
- 200–350 lines.

Commit: `feat(ai): describe AST agent model capabilities`

### Package phase 5 — claims and confidence

#### PKG-CLAIMS-001 — Normalize validated AST proposals

Changes:

- map validated proposals into canonical claims/rules;
- retain citation IDs and origin metadata;
- deduplicate without discarding distinct source behavior;
- distinguish observed implementation from inferred intent.

Estimate:

- 5–8 files;
- 450–750 lines.

Commit: `feat(claims): normalize AST-derived proposals`

#### PKG-CLAIMS-002 — Score AST-backed evidence

Changes:

- add AST/structural evidence inputs;
- ensure deterministic AST observations cannot confirm product intent alone;
- preserve human approval as the authority boundary;
- update explanations and tests.

Estimate:

- 4–6 files;
- 250–450 lines.

Commit: `feat(claims): score AST-backed evidence`

### Package phase 6 — heuristic retirement

Do not begin until the application repository passes comparison, scale, security, and rollback gates.

#### PKG-CLEAN-001 — Remove heuristic rule generation

Likely removals:

- `extraction/src/ruleatlas_extraction/heuristic_extractor.py`
- `extraction/src/ruleatlas_extraction/comment_classifier.py`
- heuristic-specific tests and exports

Likely retained:

- BDD/Gherkin parsing;
- generic evidence contracts;
- source candidate DTOs only if still used by non-heuristic importers.

Current direct production deletion is approximately 1,022 lines before tests/docs.

Acceptance:

- No package API can generate business-rule text from heuristic source matching.
- Removing the modules does not remove BDD evidence ingestion.
- Import-linter rules remain green.

Commit: `refactor(extraction): remove heuristic rule generator`

#### PKG-CLEAN-002 — Deprecate or reshape the extraction package

Decision:

- If remaining code is only BDD ingestion, rename package scope in documentation and exports.
- If generic extraction contracts have moved elsewhere, mark the package deprecated.
- Do not perform a package rename in the same commit as heuristic removal.

Commit: `refactor(extraction): narrow package responsibility`

#### PKG-CLEAN-003 — Refresh package documentation and changelogs

Changes:

- root README;
- contracts, persistence, AI, claims, and extraction READMEs;
- changelogs and version metadata;
- migration notes for downstream consumers.

Commit: `docs(packages): document AST AI contract migration`

## 6. Test plan

### Contracts

- deterministic serialization;
- invalid range rejection;
- schema compatibility;
- enum and default stability;
- payload truncation metadata.

### Persistence

- bulk node insertion;
- stable child ordering;
- project/version isolation;
- recursive/bounded traversal;
- range search;
- replacement and retention;
- cascade behavior;
- query counts;
- large-tree memory behavior.

### AI

- citation-required proposals;
- malformed tool calls;
- no-rule outcomes;
- budget-exceeded outcomes;
- provider capability mismatch;
- proposal schema-version compatibility;
- source observation versus product-intent separation.

### Claims

- proposal normalization;
- deduplication;
- distinct behavior preservation;
- AST evidence confidence;
- human-review boundary.

### Package gates

- Ruff;
- formatting;
- mypy;
- pytest;
- import-linter;
- build every package;
- install built wheels into a clean environment;
- verify no monorepo import leakage.

## 7. Compatibility and versioning

- AST contracts begin at schema version `1`.
- Rule proposal changes use an explicit schema version; do not silently reinterpret persisted traces.
- Additive package releases land before application consumption.
- Heuristic APIs receive a deprecation window during comparison mode.
- Removal requires a breaking-version note even if package versions remain pre-1.0.
- Historical persisted heuristic rules remain valid application data; removing generators does not
  invalidate their records.

## 8. Package-to-monorepo synchronization

For every package milestone:

1. Run all package gates.
2. Update the package validation report.
3. Commit package changes.
4. Record the exact package commit SHA.
5. Update every Git dependency in `ruleatlas/apps/api/pyproject.toml` to that same SHA.
6. Refresh `ruleatlas/apps/api/poetry.lock`.
7. Run monorepo API, worker, migration, and package-boundary tests.
8. Do not merge monorepo code that assumes unmerged package contracts.

Recommended synchronization points:

- S1 after `PKG-AST-004`: contracts and models;
- S2 after `PKG-AST-007`: repositories and lifecycle;
- S3 after `PKG-MCP-002`: MCP schemas and budgets;
- S4 after `PKG-AI-004`: investigation/proposal contracts;
- S5 after `PKG-CLAIMS-002`: normalization and scoring;
- S6 after `PKG-CLEAN-003`: heuristic-removal closeout.

## 9. File and line forecast

Expected package impact:

- 5–9 files removed;
- 18–28 existing files materially modified;
- 12–20 new files;
- 5,000–8,000 lines of total churn;
- approximately 2,000–4,000 net new lines.

Expected removal:

- 1,000–1,500 production lines;
- 400–900 test/documentation lines.

Expected additions:

- 600–1,000 AST contract lines;
- 1,200–1,900 persistence lines;
- 600–1,000 MCP contract lines;
- 800–1,400 AI/claims lines;
- 1,200–2,000 test lines.

These are planning ranges, not quotas. Prefer smaller cohesive modules and tests over matching an LOC
target.

## 10. Definition of done

Package work is complete when:

- normalized AST contracts are stable and parser independent;
- AST models and repositories support bounded, scoped navigation;
- MCP AST schemas support pagination, truncation, and budgets;
- AI proposals require AST/source citations;
- pure validation rejects malformed or uncited proposals;
- claims preserve provenance and authority distinctions;
- heuristic business-rule generation modules and exports are removed;
- BDD and other legitimate evidence ingestion remains available;
- package tests, type checks, builds, and import boundaries pass;
- downstream migration and version notes are complete;
- the monorepo dependency commit is synchronized and validated.
