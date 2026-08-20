# RuleAtlas Packages Audit Guide

Latest repository audit: [2026-07-28 findings](audit-findings-2026-07-28.md).

This document is the authoritative audit procedure for the standalone
`ruleatlas-packages` repository. It is derived from the monorepo
`docs/audit.md`, but its scope is the installable Python package boundary.

## Audit rules

1. Audit the tracked repository, not caches, virtual environments, generated
   build output, or an assumed architecture.
2. Treat documentation, package metadata, lockfiles, CI, release workflows,
   tests, and import contracts as production artifacts.
3. Record the exact command and outcome for every validation. A skipped or
   unavailable command is not a pass.
4. Separate confirmed defects from risks, observations, and intentional
   duplication.
5. Do not modify runtime code during the initial audit. Record findings first;
   repairs belong in a separately reviewed change.
6. Every finding must include severity, evidence, impact, and a concrete
   remediation.

## Repository scope

Audit all eight workspace members:

- `contracts`
- `persistence`
- `discovery-core`
- `claims`
- `extraction`
- `exports`
- `ai`
- `demo`

Also audit root configuration, `.github/workflows`, `.importlinter`,
`README.md`, package READMEs and changelogs, `uv.lock`, and release metadata.

## Required audit areas

### Correctness and API contracts

- Verify public models, protocols, serializers, and exceptions agree across
  package boundaries.
- Check optional and error paths, validation behavior, identifier handling,
  transaction boundaries, idempotency, and deterministic output.
- Trace the AST/MCP/AI path from contracts through persistence and provider
  integration.

### Architecture and dependency direction

- Confirm the cross-package DAG in `.importlinter`.
- Identify forbidden reverse dependencies, cycles, hidden runtime coupling,
  and imports of another package's private modules.
- Review re-exports and public `__all__` surfaces for accidental API growth.

### Security and privacy

- Inspect secret handling, provider errors, logging, serialization, unsafe
  deserialization, SQL construction, path handling, and untrusted model/tool
  output validation.
- Confirm test/demo conveniences cannot silently weaken library defaults.
- Review dependency and workflow supply-chain risk.

### Duplication, dead code, and maintainability

- Search for duplicate implementations, repeated literals, stale compatibility
  shims, unused exports, unreachable branches, broad exception handling,
  suppression comments, TODO/FIXME markers, and generated artifacts committed
  as source.
- Distinguish intentional protocol duplication from divergent implementation.

### Tests and release readiness

- Run lint, type checking where configured, tests, package builds, and the
  import-linter gate exactly as CI does.
- Confirm distributions contain the intended modules and metadata.
- Compare documentation and changelogs with current APIs and versions.

## Required commands

From the repository root:

```bash
git status --short --branch
uv sync --frozen --all-extras --group dev
uv run --frozen --all-extras --group dev --no-sync lint-imports --config .importlinter
```

For every workspace member:

```bash
cd <package>
uv sync --frozen --all-extras
uv run --frozen --all-extras --no-sync ruff check src
uv run --frozen --all-extras --no-sync mypy src          # only when [tool.mypy] is configured
uv run --frozen --all-extras --no-sync python -m pytest -q
uv build
```

Also run focused static searches over tracked source and configuration for
suppression comments, unfinished work, broad exception handling, secret-like
literals, private cross-package imports, and dependency inconsistencies.

## Finding format

Use one entry per finding:

```text
RA-PKG-<severity>-<number> — Short title
Severity: P0 | P1 | P2 | P3
Status: Open | Accepted | Fixed | Verified
Evidence: file:line and/or exact command output
Impact: user, security, correctness, performance, or maintainability impact
Remediation: bounded proposed change and validation
```

P0 blocks all release activity. P1 blocks production readiness. P2 should be
scheduled. P3 is low-risk cleanup.

## Completion checklist

- [x] Scope and tracked inventory recorded
- [x] All eight packages audited
- [x] Cross-package DAG validated
- [x] Lint results recorded
- [x] Type-check results recorded, including intentional skips
- [x] Test results recorded
- [x] Build results recorded
- [x] Security and dependency review recorded
- [x] Public API and documentation drift reviewed
- [x] Findings prioritized with evidence
- [x] Remediation checklist created
- [x] Release-readiness verdict stated

The latest dated report is the audit evidence. The guide itself is not proof
that an audit passed.
